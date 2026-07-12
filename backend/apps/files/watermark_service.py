"""
N32: 水印服务
为图片文件添加文字水印（使用 Pillow，延迟导入）

支持的图片格式: PNG / JPEG / GIF / WEBP / BMP 等 Pillow 支持的格式
当 Pillow 不可用或文件非图片时，返回 None
"""
import io
import os

# 图片扩展名集合（小写）
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'}


def is_image_file(filename, content_type=''):
    """判断是否为图片文件（基于扩展名或 content_type）"""
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return True
    if content_type and content_type.startswith('image/'):
        return True
    return False


def add_text_watermark(file_field, watermark_text, opacity=128):
    """
    为图片添加文字水印

    :param file_field: Django FileField 的 FieldFile 对象
    :param watermark_text: 水印文字
    :param opacity: 水印不透明度（0-255）
    :return: BytesIO 对象（包含加水印后的 PNG 图片），失败返回 None
    """
    if not watermark_text or not file_field:
        return None

    # 延迟导入 Pillow
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # Pillow 未安装，无法添加水印
        return None

    try:
        # 打开原始图片
        file_field.open('rb')
        try:
            img = Image.open(file_field).convert('RGBA')
        finally:
            file_field.close()
    except Exception:
        return None

    # 创建透明水印图层
    watermark_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)

    # 尝试加载字体，失败则使用默认字体
    font = None
    font_size = max(16, min(img.size) // 20)
    try:
        # 尝试加载系统中文字体
        font_paths = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/simhei.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
    except Exception:
        font = None
    if font is None:
        font = ImageFont.load_default()

    # 计算文字位置（右下角偏移）
    try:
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except Exception:
        text_width, text_height = len(watermark_text) * font_size, font_size

    margin = 10
    x = max(0, img.size[0] - text_width - margin)
    y = max(0, img.size[1] - text_height - margin)

    # 绘制水印文字（半透明白色）
    draw.text((x, y), watermark_text, fill=(255, 255, 255, opacity), font=font)

    # 合并水印图层到原图
    watermarked = Image.alpha_composite(img, watermark_layer)

    # 转换为 RGB 并输出为 PNG
    output = io.BytesIO()
    watermarked.convert('RGB').save(output, format='PNG')
    output.seek(0)
    return output
