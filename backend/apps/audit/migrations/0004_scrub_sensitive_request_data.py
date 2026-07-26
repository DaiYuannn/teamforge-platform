"""清理修复前可能已写入操作日志的敏感请求值。"""

import json
import re

from django.db import migrations


REDACTED = '[REDACTED]'
EXACT_FIELDS = {
    'password', 'password_confirm', 'old_password', 'new_password',
    'token', 'access_token', 'refresh_token', 'secret', 'api_key',
    'encryption_key', 'private_key', 'credit_card', 'id_card',
    'plaintext', 'plain_text', 'ciphertext', 'cipher_text',
    'encrypted_content', 'identity_number', 'identity_card',
    'id_number', 'passport_number', 'social_security_number',
    'bank_card', 'bank_account', 'account_number', 'debit_card',
    'payment_account', 'phone', 'mobile', 'mobile_phone',
    'address', 'home_address', 'residential_address',
    'signature', 'electronic_signature', 'seal',
}
FIELD_SUFFIXES = tuple(f'_{field}' for field in EXACT_FIELDS)
FIELD_FRAGMENTS = (
    'password', 'access_token', 'refresh_token', 'api_key',
    'private_key', 'encryption_key',
    'plaintext', 'plain_text', 'ciphertext', 'cipher_text',
    'encrypted_content',
    'identity_number', 'identity_card', 'id_card', 'id_number',
    'passport_number', 'social_security_number',
    'credit_card', 'debit_card', 'bank_card', 'bank_account',
    'account_number', 'payment_account',
    'phone', 'home_address', 'residential_address', 'address',
    'electronic_signature', 'signature',
)
CHINESE_TERMS = (
    '密码', '口令', '令牌', '密钥', '密文', '明文',
    '身份证', '护照号', '社保号',
    '银行卡', '银行账户', '支付账户', '信用卡',
    '手机号', '电话号码', '住址', '地址', '签名', '印章',
)


def _normalize(key):
    value = str(key).strip()
    value = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', value)
    value = re.sub(r'[^a-zA-Z0-9]+', '_', value)
    return value.strip('_').lower()


def _is_sensitive(key):
    raw = str(key).strip().lower()
    normalized = _normalize(key)
    return (
        any(term in raw for term in CHINESE_TERMS)
        or normalized in EXACT_FIELDS
        or any(fragment in normalized for fragment in FIELD_FRAGMENTS)
        or any(normalized.endswith(suffix) for suffix in FIELD_SUFFIXES)
    )


def scrub_payload(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if _is_sensitive(key):
                cleaned[key] = REDACTED
            elif key == '_files' and isinstance(item, dict):
                cleaned_files = {}
                for field_name, metadata in item.items():
                    if _is_sensitive(field_name):
                        cleaned_files[field_name] = REDACTED
                    elif isinstance(metadata, dict):
                        cleaned_files[field_name] = {
                            metadata_key: metadata_value
                            for metadata_key, metadata_value in metadata.items()
                            if metadata_key != 'name'
                        }
                    else:
                        cleaned_files[field_name] = metadata
                cleaned[key] = cleaned_files
            else:
                cleaned[key] = scrub_payload(item)
        return cleaned
    if isinstance(value, list):
        return [scrub_payload(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped[0] in '[{':
            try:
                return scrub_payload(json.loads(stripped))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
    return value


def scrub_operation_logs(apps, schema_editor):
    OperationLog = apps.get_model('audit', 'OperationLog')
    pending_updates = []

    for operation_log in OperationLog.objects.exclude(
        request_data__isnull=True
    ).iterator(chunk_size=500):
        cleaned = scrub_payload(operation_log.request_data)
        if cleaned != operation_log.request_data:
            operation_log.request_data = cleaned
            pending_updates.append(operation_log)
        if len(pending_updates) >= 500:
            OperationLog.objects.bulk_update(
                pending_updates, ['request_data'], batch_size=500
            )
            pending_updates.clear()

    if pending_updates:
        OperationLog.objects.bulk_update(
            pending_updates, ['request_data'], batch_size=500
        )


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0003_operationlog_user_agent'),
    ]

    operations = [
        migrations.RunPython(scrub_operation_logs, migrations.RunPython.noop),
    ]
