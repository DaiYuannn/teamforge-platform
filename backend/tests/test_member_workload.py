"""
N15 成员工作量分析测试
- 任务数、预估工时、项目数
"""
import pytest

from apps.tasks.models import Task
from apps.projects.models import ProjectMember

WORKLOAD_URL = '/api/v1/users/workload/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestMemberWorkload:
    """成员工作量分析测试"""

    def test_workload_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.get(WORKLOAD_URL)
        assert resp.status_code == 401

    def test_workload_empty(self, member_client):
        """无数据时返回空列表"""
        resp = member_client.get(WORKLOAD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert isinstance(data, list)

    def test_workload_task_count(self, member_client, make_user, make_project, make_task):
        """任务数统计"""
        user = make_user(email='wl_user@test.com')
        project = make_project(leader=user)
        make_task(project=project, assignee=user, status='todo')
        make_task(project=project, assignee=user, status='doing')
        make_task(project=project, assignee=user, status='done')

        resp = member_client.get(WORKLOAD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        wl = next(w for w in data if w['user_id'] == user.id)
        assert wl['task_count'] == 3
        # pending = todo + doing = 2 (done excluded)
        assert wl['pending_task_count'] == 2

    def test_workload_estimated_hours(self, member_client, make_user, make_project, make_task):
        """预估工时按优先级计算"""
        user = make_user(email='wl_hours@test.com')
        project = make_project(leader=user)
        # urgent=16, high=8, medium=4, low=2 => total=30
        make_task(project=project, assignee=user, status='todo', priority='urgent')
        make_task(project=project, assignee=user, status='doing', priority='high')
        make_task(project=project, assignee=user, status='todo', priority='medium')
        make_task(project=project, assignee=user, status='todo', priority='low')

        resp = member_client.get(WORKLOAD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        wl = next(w for w in data if w['user_id'] == user.id)
        assert wl['estimated_hours'] == 30

    def test_workload_project_count(self, member_client, make_user, make_project):
        """项目数统计"""
        user = make_user(email='wl_proj@test.com')
        p1 = make_project(leader=user)
        p2 = make_project()
        ProjectMember.objects.create(project=p2, user=user, role_in_project='participant')

        resp = member_client.get(WORKLOAD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        wl = next(w for w in data if w['user_id'] == user.id)
        assert wl['project_count'] == 2

    def test_workload_filter_by_user(self, member_client, make_user, make_project, make_task):
        """按 user 筛选"""
        user1 = make_user(email='wl_filter1@test.com')
        user2 = make_user(email='wl_filter2@test.com')
        project = make_project(leader=user1)
        make_task(project=project, assignee=user1, status='todo')
        make_task(project=project, assignee=user2, status='todo')

        resp = member_client.get(f'{WORKLOAD_URL}?user={user1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 1
        assert data[0]['user_id'] == user1.id

    def test_workload_done_tasks_excluded_from_hours(self, member_client, make_user, make_project, make_task):
        """已完成任务不计入预估工时"""
        user = make_user(email='wl_done@test.com')
        project = make_project(leader=user)
        make_task(project=project, assignee=user, status='done', priority='urgent')
        make_task(project=project, assignee=user, status='todo', priority='medium')

        resp = member_client.get(WORKLOAD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        wl = next(w for w in data if w['user_id'] == user.id)
        # 只有 medium=4 计入
        assert wl['estimated_hours'] == 4
