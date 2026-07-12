"""
N37: 敏感操作确认测试
- POST /api/v1/common/confirmations/generate/
- POST /api/v1/common/confirmations/verify/
"""
from datetime import timedelta
from django.utils import timezone

import pytest

from apps.common.confirmation_models import SensitiveConfirmation


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestSensitiveConfirmation:
    """敏感操作确认测试"""

    def test_generate_token(self, member_client):
        """生成确认令牌"""
        resp = member_client.post('/api/v1/common/confirmations/generate/', {
            'confirm_type': 'delete_project',
            'target_type': 'project', 'target_id': '1',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['token']
        assert data['is_confirmed'] is False
        assert data['expires_at']
        c = SensitiveConfirmation.objects.get(token=data['token'])
        assert c.user == member_client.user
        assert c.confirm_type == 'delete_project'

    def test_generate_invalid_type(self, member_client):
        """非法确认类型"""
        resp = member_client.post('/api/v1/common/confirmations/generate/', {
            'confirm_type': 'invalid_type',
        }, format='json')
        assert resp.status_code in (400, 422)

    def test_verify_token_success(self, member_client):
        """校验令牌通过"""
        gen = member_client.post('/api/v1/common/confirmations/generate/', {
            'confirm_type': 'bulk_delete',
        }, format='json')
        token = extract_data(gen)['token']
        resp = member_client.post('/api/v1/common/confirmations/verify/', {
            'token': token,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        c = SensitiveConfirmation.objects.get(token=token)
        assert c.is_confirmed is True

    def test_verify_token_not_found(self, member_client):
        """令牌不存在"""
        resp = member_client.post('/api/v1/common/confirmations/verify/', {
            'token': 'nonexistent-token',
        }, format='json')
        assert resp.status_code == 404

    def test_verify_token_already_used(self, member_client):
        """令牌已被使用"""
        gen = member_client.post('/api/v1/common/confirmations/generate/', {
            'confirm_type': 'data_export',
        }, format='json')
        token = extract_data(gen)['token']
        member_client.post('/api/v1/common/confirmations/verify/', {'token': token}, format='json')
        resp = member_client.post('/api/v1/common/confirmations/verify/', {'token': token}, format='json')
        assert resp.status_code in (400, 409)

    def test_verify_token_expired(self, member_client):
        """令牌过期"""
        c = SensitiveConfirmation.objects.create(
            user=member_client.user, confirm_type='password_change',
            token='expired-token-123',
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        resp = member_client.post('/api/v1/common/confirmations/verify/', {
            'token': c.token,
        }, format='json')
        assert resp.status_code in (400, 410)

    def test_verify_token_other_user_forbidden(self, member_client, make_user, api_client):
        """非令牌所属用户不可校验"""
        c = SensitiveConfirmation.objects.create(
            user=member_client.user, confirm_type='delete_finance',
            token='other-user-token',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        other = make_user(email='other@test.com')
        from rest_framework_simplejwt.tokens import RefreshToken
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(other).access_token}')
        resp = api_client.post('/api/v1/common/confirmations/verify/', {
            'token': c.token,
        }, format='json')
        assert resp.status_code == 403

    def test_token_unique(self, member_client):
        """令牌唯一"""
        tokens = set()
        for _ in range(3):
            gen = member_client.post('/api/v1/common/confirmations/generate/', {
                'confirm_type': 'data_export',
            }, format='json')
            tokens.add(extract_data(gen)['token'])
        assert len(tokens) == 3

    def test_unauthenticated_blocked(self, api_client):
        """未认证不可访问"""
        resp = api_client.post('/api/v1/common/confirmations/generate/', {
            'confirm_type': 'data_export',
        }, format='json')
        assert resp.status_code in (401, 403)
