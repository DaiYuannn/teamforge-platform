"""
任务 API 测试 - 验证 P01 修复
- priority 字段
- start_date 字段
- CRUD 操作
"""
import pytest
from django.utils import timezone


@pytest.mark.api
@pytest.mark.django_db
class TestTaskAPI:
    """任务 API 测试"""

    def _make_project_for(self, client, make_project):
        """创建以 client.user 为负责人的项目"""
        from apps.projects.models import ProjectMember
        project = make_project(leader=client.user)
        return project

    def test_create_task_with_priority(self, teacher_client, make_project):
        """创建任务时带优先级"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '测试任务-高优先级',
            'assignee': project.leader.id,
            'priority': 'high',
            'deadline': '2026-12-31T23:59:59',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()()
        data = resp.json().get('data', resp.json())
        assert data['priority'] == 'high'
        assert data['priority_display'] == '高'

    def test_create_task_default_priority(self, teacher_client, make_project):
        """创建任务默认优先级为 medium"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '测试任务-默认优先级',
            'assignee': project.leader.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()()
        data = resp.json().get('data', resp.json())
        assert data['priority'] == 'medium'
        assert data['priority_display'] == '中'

    def test_create_task_with_start_date(self, teacher_client, make_project):
        """创建任务时带开始时间"""
        project = make_project(leader=teacher_client.user)
        start = timezone.now().isoformat()
        resp = teacher_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '测试任务-带开始时间',
            'assignee': project.leader.id,
            'start_date': start,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()()
        data = resp.json().get('data', resp.json())
        assert data['start_date'] is not None

    def test_task_list_includes_priority(self, member_client, make_task):
        """任务列表包含 priority 字段"""
        task = make_task(priority='urgent')
        resp = member_client.get('/api/v1/tasks/')
        assert resp.status_code == 200
        data = resp.json().get('data', resp.json())
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) > 0
        assert 'priority' in results[0]
        assert 'priority_display' in results[0]

    def test_task_list_includes_start_date(self, member_client, make_task):
        """任务列表包含 start_date 字段"""
        task = make_task()
        resp = member_client.get('/api/v1/tasks/')
        assert resp.status_code == 200
        data = resp.json().get('data', resp.json())
        results = data.get('results', data) if isinstance(data, dict) else data
        assert 'start_date' in results[0]

    def test_filter_by_priority(self, member_client, make_task):
        """按优先级筛选"""
        make_task(priority='low')
        make_task(priority='urgent')
        resp = member_client.get('/api/v1/tasks/?priority=urgent')
        assert resp.status_code == 200
        data = resp.json().get('data', resp.json())
        results = data.get('results', data) if isinstance(data, dict) else data
        assert all(r['priority'] == 'urgent' for r in results)

    def test_update_task_priority(self, teacher_client, make_project, make_task):
        """更新任务优先级"""
        project = make_project(leader=teacher_client.user)
        task = make_task(project=project, priority='low')
        resp = teacher_client.patch(f'/api/v1/tasks/{task.id}/', {
            'priority': 'urgent',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()()
        data = resp.json().get('data', resp.json())
        assert data['priority'] == 'urgent'

    def test_member_cannot_create_task(self, member_client, make_project):
        """普通成员不能创建任务"""
        project = make_project()
        resp = member_client.post('/api/v1/tasks/', {
            'project': project.id,
            'title': '成员尝试创建任务',
            'assignee': project.leader.id,
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_member_can_view_tasks(self, member_client, make_task):
        """普通成员可以查看任务"""
        make_task()
        resp = member_client.get('/api/v1/tasks/')
        assert resp.status_code == 200

    def test_task_no_due_date_field(self, member_client, make_task):
        """任务 API 不返回 due_date 字段"""
        task = make_task()
        resp = member_client.get(f'/api/v1/tasks/{task.id}/')
        assert resp.status_code == 200
        data = resp.json().get('data', resp.json())
        assert 'due_date' not in data
        assert 'deadline' in data

