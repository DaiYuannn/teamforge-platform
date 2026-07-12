"""
API 冒烟测试 - 验证各模块接口可用性
检测 NaN、undefined、字段缺失等问题
统一响应格式: {code: 0, message: 'success', data: ...}
"""
import math
import pytest


def extract_data(response):
    """从统一响应格式中提取 data"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
class TestAPISmoke:
    """各模块 API 冒烟测试"""

    def test_users_list(self, admin_client):
        """用户列表"""
        resp = admin_client.get('/api/v1/users/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert 'results' in data or isinstance(data, list)

    def test_users_list_member_forbidden(self, member_client):
        """普通成员不能访问用户管理"""
        resp = member_client.get('/api/v1/users/')
        assert resp.status_code in (401, 403)

    def test_projects_list(self, member_client):
        """项目列表"""
        resp = member_client.get('/api/v1/projects/')
        assert resp.status_code == 200

    def test_tasks_list(self, member_client):
        """任务列表"""
        resp = member_client.get('/api/v1/tasks/')
        assert resp.status_code == 200

    def test_competitions_list(self, member_client):
        """比赛列表"""
        resp = member_client.get('/api/v1/competitions/')
        assert resp.status_code == 200

    def test_members_list(self, member_client):
        """成员列表"""
        resp = member_client.get('/api/v1/members/')
        assert resp.status_code == 200

    def test_finance_list(self, member_client):
        """经费列表 - 所有登录成员可访问"""
        resp = member_client.get('/api/v1/finance/')
        assert resp.status_code == 200

    def test_files_list(self, member_client):
        """文件列表"""
        resp = member_client.get('/api/v1/files/')
        assert resp.status_code == 200

    def test_contributions_list(self, member_client):
        """贡献列表"""
        resp = member_client.get('/api/v1/contributions/')
        assert resp.status_code == 200

    def test_notifications_list(self, member_client):
        """通知列表"""
        resp = member_client.get('/api/v1/notifications/')
        assert resp.status_code == 200

    def test_audit_list(self, admin_client):
        """操作日志列表"""
        resp = admin_client.get('/api/v1/audit/operation-logs/')
        assert resp.status_code == 200

    def test_audit_list_member_forbidden(self, member_client):
        """普通成员不能访问操作日志"""
        resp = member_client.get('/api/v1/audit/operation-logs/')
        assert resp.status_code in (401, 403)

    def test_integrations_list(self, admin_client):
        """集成配置列表"""
        resp = admin_client.get('/api/v1/integrations/configs/')
        assert resp.status_code == 200

    def test_integrations_member_forbidden(self, member_client):
        """普通成员不能访问集成配置"""
        resp = member_client.get('/api/v1/integrations/configs/')
        assert resp.status_code in (401, 403)

    def test_dashboard(self, member_client):
        """Dashboard 数据"""
        resp = member_client.get('/api/v1/dashboard/')
        assert resp.status_code == 200

    def test_dashboard_timeline(self, member_client):
        """时间线"""
        resp = member_client.get('/api/v1/dashboard/timeline/')
        assert resp.status_code == 200

    def test_dashboard_calendar(self, member_client):
        """日历"""
        resp = member_client.get('/api/v1/dashboard/calendar/')
        assert resp.status_code == 200

    def test_dashboard_gantt(self, member_client):
        """甘特图"""
        resp = member_client.get('/api/v1/dashboard/gantt/')
        assert resp.status_code == 200

    def test_ip_list(self, member_client):
        """知识产权列表"""
        resp = member_client.get('/api/v1/intellectual-property/')
        assert resp.status_code == 200

    def test_sensitive_list(self, member_client):
        """敏感资料列表"""
        resp = member_client.get('/api/v1/sensitive/')
        assert resp.status_code == 200

    def test_imports_list(self, admin_client):
        """导入历史"""
        resp = admin_client.get('/api/v1/imports/history/')
        assert resp.status_code in (200, 404)

    def test_exports_list(self, admin_client):
        """导出接口可用（需要 type 参数）"""
        resp = admin_client.get('/api/v1/exports/')
        assert resp.status_code in (200, 400, 404)


@pytest.mark.api
class TestNoNaNUndefined:
    """检测 NaN/undefined 等异常值"""

    def _check_no_nan(self, data, path=''):
        """递归检查数据中无 NaN/undefined"""
        if isinstance(data, dict):
            for k, v in data.items():
                assert v != 'NaN', f'发现 NaN 字符串: {path}.{k}'
                assert v != 'undefined', f'发现 undefined 字符串: {path}.{k}'
                self._check_no_nan(v, f'{path}.{k}')
        elif isinstance(data, list):
            for i, v in enumerate(data):
                self._check_no_nan(v, f'{path}[{i}]')
        elif isinstance(data, float):
            assert not math.isnan(data), f'发现 NaN: {path}'
            assert not math.isinf(data), f'发现 Inf: {path}'

    def test_dashboard_no_nan(self, admin_client):
        """Dashboard 数据无 NaN"""
        resp = admin_client.get('/api/v1/dashboard/')
        assert resp.status_code == 200
        self._check_no_nan(resp.json())

    def test_projects_no_nan(self, admin_client, make_project):
        """项目数据无 NaN"""
        make_project()
        resp = admin_client.get('/api/v1/projects/')
        assert resp.status_code == 200
        self._check_no_nan(resp.json())


@pytest.mark.permission
class TestPermissionMatrix:
    """权限矩阵测试"""

    def test_member_cannot_access_user_management(self, member_client):
        """普通成员不能访问用户管理"""
        resp = member_client.get('/api/v1/users/')
        assert resp.status_code in (401, 403)

    def test_member_cannot_access_audit_logs(self, member_client):
        """普通成员不能访问操作日志"""
        resp = member_client.get('/api/v1/audit/operation-logs/')
        assert resp.status_code in (401, 403)

    def test_member_cannot_access_integrations(self, member_client):
        """普通成员不能访问集成配置"""
        resp = member_client.get('/api/v1/integrations/configs/')
        assert resp.status_code in (401, 403)

    def test_teacher_can_access_audit_logs(self, teacher_client):
        """老师可以访问操作日志"""
        resp = teacher_client.get('/api/v1/audit/operation-logs/')
        assert resp.status_code == 200

    def test_admin_can_access_all(self, admin_client):
        """管理员可以访问所有模块"""
        urls = [
            '/api/v1/users/',
            '/api/v1/audit/operation-logs/',
            '/api/v1/integrations/configs/',
            '/api/v1/projects/',
            '/api/v1/tasks/',
            '/api/v1/finance/',
        ]
        for url in urls:
            resp = admin_client.get(url)
            assert resp.status_code == 200, f'管理员访问 {url} 失败: {resp.status_code}'

    def test_unauthenticated_blocked(self, api_client):
        """未认证访问全部被拦截"""
        urls = [
            '/api/v1/users/',
            '/api/v1/projects/',
            '/api/v1/tasks/',
            '/api/v1/finance/',
            '/api/v1/files/',
            '/api/v1/sensitive/',
        ]
        for url in urls:
            resp = api_client.get(url)
            assert resp.status_code == 401, f'未认证访问 {url} 未被拦截: {resp.status_code}'
