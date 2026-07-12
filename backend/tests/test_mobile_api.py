"""
P16 移动端适配验证测试
- 关键端点（projects/tasks/notifications/dashboard）返回移动端友好的结构
- 列表端点均应用分页（count/results/page_size 等元数据）
- 统一响应信封 {code, message, data}
"""
import pytest

from apps.notifications.models import Notification


def extract_data(response):
    """从统一响应格式中提取 data"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


def get_envelope(response):
    """返回完整响应信封"""
    return response.json()


def assert_paginated(data):
    """断言 data 为分页结构"""
    assert isinstance(data, dict), f'期望分页字典，实际 {type(data)}'
    assert 'count' in data, '分页结构缺少 count'
    assert 'results' in data, '分页结构缺少 results'
    assert isinstance(data['results'], list), 'results 应为列表'


@pytest.mark.api
@pytest.mark.django_db
class TestProjectListMobile:
    """项目列表移动端适配"""

    def test_projects_paginated_structure(self, auth_client, make_project):
        """项目列表返回分页结构"""
        make_project()
        make_project()
        resp = auth_client.get('/api/v1/projects/')
        assert resp.status_code == 200
        envelope = get_envelope(resp)
        # 统一信封
        assert envelope['code'] == 0
        assert 'data' in envelope
        assert_paginated(envelope['data'])
        assert envelope['data']['count'] >= 2

    def test_projects_results_is_list(self, auth_client, make_project):
        """results 为列表，移动端可遍历"""
        make_project()
        resp = auth_client.get('/api/v1/projects/')
        data = extract_data(resp)
        assert isinstance(data['results'], list)
        assert len(data['results']) >= 1

    def test_projects_pagination_metadata(self, auth_client, make_project):
        """分页元数据完整（count/page_size/total_pages/current_page）"""
        make_project()
        resp = auth_client.get('/api/v1/projects/')
        data = extract_data(resp)
        for key in ('count', 'page_size', 'total_pages', 'current_page'):
            assert key in data, f'缺少分页元数据 {key}'

    def test_projects_empty_paginated(self, auth_client):
        """无数据时仍返回分页结构（移动端可正常渲染空状态）"""
        resp = auth_client.get('/api/v1/projects/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert_paginated(data)
        assert data['count'] == 0
        assert data['results'] == []


@pytest.mark.api
@pytest.mark.django_db
class TestTaskListMobile:
    """任务列表移动端适配"""

    def test_tasks_paginated_structure(self, auth_client, make_task):
        """任务列表返回分页结构"""
        make_task()
        make_task()
        resp = auth_client.get('/api/v1/tasks/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert_paginated(data)
        assert data['count'] >= 2

    def test_tasks_results_is_list(self, auth_client, make_task):
        """任务 results 为列表"""
        make_task()
        resp = auth_client.get('/api/v1/tasks/')
        data = extract_data(resp)
        assert isinstance(data['results'], list)


@pytest.mark.api
@pytest.mark.django_db
class TestNotificationListMobile:
    """通知列表移动端适配"""

    def test_notifications_paginated_structure(self, auth_client):
        """通知列表返回分页结构"""
        user = auth_client.user
        for i in range(3):
            Notification.objects.create(
                recipient=user,
                title=f'移动端通知{i}',
                content='内容',
            )
        resp = auth_client.get('/api/v1/notifications/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert_paginated(data)
        assert data['count'] == 3

    def test_notifications_empty_paginated(self, auth_client):
        """无通知时返回分页空结构"""
        resp = auth_client.get('/api/v1/notifications/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert_paginated(data)
        assert data['count'] == 0


@pytest.mark.api
@pytest.mark.django_db
class TestDashboardMobile:
    """驾驶舱移动端适配"""

    def test_dashboard_structured(self, auth_client):
        """驾驶舱返回结构化聚合数据"""
        resp = auth_client.get('/api/v1/dashboard/')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 聚合数据为字典（非分页），包含移动端需要的各模块
        assert isinstance(data, dict)
        for key in ('project_overview', 'task_overview', 'member_overview'):
            assert key in data, f'驾驶舱缺少 {key}'

    def test_dashboard_envelope(self, auth_client):
        """驾驶舱使用统一响应信封"""
        resp = auth_client.get('/api/v1/dashboard/')
        envelope = get_envelope(resp)
        assert envelope['code'] == 0
        assert envelope['message'] == 'success'


@pytest.mark.api
@pytest.mark.django_db
class TestMobilePaginationControl:
    """移动端分页控制测试"""

    def test_custom_page_size(self, auth_client):
        """移动端可通过 page_size 自定义每页条数"""
        user = auth_client.user
        for i in range(5):
            Notification.objects.create(
                recipient=user,
                title=f'分页通知{i}',
                content='内容',
            )
        resp = auth_client.get('/api/v1/notifications/', {'page_size': 2})
        assert resp.status_code == 200
        data = extract_data(resp)
        # 实际每页返回 2 条，总数 5，共 3 页
        assert len(data['results']) == 2
        assert data['count'] == 5
        assert data['total_pages'] == 3

    def test_next_previous_links(self, auth_client):
        """分页包含 next/previous 链接"""
        user = auth_client.user
        for i in range(3):
            Notification.objects.create(
                recipient=user,
                title=f'链接通知{i}',
                content='内容',
            )
        resp = auth_client.get('/api/v1/notifications/', {'page_size': 2})
        data = extract_data(resp)
        # 第一页应有 next 链接，无 previous
        assert data['next'] is not None
        assert data['previous'] is None

    def test_max_page_size_enforced(self, auth_client):
        """超过最大 page_size 时被限制为 max_page_size，不报错"""
        user = auth_client.user
        for i in range(3):
            Notification.objects.create(
                recipient=user,
                title=f'上限通知{i}',
                content='内容',
            )
        # 请求 1000 条/页，应被限制为 100，3 条全部返回
        resp = auth_client.get('/api/v1/notifications/', {'page_size': 1000})
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['results']) == 3
        assert data['count'] == 3
