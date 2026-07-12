"""
N43: 第三方登录（OAuth）测试
- GET  /api/v1/users/oauth/providers/
- POST /api/v1/users/oauth/callback/
- GET  /api/v1/users/oauth/bindings/
"""
import pytest

from apps.users.oauth_models import OAuthAccount


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestOAuth:
    """第三方登录测试"""

    def test_list_providers(self, api_client):
        """列出支持的提供商（公开）"""
        resp = api_client.get('/api/v1/users/oauth/providers/')
        assert resp.status_code == 200
        data = extract_data(resp)
        providers = [p['provider'] for p in data]
        assert 'github' in providers

    def test_callback_stub_not_implemented(self, api_client):
        """回调桩实现返回 501"""
        resp = api_client.post('/api/v1/users/oauth/callback/', {
            'provider': 'github', 'code': 'abc',
        }, format='json')
        assert resp.status_code == 501

    def test_callback_missing_params(self, api_client):
        """回调缺少参数"""
        resp = api_client.post('/api/v1/users/oauth/callback/', {
            'provider': 'github',
        }, format='json')
        assert resp.status_code in (400, 422)

    def test_bindings_requires_auth(self, api_client):
        """绑定列表需认证"""
        resp = api_client.get('/api/v1/users/oauth/bindings/')
        assert resp.status_code in (401, 403)

    def test_bindings_empty(self, member_client):
        """无绑定时返回空"""
        resp = member_client.get('/api/v1/users/oauth/bindings/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data == []

    def test_bindings_returns_own(self, member_client):
        """返回当前用户的绑定"""
        OAuthAccount.objects.create(
            provider='github', provider_uid='12345', user=member_client.user,
        )
        resp = member_client.get('/api/v1/users/oauth/bindings/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 1
        assert data[0]['provider'] == 'github'

    def test_oauth_account_unique(self, member_client, make_user):
        """provider + provider_uid 唯一"""
        OAuthAccount.objects.create(
            provider='google', provider_uid='u1', user=member_client.user,
        )
        other = make_user(email='oauth-other@test.com')
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            OAuthAccount.objects.create(
                provider='google', provider_uid='u1', user=other,
            )
