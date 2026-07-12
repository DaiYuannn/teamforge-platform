"""
OCR 票据识别服务（Stub）
- 当前为占位实现，仅校验图片并返回结构化占位响应
- 实际生产环境可对接 Tesseract 或云 OCR API
"""
import os
from datetime import date


# 支持的图片类型
SUPPORTED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
}

SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

# 最大文件大小 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


class OCRError(Exception):
    """OCR 服务异常"""

    def __init__(self, message, code=1):
        self.message = message
        self.code = code
        super().__init__(message)


def validate_image(uploaded_file):
    """
    校验上传的图片文件
    :param uploaded_file: Django UploadedFile 对象
    :raises OCRError: 校验失败时抛出异常
    """
    if not uploaded_file:
        raise OCRError('请上传图片文件', code=2001)

    if not hasattr(uploaded_file, 'size'):
        raise OCRError('无效的文件对象', code=2002)

    # 校验文件大小
    if uploaded_file.size > MAX_FILE_SIZE:
        raise OCRError(
            f'图片大小不能超过 10MB，当前: {uploaded_file.size / 1024 / 1024:.1f}MB',
            code=2003,
        )

    if uploaded_file.size == 0:
        raise OCRError('图片文件为空', code=2004)

    # 校验文件类型
    content_type = (uploaded_file.content_type or '').lower()
    name = getattr(uploaded_file, 'name', '') or ''
    _, ext = os.path.splitext(name)
    ext = ext.lower()

    if content_type and content_type not in SUPPORTED_IMAGE_TYPES:
        if ext not in SUPPORTED_IMAGE_EXTENSIONS:
            raise OCRError(
                f'不支持的图片格式: {content_type or ext}，请上传 JPG/PNG/GIF/WebP 格式',
                code=2005,
            )


def recognize_receipt(uploaded_file):
    """
    识别票据图片（Stub 实现）
    - 当前为占位实现，返回结构化的占位响应
    - 实际生产环境应替换为真实的 OCR 调用

    :param uploaded_file: Django UploadedFile 对象
    :return: dict 识别结果
    :raises OCRError: 校验或识别失败时抛出异常
    """
    # 1. 校验图片
    validate_image(uploaded_file)

    # 2. Stub 识别（占位）
    # 实际 OCR 应解析图片内容，提取金额、日期、类别等信息
    # 当前仅返回占位结构化数据
    name = getattr(uploaded_file, 'name', 'receipt.jpg')
    today = date.today().isoformat()

    result = {
        'success': True,
        'is_stub': True,
        'message': 'OCR 识别为占位实现，实际环境请对接 Tesseract 或云 OCR API',
        'file_info': {
            'name': name,
            'size': uploaded_file.size,
            'content_type': uploaded_file.content_type or '',
        },
        'recognized': {
            'amount': None,
            'expense_date': today,
            'category': 'other',
            'title': f'票据识别（占位）-{name}',
            'vendor': '',
            'confidence': 0.0,
        },
    }

    return result
