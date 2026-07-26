"""
N61: 无障碍 / API 可访问性报告测试
- GET /api/v1/common/accessibility/report/
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestAccessibilityReport:
    """无障碍报告测试"""

    def test_report_requires_auth(self, api_client):
        """报告需认证"""
        resp = api_client.get('/api/v1/common/accessibility/report/')
        assert resp.status_code in (401, 403)

    def test_report_returns_checks(self, teacher_client):
        """返回检查清单"""
        resp = teacher_client.get('/api/v1/common/accessibility/report/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'checks' in data
        assert isinstance(data['checks'], list)
        assert len(data['checks']) >= 4

    def test_includes_error_responses_check(self, teacher_client):
        """包含统一错误响应检查"""
        data = extract_data(teacher_client.get('/api/v1/common/accessibility/report/'))
        items = [c['item'] for c in data['checks']]
        assert 'error_responses' in items

    def test_includes_list_pagination_check(self, teacher_client):
        """包含列表分页检查"""
        data = extract_data(teacher_client.get('/api/v1/common/accessibility/report/'))
        items = [c['item'] for c in data['checks']]
        assert 'list_pagination' in items

    def test_includes_write_requires_auth_check(self, teacher_client):
        """包含写操作认证检查"""
        data = extract_data(teacher_client.get('/api/v1/common/accessibility/report/'))
        items = [c['item'] for c in data['checks']]
        assert 'write_requires_auth' in items

    def test_includes_destructive_requires_permissions_check(self, teacher_client):
        """包含破坏性操作权限检查"""
        data = extract_data(teacher_client.get('/api/v1/common/accessibility/report/'))
        items = [c['item'] for c in data['checks']]
        assert 'destructive_requires_permissions' in items

    def test_each_check_has_passed_field(self, teacher_client):
        """每项检查包含 passed 字段"""
        data = extract_data(teacher_client.get('/api/v1/common/accessibility/report/'))
        for check in data['checks']:
            assert 'passed' in check
            assert isinstance(check['passed'], bool)

    def test_report_returns_score(self, teacher_client):
        """返回可访问性评分"""
        data = extract_data(teacher_client.get('/api/v1/common/accessibility/report/'))
        assert 'score' in data
        assert 0 <= data['score'] <= 100
        assert data['passed'] + data['failed'] == data['total']
