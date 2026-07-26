"""基于本地 Tesseract 的票据 OCR 与结构化字段提取。"""
from __future__ import annotations

import os
import re
import logging
import math
import warnings
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError


SUPPORTED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
}
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024
DEFAULT_MAX_IMAGE_PIXELS = 25_000_000
DEFAULT_MAX_IMAGE_DIMENSION = 10_000
DEFAULT_TESSERACT_TIMEOUT_SECONDS = 15.0

logger = logging.getLogger('apps.finance')


class OCRError(Exception):
    """可展示给前端的 OCR 服务异常。"""

    def __init__(self, message, code=1):
        self.message = message
        self.code = code
        super().__init__(message)


def _positive_setting(name, default, cast):
    try:
        value = cast(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _image_limits():
    return (
        _positive_setting(
            'OCR_MAX_IMAGE_PIXELS', DEFAULT_MAX_IMAGE_PIXELS, int
        ),
        _positive_setting(
            'OCR_MAX_IMAGE_DIMENSION', DEFAULT_MAX_IMAGE_DIMENSION, int
        ),
    )


def _validate_image_dimensions(image):
    width, height = image.size
    max_pixels, max_dimension = _image_limits()
    if width <= 0 or height <= 0:
        raise OCRError('图片尺寸无效', code=2006)
    if width > max_dimension or height > max_dimension:
        raise OCRError(
            f'图片边长不能超过 {max_dimension} 像素',
            code=2008,
        )
    if width * height > max_pixels:
        raise OCRError(
            f'图片总像素不能超过 {max_pixels}，请压缩后重试',
            code=2007,
        )


def _open_image(uploaded_file):
    # Pillow 的 verify()/close() 可能关闭传入流；使用独立内存流，保留 Django
    # UploadedFile 给后续预处理读取。文件大小已在调用前限制为 10MB。
    uploaded_file.seek(0)
    image_source = BytesIO(uploaded_file.read())
    uploaded_file.seek(0)
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        image = Image.open(image_source)
    try:
        _validate_image_dimensions(image)
    except Exception:
        image.close()
        raise
    return image


def validate_image(uploaded_file):
    """校验大小、扩展名、MIME 与真实图片内容。"""
    if not uploaded_file:
        raise OCRError('请上传图片文件', code=2001)
    if not hasattr(uploaded_file, 'size'):
        raise OCRError('无效的文件对象', code=2002)
    if uploaded_file.size > MAX_FILE_SIZE:
        raise OCRError(
            f'图片大小不能超过 10MB，当前: {uploaded_file.size / 1024 / 1024:.1f}MB',
            code=2003,
        )
    if uploaded_file.size == 0:
        raise OCRError('图片文件为空', code=2004)

    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    _, extension = os.path.splitext(getattr(uploaded_file, 'name', '') or '')
    extension = extension.lower()
    if (
        content_type not in SUPPORTED_IMAGE_TYPES
        or extension not in SUPPORTED_IMAGE_EXTENSIONS
    ):
        raise OCRError('不支持的图片格式，请上传 JPG、PNG、GIF 或 WebP 图片', code=2005)

    image = None
    try:
        uploaded_file.seek(0)
        image = _open_image(uploaded_file)
        image.verify()
    except OCRError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise OCRError('图片像素过大，请压缩后重试', code=2007) from exc
    except (UnidentifiedImageError, OSError, ValueError):
        raise OCRError('文件内容不是有效图片或图片已经损坏', code=2006)
    finally:
        if image is not None:
            image.close()
        uploaded_file.seek(0)


def _prepare_image(uploaded_file):
    uploaded_file.seek(0)
    source = None
    try:
        source = _open_image(uploaded_file)
        if getattr(source, 'n_frames', 1) > 1:
            source.seek(0)
        image = ImageOps.exif_transpose(source).convert('L')
    except OCRError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise OCRError('图片像素过大，请压缩后重试', code=2007) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise OCRError('图片解码失败，请重新导出后上传', code=2006) from exc
    finally:
        if source is not None:
            source.close()

    max_pixels, max_dimension = _image_limits()
    max_width = min(2400, max_dimension)
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, max(1, int(image.height * ratio))))
    elif image.width < 1200:
        ratio = min(
            2.0,
            1200 / max(image.width, 1),
            max_dimension / max(image.width, image.height),
            math.sqrt(max_pixels / max(image.width * image.height, 1)),
        )
        if ratio > 1:
            image = image.resize((int(image.width * ratio), int(image.height * ratio)))
    image = ImageEnhance.Contrast(image).enhance(1.7)
    return image.filter(ImageFilter.SHARPEN)


def _reconstruct_ocr_text(data: dict) -> str:
    """按 Tesseract 行信息重建文本，避免中文被逐字换行后无法解析字段。"""
    texts = data.get('text', [])
    line_fields = ('page_num', 'block_num', 'par_num', 'line_num')
    lines: dict[tuple, list[str]] = {}
    line_order: list[tuple] = []

    for index, value in enumerate(texts):
        cleaned = str(value).strip()
        if not cleaned:
            continue
        key = tuple(
            values[index] if index < len(values) else 0
            for field in line_fields
            for values in [data.get(field, [])]
        )
        if key not in lines:
            lines[key] = []
            line_order.append(key)
        tokens = lines[key]
        if (
            tokens
            and re.search(r'[A-Za-z0-9]$', tokens[-1])
            and re.match(r'^[A-Za-z0-9]', cleaned)
        ):
            tokens.append(' ')
        tokens.append(cleaned)

    return '\n'.join(''.join(lines[key]) for key in line_order)


def _extract_ocr_text(image) -> tuple[str, float]:
    """调用 Tesseract，返回文本和 0-1 平均置信度。"""
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError as exc:
        raise OCRError('服务器未安装 OCR 组件 pytesseract', code=2010) from exc

    command = getattr(settings, 'TESSERACT_CMD', '') or os.environ.get('TESSERACT_CMD', '')
    if command:
        pytesseract.pytesseract.tesseract_cmd = command
    language = getattr(settings, 'OCR_TESSERACT_LANG', 'chi_sim+eng')
    timeout = _positive_setting(
        'OCR_TESSERACT_TIMEOUT_SECONDS',
        DEFAULT_TESSERACT_TIMEOUT_SECONDS,
        float,
    )

    def run_ocr(selected_language):
        return pytesseract.image_to_data(
            image,
            lang=selected_language,
            config='--oem 3 --psm 6',
            output_type=Output.DICT,
            timeout=timeout,
        )

    try:
        data = run_ocr(language)
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError('服务器未安装 Tesseract OCR 引擎', code=2011) from exc
    except pytesseract.TesseractError as exc:
        # 部分本地环境只有英文语言包，自动降级后仍属于真实 OCR。
        if language != 'eng':
            try:
                data = run_ocr('eng')
            except pytesseract.TesseractNotFoundError as fallback_exc:
                raise OCRError(
                    '服务器未安装 Tesseract OCR 引擎',
                    code=2011,
                ) from fallback_exc
            except pytesseract.TesseractError as fallback_exc:
                logger.warning(
                    'Tesseract OCR 主语言及英文降级均失败',
                    exc_info=True,
                )
                raise OCRError(
                    'OCR 引擎执行失败，请稍后重试',
                    code=2012,
                ) from fallback_exc
            except RuntimeError as fallback_exc:
                logger.warning('Tesseract 英文降级识别超时: %s', fallback_exc)
                raise OCRError(
                    'OCR 识别超时，请压缩图片或稍后重试',
                    code=2013,
                ) from fallback_exc
            except Exception as fallback_exc:
                logger.warning(
                    'Tesseract OCR 主语言及英文降级均失败',
                    exc_info=True,
                )
                raise OCRError('OCR 引擎执行失败，请稍后重试', code=2012) from fallback_exc
        else:
            logger.warning('Tesseract OCR 执行失败', exc_info=True)
            raise OCRError('OCR 引擎执行失败，请稍后重试', code=2012) from exc
    except RuntimeError as exc:
        logger.warning('Tesseract OCR 执行超时: %s', exc)
        raise OCRError('OCR 识别超时，请压缩图片或稍后重试', code=2013) from exc

    confidences = []
    for text, confidence in zip(data.get('text', []), data.get('conf', [])):
        cleaned = str(text).strip()
        try:
            confidence_value = float(confidence)
            if cleaned and confidence_value >= 0:
                confidences.append(confidence_value)
        except (TypeError, ValueError):
            continue
    return (
        _reconstruct_ocr_text(data),
        round(sum(confidences) / len(confidences) / 100, 3) if confidences else 0.0,
    )


def _normalize_amount(value: str):
    try:
        amount = Decimal(value.replace(',', '').replace('，', ''))
    except (InvalidOperation, AttributeError):
        return None
    if amount <= 0 or amount > Decimal('9999999999'):
        return None
    return f'{amount.quantize(Decimal("0.01"))}'


def _extract_amount(text: str):
    patterns = (
        r'(?:价税合计|合\s*计|总\s*计|总额|金额|TOTAL|AMOUNT)[^\d]{0,18}[¥￥]?\s*([\d,，]+(?:\.\d{1,2})?)',
        r'[¥￥]\s*([\d,，]+(?:\.\d{1,2})?)',
    )
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in reversed(matches):
            amount = _normalize_amount(match)
            if amount:
                return amount
    values = [
        normalized
        for value in re.findall(r'(?<!\d)(\d{1,8}\.\d{2})(?!\d)', text)
        if (normalized := _normalize_amount(value))
    ]
    return max(values, key=lambda item: Decimal(item)) if values else None


def _extract_date(text: str) -> str:
    patterns = (
        r'((?:19|20)\d{2})[年./\-]\s*(\d{1,2})[月./\-]\s*(\d{1,2})日?',
        r'(\d{1,2})[./\-](\d{1,2})[./\-]((?:19|20)\d{2})',
    )
    for index, pattern in enumerate(patterns):
        for groups in re.findall(pattern, text):
            try:
                year, month, day = groups if index == 0 else (groups[2], groups[0], groups[1])
                return date(int(year), int(month), int(day)).isoformat()
            except ValueError:
                continue
    return ''


def _extract_invoice_number(text: str) -> str:
    match = re.search(
        r'(?:发票号码|票据号码|单据号|NO\.?|NUMBER)[:：\s]*([A-Z0-9\-]{6,24})',
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else ''


def _extract_vendor(text: str) -> str:
    match = re.search(
        r'(?:销售方(?:名称)?|商户(?:名称)?|收款单位|开票方)[:：\s]*([^\n]{2,40})',
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(' ：:')
    ignored = re.compile(r'发票|票据|收据|日期|金额|合计|TOTAL|NO\.', re.IGNORECASE)
    for line in text.splitlines():
        cleaned = line.strip()
        if 2 <= len(cleaned) <= 40 and not ignored.search(cleaned) and not cleaned.isdigit():
            return cleaned
    return ''


def _category(text: str) -> str:
    categories = (
        ('travel', ('出租车', '滴滴', '机票', '火车', '酒店', '住宿', '交通', 'travel', 'taxi')),
        ('equipment', ('设备', '电脑', '显示器', '仪器', '硬盘', 'equipment')),
        ('material', ('材料', '耗材', '办公用品', '文具', '打印', 'material')),
        ('software', ('软件', '订阅', '云服务', 'software', 'subscription')),
        ('printing', ('打印', '印刷', '复印', '装订', 'printing')),
        ('competition_fee', ('报名费', '参赛费', 'competition')),
        ('promotion', ('宣传', '推广', '广告', '海报', 'promotion')),
        ('labor', ('劳务', '咨询费', '服务费', 'labor')),
    )
    lowered = text.lower()
    for category, keywords in categories:
        if any(keyword.lower() in lowered for keyword in keywords):
            return category
    return 'other'


def parse_receipt_text(text: str, confidence: float = 0.0) -> dict:
    """从 OCR 文本提取可编辑的支出草稿。"""
    amount = _extract_amount(text)
    expense_date = _extract_date(text)
    vendor = _extract_vendor(text)
    invoice_number = _extract_invoice_number(text)
    category = _category(text)
    warnings = []
    if not amount:
        warnings.append('未可靠识别金额，请人工核对')
    if not expense_date:
        warnings.append('未可靠识别日期，请人工核对')
    if not vendor:
        warnings.append('未识别商户名称')

    base = max(0.0, min(float(confidence), 1.0))
    return {
        'amount': amount,
        'expense_date': expense_date or date.today().isoformat(),
        'category': category,
        'title': f'{vendor}票据' if vendor else '票据支出',
        'vendor': vendor,
        'invoice_number': invoice_number,
        'confidence': round(base, 3),
        'field_confidence': {
            'amount': round(min(1.0, base + 0.12), 3) if amount else 0.0,
            'expense_date': round(min(1.0, base + 0.08), 3) if expense_date else 0.0,
            'vendor': round(base, 3) if vendor else 0.0,
            'category': round(max(0.35, base), 3) if category != 'other' else 0.25,
        },
        'warnings': warnings,
    }


def recognize_receipt(uploaded_file):
    """执行真实 OCR 并返回原文、结构化字段、置信度与校验提示。"""
    validate_image(uploaded_file)
    image = _prepare_image(uploaded_file)
    try:
        raw_text, confidence = _extract_ocr_text(image)
        recognized = parse_receipt_text(raw_text, confidence)
        return {
            'success': True,
            'is_stub': False,
            'engine': 'tesseract',
            'message': '识别完成，请在保存支出前核对关键字段',
            'file_info': {
                'name': getattr(uploaded_file, 'name', 'receipt.jpg'),
                'size': uploaded_file.size,
                'content_type': getattr(uploaded_file, 'content_type', '') or '',
                'width': image.width,
                'height': image.height,
            },
            'recognized': recognized,
            'raw_text': raw_text,
        }
    finally:
        image.close()
