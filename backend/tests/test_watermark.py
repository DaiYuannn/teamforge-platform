"""
N32: 水印（Watermark）测试
- 水印服务：is_image_file / add_text_watermark
- API 层：download_watermarked 下载带水印图片
- 非图片文件、缺少水印文字等异常处理
"""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def make_image_bytes(color='blue', size=(120, 80)):
    """生成小型 PNG 图片字节"""
    from PIL import Image
    img = Image.new('RGB', size, color=color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


@pytest.mark.model
@pytest.mark.django_db
class TestWatermarkService:
    """水印服务测试"""

    def test_is_image_file_png(self):
        """识别 PNG 图片"""
        from apps.files.watermark_service import is_image_file
        assert is_image_file('photo.png') is True
        assert is_image_file('photo.jpg') is True
        assert is_image_file('photo.jpeg') is True

    def test_is_image_file_non_image(self):
        """识别非图片文件"""
        from apps.files.watermark_service import is_image_file
        assert is_image_file('doc.pdf') is False
        assert is_image_file('data.csv') is False

    def test_is_image_file_by_content_type(self):
        """通过 content_type 识别图片"""
        from apps.files.watermark_service import is_image_file
        assert is_image_file('file', content_type='image/png') is True
        assert is_image_file('file', content_type='application/pdf') is False

    def test_add_text_watermark_returns_bytes(self, make_project, make_user):
        """添加水印返回 BytesIO"""
        from apps.files.watermark_service import add_text_watermark
        from apps.files.models import FileAsset
        img_bytes = make_image_bytes()
        upload = SimpleUploadedFile('img.png', img_bytes, content_type='image/png')
        asset = FileAsset.objects.create(
            project=make_project(), name='img.png', file=upload, uploader=make_user(),
        )
        result = add_text_watermark(asset.file, '机密水印')
        assert result is not None
        assert result.read(8)  # 有内容
        # 确认是有效的 PNG
        result.seek(0)
        assert result.read(8)[:8] == b'\x89PNG\r\n\x1a\n'

    def test_add_text_watermark_empty_text(self, make_project, make_user):
        """空水印文字返回 None"""
        from apps.files.watermark_service import add_text_watermark
        from apps.files.models import FileAsset
        img_bytes = make_image_bytes()
        upload = SimpleUploadedFile('img.png', img_bytes, content_type='image/png')
        asset = FileAsset.objects.create(
            project=make_project(), name='img.png', file=upload, uploader=make_user(),
        )
        assert add_text_watermark(asset.file, '') is None
        assert add_text_watermark(asset.file, None) is None


@pytest.mark.api
@pytest.mark.django_db
class TestDownloadWatermarkedAPI:
    """水印下载 API 测试"""

    def test_download_watermarked_image(self, teacher_client, make_project, make_user):
        """下载带水印的图片"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        img_bytes = make_image_bytes()
        upload = SimpleUploadedFile('photo.png', img_bytes, content_type='image/png')
        asset = FileAsset.objects.create(
            project=project, name='photo.png', file=upload,
            level='public', uploader=teacher_client.user,
        )
        resp = teacher_client.get(f'/api/v1/files/{asset.id}/download-watermarked/?text=机密')
        assert resp.status_code == 200, resp.content
        assert resp['Content-Type'] == 'image/png'
        assert 'attachment' in resp['Content-Disposition']
        # 返回的应是有效 PNG
        assert resp.content[:8] == b'\x89PNG\r\n\x1a\n'

    def test_download_watermarked_with_file_field(self, teacher_client, make_project, make_user):
        """使用文件自身的 watermark_text 字段"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        img_bytes = make_image_bytes()
        upload = SimpleUploadedFile('photo.png', img_bytes, content_type='image/png')
        asset = FileAsset.objects.create(
            project=project, name='photo.png', file=upload,
            level='public', uploader=teacher_client.user,
            watermark_text='内部资料',
        )
        resp = teacher_client.get(f'/api/v1/files/{asset.id}/download-watermarked/')
        assert resp.status_code == 200, resp.content
        assert resp['Content-Type'] == 'image/png'

    def test_download_watermarked_non_image(self, teacher_client, make_project, make_user):
        """非图片文件加水印返回 400"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        upload = SimpleUploadedFile('doc.txt', b'text content', content_type='text/plain')
        asset = FileAsset.objects.create(
            project=project, name='doc.txt', file=upload,
            level='public', uploader=teacher_client.user,
        )
        resp = teacher_client.get(f'/api/v1/files/{asset.id}/download-watermarked/?text=水印')
        assert resp.status_code == 400

    def test_download_watermarked_missing_text(self, teacher_client, make_project, make_user):
        """缺少水印文字返回 400"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        img_bytes = make_image_bytes()
        upload = SimpleUploadedFile('photo.png', img_bytes, content_type='image/png')
        asset = FileAsset.objects.create(
            project=project, name='photo.png', file=upload,
            level='public', uploader=teacher_client.user,
        )
        resp = teacher_client.get(f'/api/v1/files/{asset.id}/download-watermarked/')
        assert resp.status_code == 400

    def test_download_watermarked_watermarked_diff_from_original(self, teacher_client, make_project, make_user):
        """水印图片大小与原图不同（确认确实加了水印）"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        img_bytes = make_image_bytes()
        upload = SimpleUploadedFile('photo.png', img_bytes, content_type='image/png')
        asset = FileAsset.objects.create(
            project=project, name='photo.png', file=upload,
            level='public', uploader=teacher_client.user,
        )
        resp = teacher_client.get(f'/api/v1/files/{asset.id}/download-watermarked/?text=WATERMARK_TEXT')
        assert resp.status_code == 200, resp.content
        # 水印后的 PNG 与原图字节不同（重新编码 + 水印内容）
        assert resp.content != img_bytes

    def test_watermark_text_field_settable(self, teacher_client, make_project, make_user):
        """watermark_text 字段可设置"""
        from apps.files.models import FileAsset
        project = make_project(leader=teacher_client.user)
        img_bytes = make_image_bytes()
        upload = SimpleUploadedFile('photo.png', img_bytes, content_type='image/png')
        asset = FileAsset.objects.create(
            project=project, name='photo.png', file=upload,
            level='public', uploader=teacher_client.user,
            watermark_text='专用水印',
        )
        assert asset.watermark_text == '专用水印'
