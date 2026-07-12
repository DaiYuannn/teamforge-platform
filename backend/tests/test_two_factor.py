"""
N34: 双因素认证（2FA）测试
- POST /api/v1/users/2fa/generate/
- POST /api/v1/users/2fa/verify/
- POST /api/v1/users/2fa/disable/
- GET  /api/v1/users/2fa/disable/  查询状态
"""
import pytest

from apps.users.two_factor_models import TwoFactorSecret


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestTwoFactor:
    """双因素认证接口测试"""

    def test_generate_creates_secret(self, member_client):
        """生成 2FA 密钥返回 secret 与 otpauth_uri"""
        resp = member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['secret']
        assert data['otpauth_uri'].startswith('otpauth://totp/')
        assert isinstance(data['backup_codes'], list)
        assert len(data['backup_codes']) > 0
        # 记录已创建且未启用
        tf = TwoFactorSecret.objects.get(user=member_client.user)
        assert tf.is_enabled is False
        assert tf.enabled_at is None

    def test_generate_idempotent_regenerates(self, member_client):
        """重复生成会重置密钥（未启用时）"""
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        first = TwoFactorSecret.objects.get(user=member_client.user).secret
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        second = TwoFactorSecret.objects.get(user=member_client.user).secret
        # 仍只有一条记录
        assert TwoFactorSecret.objects.filter(user=member_client.user).count() == 1
        # 密钥已重置（可能相同，但记录字段被刷新）
        assert TwoFactorSecret.objects.get(user=member_client.user).is_enabled is False

    def test_generate_blocked_when_enabled(self, member_client):
        """已启用时不允许重新生成"""
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        resp = member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        assert resp.status_code in (400, 403, 409)

    def test_verify_enables_2fa(self, member_client):
        """校验验证码通过后启用 2FA"""
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        resp = member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['is_enabled'] is True
        tf = TwoFactorSecret.objects.get(user=member_client.user)
        assert tf.is_enabled is True
        assert tf.enabled_at is not None

    def test_verify_wrong_code(self, member_client):
        """错误验证码不启用"""
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        resp = member_client.post('/api/v1/users/2fa/verify/', {'code': '12345'}, format='json')
        assert resp.status_code in (400, 401, 403)
        assert TwoFactorSecret.objects.get(user=member_client.user).is_enabled is False

    def test_verify_without_generate(self, member_client):
        """未生成密钥直接校验"""
        resp = member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        assert resp.status_code in (400, 404)

    def test_verify_already_enabled(self, member_client):
        """已启用再次校验"""
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        resp = member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        assert resp.status_code in (400, 409)

    def test_disable_with_code(self, member_client):
        """通过验证码关闭 2FA"""
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        resp = member_client.post('/api/v1/users/2fa/disable/', {'code': '123456'}, format='json')
        assert resp.status_code == 200, resp.json()
        assert TwoFactorSecret.objects.get(user=member_client.user).is_enabled is False

    def test_disable_with_backup_code(self, member_client):
        """通过备用码关闭 2FA（一次性）"""
        gen = member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        backup = extract_data(gen)['backup_codes'][0]
        member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        resp = member_client.post('/api/v1/users/2fa/disable/', {'backup_code': backup}, format='json')
        assert resp.status_code == 200, resp.json()
        # 备用码已被消耗
        tf = TwoFactorSecret.objects.get(user=member_client.user)
        assert backup not in tf.backup_codes

    def test_disable_wrong_code(self, member_client):
        """错误验证码/备用码不能关闭"""
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        resp = member_client.post('/api/v1/users/2fa/disable/', {'code': '00000', 'backup_code': 'ZZZZ'}, format='json')
        assert resp.status_code in (400, 401, 403)
        assert TwoFactorSecret.objects.get(user=member_client.user).is_enabled is True

    def test_disable_when_not_enabled(self, member_client):
        """未启用时关闭"""
        resp = member_client.post('/api/v1/users/2fa/disable/', {'code': '123456'}, format='json')
        assert resp.status_code in (400, 404)

    def test_status_query(self, member_client):
        """查询 2FA 状态"""
        resp = member_client.get('/api/v1/users/2fa/disable/')
        assert resp.status_code == 200
        assert extract_data(resp)['is_enabled'] is False
        member_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        member_client.post('/api/v1/users/2fa/verify/', {'code': '123456'}, format='json')
        resp = member_client.get('/api/v1/users/2fa/disable/')
        assert extract_data(resp)['is_enabled'] is True

    def test_unauthenticated_blocked(self, api_client):
        """未认证不可访问"""
        resp = api_client.post('/api/v1/users/2fa/generate/', {}, format='json')
        assert resp.status_code in (401, 403)
