"""
N35: 登录安全增强测试
- 登录尝试记录
- IP 连续失败 5 次/30 分钟自动封禁 1 小时
- 封禁 IP 登录被拒绝
"""
from datetime import timedelta
from django.utils import timezone

import pytest

from apps.users.login_security_models import LoginAttempt, IPBlocklist
from apps.users.login_security_services import (
    is_ip_blocked, record_login_attempt, FAILED_THRESHOLD,
)


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestLoginSecurity:
    """登录安全测试"""

    def test_successful_login_recorded(self, api_client, make_user):
        """成功登录被记录"""
        make_user(email='sec@test.com', password='TestPass123!')
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'sec@test.com', 'password': 'TestPass123!',
        }, format='json')
        assert resp.status_code == 200
        assert LoginAttempt.objects.filter(email='sec@test.com', is_success=True).exists()

    def test_failed_password_recorded(self, api_client, make_user):
        """密码错误被记录"""
        make_user(email='sec@test.com', password='TestPass123!')
        api_client.post('/api/v1/auth/login/', {
            'email': 'sec@test.com', 'password': 'Wrong!',
        }, format='json')
        attempt = LoginAttempt.objects.filter(email='sec@test.com').first()
        assert attempt is not None
        assert attempt.is_success is False
        assert attempt.failure_reason == '密码错误'

    def test_nonexistent_user_recorded(self, api_client):
        """不存在用户被记录"""
        api_client.post('/api/v1/auth/login/', {
            'email': 'ghost@test.com', 'password': 'TestPass123!',
        }, format='json')
        attempt = LoginAttempt.objects.filter(email='ghost@test.com').first()
        assert attempt is not None
        assert attempt.is_success is False
        assert attempt.failure_reason == '用户不存在'

    def test_user_agent_recorded(self, api_client, make_user):
        """User-Agent 被记录"""
        make_user(email='ua@test.com', password='TestPass123!')
        api_client.post(
            '/api/v1/auth/login/',
            {'email': 'ua@test.com', 'password': 'Wrong!'},
            format='json',
            HTTP_USER_AGENT='Mozilla/5.0 TestAgent',
        )
        attempt = LoginAttempt.objects.get(email='ua@test.com')
        assert 'TestAgent' in attempt.user_agent

    def test_auto_block_after_threshold(self):
        """连续失败达到阈值自动封禁 IP"""
        ip = '203.0.113.5'
        for _ in range(FAILED_THRESHOLD):
            record_login_attempt('x@test.com', ip, 'UA', False, '密码错误')
        assert IPBlocklist.objects.filter(ip_address=ip).exists()
        assert is_ip_blocked(ip) is True

    def test_below_threshold_not_blocked(self):
        """未达阈值不封禁"""
        ip = '203.0.113.6'
        for _ in range(FAILED_THRESHOLD - 1):
            record_login_attempt('x@test.com', ip, 'UA', False, '密码错误')
        assert not IPBlocklist.objects.filter(ip_address=ip).exists()
        assert is_ip_blocked(ip) is False

    def test_blocked_ip_login_rejected(self, api_client, make_user):
        """被封禁 IP 登录被拒绝"""
        make_user(email='block@test.com', password='TestPass123!')
        # 手动封禁
        IPBlocklist.objects.create(
            ip_address='127.0.0.1',
            reason='测试封禁',
            blocked_until=timezone.now() + timedelta(hours=1),
        )
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'block@test.com', 'password': 'TestPass123!',
        }, format='json')
        assert resp.status_code == 403
        # 应记录一次失败尝试
        assert LoginAttempt.objects.filter(
            email='block@test.com', failure_reason='IP 已被封禁',
        ).exists()

    def test_expired_block_not_active(self):
        """过期封禁不生效"""
        ip = '203.0.113.7'
        IPBlocklist.objects.create(
            ip_address=ip,
            reason='过期封禁',
            blocked_until=timezone.now() - timedelta(hours=1),
        )
        assert is_ip_blocked(ip) is False

    def test_success_does_not_trigger_block(self):
        """成功登录不触发封禁"""
        ip = '203.0.113.8'
        for _ in range(FAILED_THRESHOLD + 2):
            record_login_attempt('ok@test.com', ip, 'UA', True, '')
        assert not IPBlocklist.objects.filter(ip_address=ip).exists()
        assert is_ip_blocked(ip) is False

    def test_block_duration_one_hour(self):
        """封禁时长为 1 小时"""
        ip = '203.0.113.9'
        for _ in range(FAILED_THRESHOLD):
            record_login_attempt('x@test.com', ip, 'UA', False, '密码错误')
        block = IPBlocklist.objects.get(ip_address=ip)
        assert block.blocked_until is not None
        # 封禁截止时间应在 1 小时前后（允许少许误差）
        delta = block.blocked_until - timezone.now()
        assert 55 * 60 <= delta.total_seconds() <= 65 * 60

    def test_distinct_ip_independent(self):
        """不同 IP 失败互不影响"""
        for i in range(FAILED_THRESHOLD):
            record_login_attempt('x@test.com', f'203.0.113.{10 + i}', 'UA', False, '密码错误')
        # 每个 IP 只失败 1 次，都不应被封禁
        assert IPBlocklist.objects.count() == 0
