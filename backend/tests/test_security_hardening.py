"""审计日志与媒体访问安全回归测试。"""

import importlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import signing
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.test import override_settings

from apps.audit.middleware import (
    REDACTED_VALUE,
    OperationLogMiddleware,
    redact_sensitive_data,
)
from apps.audit.models import OperationLog
from common.storage import (
    ProtectedMediaStorage,
    create_protected_media_token,
    load_protected_media_token,
)


def test_recursive_audit_redaction_handles_nested_and_mixed_case_fields():
    source = {
        'title': '可记录标题',
        'plaintext': '绝密明文',
        'profile': {
            'identityNumber': '330102199901010011',
            'contacts': [
                {'home-address': '测试路 1 号', 'nickname': '小明'},
                {'银行卡号': '6222000000000000'},
            ],
        },
        'payment': {'applicantBankAccount': '123456789'},
        'credentials': {'oauthAccessToken': 'token-value'},
    }

    result = redact_sensitive_data(source)

    assert result['title'] == '可记录标题'
    assert result['plaintext'] == REDACTED_VALUE
    assert result['profile']['identityNumber'] == REDACTED_VALUE
    assert result['profile']['contacts'][0]['home-address'] == REDACTED_VALUE
    assert result['profile']['contacts'][0]['nickname'] == '小明'
    assert result['profile']['contacts'][1]['银行卡号'] == REDACTED_VALUE
    assert result['payment']['applicantBankAccount'] == REDACTED_VALUE
    assert result['credentials']['oauthAccessToken'] == REDACTED_VALUE


def test_audit_upload_metadata_never_records_sensitive_filename():
    request = RequestFactory().post(
        '/api/v1/files/',
        {
            'file': SimpleUploadedFile(
                '张三_身份证号_330102199901010011.jpg',
                b'fake image',
                content_type='image/jpeg',
            ),
            'metadata': json.dumps({
                'bankAccount': '6222000000000000',
                'label': '可记录',
            }),
        },
    )
    middleware = OperationLogMiddleware(lambda current_request: None)

    summary = middleware._get_request_summary(request)

    assert summary['_files']['file'] == {
        'size': 10,
        'content_type': 'image/jpeg',
    }
    assert summary['metadata'] == {
        'bankAccount': REDACTED_VALUE,
        'label': '可记录',
    }
    assert '张三' not in json.dumps(summary, ensure_ascii=False)
    assert '330102199901010011' not in json.dumps(summary, ensure_ascii=False)
    assert '6222000000000000' not in json.dumps(summary, ensure_ascii=False)


@override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=64)
def test_audit_multipart_summary_streams_file_without_reading_whole_body():
    request = RequestFactory().post(
        '/api/v1/files/',
        {
            'file': SimpleUploadedFile(
                'large.bin',
                b'x' * 4096,
                content_type='application/octet-stream',
            ),
        },
    )
    middleware = OperationLogMiddleware(lambda current_request: None)

    summary = middleware._get_request_summary(request)

    assert summary['_files']['file']['size'] == 4096


def test_audit_data_migration_scrubs_existing_secrets_and_upload_names():
    migration = importlib.import_module(
        'apps.audit.migrations.0004_scrub_sensitive_request_data'
    )
    payload = {
        'plaintext': 'legacy plaintext',
        'profile': {'bankAccount': 'legacy account'},
        'metadata': '{"identityNumber": "legacy identity", "label": "可记录"}',
        '_files': {
            'file': {
                'name': '张三_身份证_330102.jpg',
                'size': 12,
                'content_type': 'image/jpeg',
            },
            'id_card': {'name': 'identity.jpg', 'size': 20},
        },
    }

    result = migration.scrub_payload(payload)

    assert result['plaintext'] == REDACTED_VALUE
    assert result['profile']['bankAccount'] == REDACTED_VALUE
    assert result['metadata'] == {
        'identityNumber': REDACTED_VALUE,
        'label': '可记录',
    }
    assert result['_files']['file'] == {
        'size': 12,
        'content_type': 'image/jpeg',
    }
    assert result['_files']['id_card'] == REDACTED_VALUE
    serialized = json.dumps(result, ensure_ascii=False)
    assert 'legacy plaintext' not in serialized
    assert 'legacy account' not in serialized
    assert 'legacy identity' not in serialized
    assert '张三' not in serialized


@pytest.mark.api
@pytest.mark.django_db
def test_sensitive_create_plaintext_and_nested_identity_data_never_enter_operation_log(
    teacher_client,
):
    secret_values = (
        'create-secret-plaintext',
        '330102199901010011',
        '6222000000000000',
        '测试路 1 号',
    )
    response = teacher_client.post(
        '/api/v1/sensitive/data/',
        {
            'data_type': 'id_card',
            'title': '审计脱敏测试',
            'plaintext': secret_values[0],
            # 即使未来接口接收嵌套扩展字段，中间件也必须递归脱敏。
            'profile': {
                'identityNumber': secret_values[1],
                'bankAccount': secret_values[2],
                'address': secret_values[3],
            },
        },
        format='json',
    )
    assert response.status_code == 201, response.content

    middleware_log = (
        OperationLog.objects.filter(
            request_path='/api/v1/sensitive/data/',
            request_method='POST',
            request_data__isnull=False,
        )
        .order_by('-id')
        .first()
    )
    assert middleware_log is not None

    serialized = json.dumps(middleware_log.request_data, ensure_ascii=False)
    for secret in secret_values:
        assert secret not in serialized
    assert middleware_log.request_data['plaintext'] == REDACTED_VALUE
    assert middleware_log.request_data['profile']['identityNumber'] == REDACTED_VALUE
    assert middleware_log.request_data['profile']['bankAccount'] == REDACTED_VALUE
    assert middleware_log.request_data['profile']['address'] == REDACTED_VALUE


def test_protected_storage_uses_public_url_only_for_public_directory(settings):
    assert isinstance(default_storage, ProtectedMediaStorage)
    storage = ProtectedMediaStorage(location=settings.MEDIA_ROOT, base_url='/media/')

    public_url = storage.url('public/team/logo.png')
    protected_url = storage.url('finance/receipts/receipt.png')

    assert public_url == '/media/public/team/logo.png'
    parsed = urlparse(protected_url)
    assert parsed.path == '/api/v1/common/media/'
    token = parse_qs(parsed.query)['token'][0]
    assert load_protected_media_token(token) == 'finance/receipts/receipt.png'
    assert 'finance/receipts/receipt.png' not in protected_url


def test_media_token_rejects_path_traversal():
    with pytest.raises(ValueError):
        create_protected_media_token('../secrets.txt')


def test_expired_media_token_is_rejected(monkeypatch, settings):
    settings.PROTECTED_MEDIA_URL_TTL = 5
    monkeypatch.setattr(signing.time, 'time', lambda: 100)
    token = create_protected_media_token('files/report.pdf')
    monkeypatch.setattr(signing.time, 'time', lambda: 106)

    with pytest.raises(signing.SignatureExpired):
        load_protected_media_token(token)


@pytest.mark.api
@pytest.mark.django_db
def test_signed_media_endpoint_serves_file_but_direct_media_path_does_not(
    api_client,
    tmp_path,
):
    relative_name = 'finance/receipts/private-receipt.txt'
    target = tmp_path / relative_name
    target.parent.mkdir(parents=True)
    target.write_bytes(b'private receipt')
    token = create_protected_media_token(relative_name)

    with override_settings(
        MEDIA_ROOT=str(tmp_path),
        PROTECTED_MEDIA_USE_X_ACCEL_REDIRECT=False,
    ):
        signed_response = api_client.get(
            '/api/v1/common/media/',
            {'token': token},
        )
        direct_response = api_client.get(f'/media/{relative_name}')

    assert signed_response.status_code == 200
    assert b''.join(signed_response.streaming_content) == b'private receipt'
    assert signed_response['Cache-Control'] == 'private, no-store'
    assert signed_response['X-Content-Type-Options'] == 'nosniff'
    assert signed_response['Content-Disposition'].startswith('attachment;')
    assert signed_response['Content-Security-Policy'] == "default-src 'none'; sandbox"
    assert direct_response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_invalid_media_signature_does_not_reveal_file(api_client, tmp_path):
    target = tmp_path / 'files/private.txt'
    target.parent.mkdir(parents=True)
    target.write_text('private', encoding='utf-8')

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        response = api_client.get(
            '/api/v1/common/media/',
            {'token': 'forged-token'},
        )

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_finance_receipt_api_returns_signed_url_instead_of_raw_media_path(
    member_client,
    make_finance,
    tmp_path,
):
    from apps.finance.models import FinanceReceipt

    expense = make_finance()
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        receipt = FinanceReceipt.objects.create(
            expense=expense,
            file=SimpleUploadedFile(
                'receipt.png',
                b'fake receipt image',
                content_type='image/png',
            ),
            uploaded_by=member_client.user,
        )
        response = member_client.get(
            '/api/v1/finance/receipts/',
            {'expense': expense.id},
        )

    assert response.status_code == 200
    payload = response.json()
    data = payload.get('data', payload)
    rows = data.get('results', data)
    receipt_url = next(row['file'] for row in rows if row['id'] == receipt.id)
    parsed = urlparse(receipt_url)
    assert parsed.path == '/api/v1/common/media/'
    assert load_protected_media_token(
        parse_qs(parsed.query)['token'][0]
    ).startswith('finance/receipts/')
    assert '/media/finance/' not in receipt_url


@pytest.mark.api
@pytest.mark.django_db
def test_authorized_file_download_uses_nginx_internal_redirect(
    admin_client,
    make_project,
    tmp_path,
):
    from apps.files.models import FileAsset

    project = make_project()
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        asset = FileAsset.objects.create(
            project=project,
            name='内部材料.pdf',
            file=SimpleUploadedFile(
                'internal.pdf',
                b'internal content',
                content_type='application/pdf',
            ),
            level=FileAsset.Level.INTERNAL,
            size=16,
            content_type='application/pdf',
            uploader=admin_client.user,
        )

        with override_settings(PROTECTED_MEDIA_USE_X_ACCEL_REDIRECT=True):
            response = admin_client.get(f'/api/v1/files/{asset.id}/download/')

    assert response.status_code == 200
    assert response['X-Accel-Redirect'].startswith('/_protected_media/files/')
    assert response['Cache-Control'] == 'private, no-store'
    assert response['Content-Disposition'].startswith('attachment;')


def test_production_nginx_blocks_raw_media_and_uses_internal_location():
    workspace = Path(__file__).resolve().parents[2]
    config = (workspace / 'deploy/nginx/default.prod.conf').read_text(
        encoding='utf-8'
    )

    assert 'location ^~ /media/public/' in config
    assert 'alias /app/media/public/;' in config
    assert 'location ^~ /_protected_media/' in config
    assert 'internal;' in config
    assert 'location ^~ /media/' in config
    assert 'return 404;' in config
    assert 'location = /api/v1/common/media/' in config
    assert 'access_log off;' in config
