"""
N39: 安全扫描测试
- GET /api/v1/common/security-scan/
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestSecurityScan:
    """安全扫描测试"""

    def test_scan_returns_checks(self, member_client):
        """返回安全检查清单"""
        resp = member_client.get('/api/v1/common/security-scan/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'checks' in data
        assert isinstance(data['checks'], list)
        assert data['total'] == len(data['checks'])
        assert data['passed'] + data['failed'] == data['total']

    def test_scan_includes_secret_key_check(self, member_client):
        """包含 SECRET_KEY 检查项"""
        data = extract_data(member_client.get('/api/v1/common/security-scan/'))
        items = [c['item'] for c in data['checks']]
        assert 'secret_key_from_env' in items

    def test_scan_includes_debug_check(self, member_client):
        """包含 DEBUG 检查项"""
        data = extract_data(member_client.get('/api/v1/common/security-scan/'))
        items = [c['item'] for c in data['checks']]
        assert 'debug_disabled' in items
        # 测试环境 DEBUG=False
        debug_check = next(c for c in data['checks'] if c['item'] == 'debug_disabled')
        assert debug_check['passed'] is True

    def test_scan_includes_https_check(self, member_client):
        """包含 HTTPS 检查项"""
        data = extract_data(member_client.get('/api/v1/common/security-scan/'))
        items = [c['item'] for c in data['checks']]
        assert 'https_recommended' in items

    def test_scan_includes_password_policy(self, member_client):
        """包含密码策略检查项"""
        data = extract_data(member_client.get('/api/v1/common/security-scan/'))
        items = [c['item'] for c in data['checks']]
        assert 'password_policy' in items

    def test_scan_includes_cors_check(self, member_client):
        """包含 CORS 检查项"""
        data = extract_data(member_client.get('/api/v1/common/security-scan/'))
        items = [c['item'] for c in data['checks']]
        assert 'cors_restricted' in items

    def test_scan_returns_score(self, member_client):
        """返回安全评分"""
        data = extract_data(member_client.get('/api/v1/common/security-scan/'))
        assert 'score' in data
        assert 0 <= data['score'] <= 100

    def test_scan_each_check_has_severity(self, member_client):
        """每项检查包含严重级别"""
        data = extract_data(member_client.get('/api/v1/common/security-scan/'))
        for check in data['checks']:
            assert 'severity' in check
            assert check['severity'] in ('high', 'medium', 'low')
            assert 'passed' in check
            assert 'title' in check

    def test_unauthenticated_blocked(self, api_client):
        """未认证不可访问"""
        resp = api_client.get('/api/v1/common/security-scan/')
        assert resp.status_code in (401, 403)
