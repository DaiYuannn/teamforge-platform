"""
N23 OCR 票据识别（Stub）测试
- 图片校验、占位响应
"""
import pytest
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.finance.ocr_service import (
    recognize_receipt,
    validate_image,
    OCRError,
    SUPPORTED_IMAGE_TYPES,
)

OCR_URL = '/api/v1/finance/ocr/recognize/'


def make_image_file(name='receipt.jpg', content_type='image/jpeg', size=1024):
    """创建模拟图片文件"""
    content = b'\xff\xd8\xff\xe0' + b'\x00' * size
    return SimpleUploadedFile(
        name=name, content=content, content_type=content_type,
    )


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


class TestOCRService:
    """OCR 服务单元测试"""

    def test_recognize_valid_image(self):
        """有效图片返回占位结果"""
        img = make_image_file()
        result = recognize_receipt(img)
        assert result['success'] is True
        assert result['is_stub'] is True
        assert 'recognized' in result

    def test_recognize_returns_structure(self):
        """返回结构化占位数据"""
        img = make_image_file(name='test.png', content_type='image/png')
        result = recognize_receipt(img)
        assert 'file_info' in result
        assert result['file_info']['name'] == 'test.png'
        assert 'amount' in result['recognized']
        assert 'expense_date' in result['recognized']
        assert 'category' in result['recognized']

    def test_validate_empty_file(self):
        """空文件报错"""
        img = SimpleUploadedFile(name='empty.jpg', content=b'', content_type='image/jpeg')
        with pytest.raises(OCRError):
            validate_image(img)

    def test_validate_no_file(self):
        """无文件报错"""
        with pytest.raises(OCRError):
            validate_image(None)

    def test_validate_unsupported_type(self):
        """不支持的类型报错"""
        img = SimpleUploadedFile(
            name='doc.pdf', content=b'%PDF-1.4', content_type='application/pdf',
        )
        with pytest.raises(OCRError):
            validate_image(img)


@pytest.mark.api
@pytest.mark.django_db
class TestOCRAPI:
    """OCR API 测试"""

    def test_ocr_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.post(OCR_URL)
        assert resp.status_code == 401

    def test_ocr_no_file(self, member_client):
        """未上传文件报错"""
        resp = member_client.post(OCR_URL)
        assert resp.status_code == 400

    def test_ocr_valid_upload(self, member_client):
        """上传有效图片"""
        img = make_image_file()
        resp = member_client.post(OCR_URL, {'image': img}, format='multipart')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['success'] is True
        assert data['is_stub'] is True

    def test_ocr_invalid_type(self, member_client):
        """上传非图片文件报错"""
        img = SimpleUploadedFile(
            name='doc.pdf', content=b'%PDF-1.4', content_type='application/pdf',
        )
        resp = member_client.post(OCR_URL, {'image': img}, format='multipart')
        assert resp.status_code == 400

    def test_ocr_recognized_fields(self, member_client):
        """返回占位识别字段"""
        img = make_image_file(name='bill.png', content_type='image/png')
        resp = member_client.post(OCR_URL, {'image': img}, format='multipart')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert 'recognized' in data
        assert data['recognized']['category'] == 'other'
