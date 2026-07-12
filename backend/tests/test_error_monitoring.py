"""
N57: 前端错误监控测试
- POST /api/v1/common/error-logs/   创建（任意已登录用户）
- GET  /api/v1/common/error-logs/   列表（仅管理员/教师）
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


def extract_results(response):
    """从（可能分页的）响应中提取结果列表"""
    data = extract_data(response)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    if isinstance(data, list):
        return data
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestErrorLogCreate:
    """错误日志创建测试"""

    def test_create_error_log(self, member_client):
        """普通用户可上报错误日志"""
        resp = member_client.post('/api/v1/common/error-logs/', {
            'level': 'error',
            'message': '前端崩溃：未捕获的异常',
            'stack': 'Error: at foo.js:10',
            'url': 'http://localhost/dashboard',
            'user_agent': 'Mozilla/5.0',
            'metadata': {'component': 'Dashboard'},
        }, format='json')
        assert resp.status_code == 201, resp.json()
        data = extract_data(resp)
        assert data['level'] == 'error'
        assert data['message'] == '前端崩溃：未捕获的异常'
        assert data['id'] > 0

    def test_create_records_user(self, member_client):
        """创建时自动记录当前用户"""
        resp = member_client.post('/api/v1/common/error-logs/', {
            'message': '测试错误',
        }, format='json')
        assert resp.status_code == 201
        data = extract_data(resp)
        assert data['user'] == member_client.user.id
        assert data['user_name'] == member_client.user.name

    def test_create_default_level_is_error(self, member_client):
        """未提供 level 时默认 error"""
        resp = member_client.post('/api/v1/common/error-logs/', {
            'message': '默认级别',
        }, format='json')
        assert resp.status_code == 201
        assert extract_data(resp)['level'] == 'error'

    def test_create_with_warning_level(self, member_client):
        """可上报 warning 级别"""
        resp = member_client.post('/api/v1/common/error-logs/', {
            'level': 'warning',
            'message': '告警信息',
        }, format='json')
        assert resp.status_code == 201
        assert extract_data(resp)['level'] == 'warning'

    def test_create_invalid_level(self, member_client):
        """非法 level 返回 400"""
        resp = member_client.post('/api/v1/common/error-logs/', {
            'level': 'critical',
            'message': '非法级别',
        }, format='json')
        assert resp.status_code == 400

    def test_create_requires_message(self, member_client):
        """缺少 message 返回 400"""
        resp = member_client.post('/api/v1/common/error-logs/', {
            'level': 'error',
        }, format='json')
        assert resp.status_code == 400

    def test_create_unauthenticated_blocked(self, api_client):
        """未认证不可上报"""
        resp = api_client.post('/api/v1/common/error-logs/', {
            'message': '匿名错误',
        }, format='json')
        assert resp.status_code in (401, 403)


@pytest.mark.api
@pytest.mark.django_db
class TestErrorLogList:
    """错误日志列表测试"""

    def _make_log(self, make_user, level='error', message='err'):
        """直接通过 ORM 创建错误日志（避免共享 api_client 冲突）"""
        from apps.common.error_models import ErrorLog
        import itertools
        if not hasattr(self, '_counter'):
            self._counter = itertools.count(1)
        n = next(self._counter)
        user = make_user(email=f'log_user_{n}@test.com')
        return ErrorLog.objects.create(
            level=level,
            message=message,
            user=user,
        )

    def test_admin_can_list(self, admin_client, make_user):
        """管理员可查看列表"""
        self._make_log(make_user, message='管理员错误')
        resp = admin_client.get('/api/v1/common/error-logs/')
        assert resp.status_code == 200, resp.json()

    def test_list_returns_results(self, admin_client, make_user):
        """列表返回已上报的错误日志"""
        self._make_log(make_user, level='error', message='错误1')
        self._make_log(make_user, level='warning', message='警告1')
        resp = admin_client.get('/api/v1/common/error-logs/')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert isinstance(results, list)
        assert len(results) >= 2

    def test_list_filter_by_level(self, admin_client, make_user):
        """可按 level 过滤"""
        self._make_log(make_user, level='error', message='E')
        self._make_log(make_user, level='warning', message='W')
        resp = admin_client.get('/api/v1/common/error-logs/?level=warning')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['level'] == 'warning' for r in results)
        assert len(results) >= 1

    def test_member_cannot_list(self, member_client):
        """普通成员不可查看列表"""
        resp = member_client.get('/api/v1/common/error-logs/')
        assert resp.status_code == 403

    def test_list_unauthenticated_blocked(self, api_client):
        """未认证不可查看列表"""
        resp = api_client.get('/api/v1/common/error-logs/')
        assert resp.status_code in (401, 403)

    def test_list_ordered_by_created_at_desc(self, admin_client, make_user):
        """列表按创建时间倒序"""
        import time
        self._make_log(make_user, message='first')
        time.sleep(0.01)
        self._make_log(make_user, message='second')
        resp = admin_client.get('/api/v1/common/error-logs/')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 2
        assert results[0]['created_at'] >= results[1]['created_at']
