"""真实 OCR 服务的图片校验、字段解析与 API 测试。"""
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.finance import ocr_service
from apps.finance.ocr_service import (
    OCRError,
    _extract_ocr_text,
    _reconstruct_ocr_text,
    parse_receipt_text,
    recognize_receipt,
    validate_image,
)

OCR_URL = '/api/v1/finance/ocr/recognize/'
OCR_TEXT = (
    '增值税电子普通发票\n'
    '销售方名称：北京示例科技有限公司\n'
    '发票号码：12345678901234567890\n'
    '开票日期：2026年07月25日\n'
    '软件订阅服务\n'
    '价税合计 ￥1,280.50'
)


def make_image_file(name='receipt.jpg', content_type='image/jpeg'):
    output = BytesIO()
    image_format = 'PNG' if name.lower().endswith('.png') else 'JPEG'
    Image.new('RGB', (480, 320), color='white').save(output, format=image_format)
    return SimpleUploadedFile(name=name, content=output.getvalue(), content_type=content_type)


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


class TestOCRService:
    def test_reconstruct_ocr_text_preserves_chinese_lines(self):
        data = {
            'text': ['销售', '方', '名称', ':', '星云', '办公', 'Invoice', 'No', 'FP2026'],
            'page_num': [1] * 9,
            'block_num': [1] * 9,
            'par_num': [1] * 9,
            'line_num': [1, 1, 1, 1, 1, 1, 2, 2, 2],
        }
        assert _reconstruct_ocr_text(data) == '销售方名称:星云办公\nInvoice No FP2026'

    def test_recognize_valid_image_uses_real_engine_contract(self, monkeypatch):
        monkeypatch.setattr(ocr_service, '_extract_ocr_text', lambda image: (OCR_TEXT, 0.88))
        result = recognize_receipt(make_image_file())
        assert result['success'] is True
        assert result['is_stub'] is False
        assert result['engine'] == 'tesseract'
        assert result['recognized']['amount'] == '1280.50'

    def test_recognize_returns_structured_fields(self, monkeypatch):
        monkeypatch.setattr(ocr_service, '_extract_ocr_text', lambda image: (OCR_TEXT, 0.82))
        result = recognize_receipt(make_image_file('test.png', 'image/png'))
        assert result['file_info']['name'] == 'test.png'
        assert result['recognized']['expense_date'] == '2026-07-25'
        assert result['recognized']['category'] == 'software'
        assert result['recognized']['vendor'] == '北京示例科技有限公司'
        assert result['recognized']['invoice_number'] == '12345678901234567890'
        assert result['raw_text'] == OCR_TEXT

    def test_parse_receipt_warns_when_fields_missing(self):
        parsed = parse_receipt_text('普通票据', confidence=0.4)
        assert parsed['amount'] is None
        assert parsed['warnings']
        assert parsed['field_confidence']['amount'] == 0

    def test_validate_empty_file(self):
        image = SimpleUploadedFile(name='empty.jpg', content=b'', content_type='image/jpeg')
        with pytest.raises(OCRError):
            validate_image(image)

    def test_validate_no_file(self):
        with pytest.raises(OCRError):
            validate_image(None)

    def test_validate_unsupported_type(self):
        image = SimpleUploadedFile(
            name='doc.pdf',
            content=b'%PDF-1.4',
            content_type='application/pdf',
        )
        with pytest.raises(OCRError):
            validate_image(image)

    def test_validate_rejects_fake_image_content(self):
        image = SimpleUploadedFile(
            name='fake.jpg',
            content=b'not-an-image',
            content_type='image/jpeg',
        )
        with pytest.raises(OCRError) as error:
            validate_image(image)
        assert error.value.code == 2006

    def test_validate_rejects_image_over_dimension_limit(self, settings):
        settings.OCR_MAX_IMAGE_DIMENSION = 300

        with pytest.raises(OCRError) as error:
            validate_image(make_image_file())

        assert error.value.code == 2008

    def test_validate_rejects_image_over_pixel_limit(self, settings):
        settings.OCR_MAX_IMAGE_DIMENSION = 1000
        settings.OCR_MAX_IMAGE_PIXELS = 100_000

        with pytest.raises(OCRError) as error:
            validate_image(make_image_file())

        assert error.value.code == 2007

    def test_tesseract_timeout_is_bounded_and_friendly(
        self, monkeypatch, settings
    ):
        import pytesseract

        calls = []

        def timeout(*args, **kwargs):
            calls.append(kwargs['timeout'])
            raise RuntimeError('Tesseract process timeout')

        settings.OCR_TESSERACT_TIMEOUT_SECONDS = 2.5
        monkeypatch.setattr(pytesseract, 'image_to_data', timeout)

        with pytest.raises(OCRError) as error:
            _extract_ocr_text(Image.new('L', (20, 20), color='white'))

        assert error.value.code == 2013
        assert 'timeout' not in error.value.message.lower()
        assert calls == [2.5]

    def test_english_fallback_uses_same_timeout(self, monkeypatch, settings):
        import pytesseract

        calls = []

        def recognize(*args, **kwargs):
            calls.append((kwargs['lang'], kwargs['timeout']))
            if len(calls) == 1:
                raise pytesseract.TesseractError(1, 'missing language')
            return {'text': [], 'conf': []}

        settings.OCR_TESSERACT_LANG = 'chi_sim+eng'
        settings.OCR_TESSERACT_TIMEOUT_SECONDS = 3
        monkeypatch.setattr(pytesseract, 'image_to_data', recognize)

        result = _extract_ocr_text(Image.new('L', (20, 20), color='white'))
        assert result == ('', 0.0)
        assert calls == [('chi_sim+eng', 3.0), ('eng', 3.0)]


@pytest.mark.api
@pytest.mark.django_db
class TestOCRAPI:
    def test_ocr_requires_auth(self, api_client):
        assert api_client.post(OCR_URL).status_code == 401

    def test_ocr_no_file(self, member_client):
        assert member_client.post(OCR_URL).status_code == 400

    def test_ocr_valid_upload(self, member_client, monkeypatch):
        monkeypatch.setattr(ocr_service, '_extract_ocr_text', lambda image: (OCR_TEXT, 0.9))
        response = member_client.post(
            OCR_URL,
            {'image': make_image_file()},
            format='multipart',
        )
        assert response.status_code == 200
        data = extract_data(response)
        assert data['success'] is True
        assert data['is_stub'] is False
        assert data['recognized']['amount'] == '1280.50'

    def test_ocr_invalid_type(self, member_client):
        image = SimpleUploadedFile(
            name='doc.pdf',
            content=b'%PDF-1.4',
            content_type='application/pdf',
        )
        assert member_client.post(
            OCR_URL,
            {'image': image},
            format='multipart',
        ).status_code == 400

    def test_ocr_recognized_fields(self, member_client, monkeypatch):
        monkeypatch.setattr(ocr_service, '_extract_ocr_text', lambda image: (OCR_TEXT, 0.8))
        response = member_client.post(
            OCR_URL,
            {'image': make_image_file('bill.png', 'image/png')},
            format='multipart',
        )
        data = extract_data(response)
        assert response.status_code == 200
        assert data['recognized']['category'] == 'software'
        assert 'field_confidence' in data['recognized']

    def test_ocr_engine_error_returns_service_unavailable(
        self, member_client, monkeypatch
    ):
        def unavailable(*args, **kwargs):
            raise OCRError('OCR 识别超时，请稍后重试', code=2013)

        monkeypatch.setattr(
            'apps.finance.ocr_views.recognize_receipt', unavailable
        )
        response = member_client.post(
            OCR_URL,
            {'image': make_image_file()},
            format='multipart',
        )

        assert response.status_code == 503
        assert response.json()['code'] == 2013

    def test_ocr_unexpected_error_does_not_leak_details(
        self, member_client, monkeypatch
    ):
        def broken(*args, **kwargs):
            raise RuntimeError('secret backend path')

        monkeypatch.setattr('apps.finance.ocr_views.recognize_receipt', broken)
        response = member_client.post(
            OCR_URL,
            {'image': make_image_file()},
            format='multipart',
        )

        assert response.status_code == 503
        assert response.json()['code'] == 2014
        assert 'secret backend path' not in response.json()['message']
