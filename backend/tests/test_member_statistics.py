"""
N13 成员统计分析测试
- 任务完成率、项目参与数、贡献得分、出勤率
"""
import pytest

from apps.users.models import User
from apps.tasks.models import Task
from apps.projects.models import Project, ProjectMember
from apps.contributions.models import Contribution

STATS_URL = '/api/v1/users/statistics/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestMemberStatistics:
    """成员统计 API 测试"""

    def test_statistics_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.get(STATS_URL)
        assert resp.status_code == 401

    def test_statistics_empty(self, member_client):
        """无数据时返回空列表"""
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert isinstance(data, list)

    def test_statistics_basic(self, member_client, make_user, make_project, make_task):
        """基本统计：任务完成率"""
        user = make_user(email='stat_user@test.com')
        project = make_project(leader=user)
        # 2 个任务，1 个完成
        make_task(project=project, assignee=user, status='done')
        make_task(project=project, assignee=user, status='todo')

        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        stat = next(s for s in data if s['user_id'] == user.id)
        assert stat['total_tasks'] == 2
        assert stat['completed_tasks'] == 1
        assert stat['task_completion_rate'] == 50.0

    def test_statistics_project_participation(self, member_client, make_user, make_project):
        """项目参与数"""
        user = make_user(email='proj_user@test.com')
        p1 = make_project(leader=user)
        p2 = make_project()
        ProjectMember.objects.create(project=p2, user=user, role_in_project='participant')

        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        stat = next(s for s in data if s['user_id'] == user.id)
        assert stat['project_participation_count'] == 2

    def test_statistics_contribution_score(self, member_client, make_user, make_project):
        """贡献得分（已通过的权重之和）"""
        user = make_user(email='contrib_user@test.com')
        project = make_project(leader=user)
        Contribution.objects.create(
            user=user, project=project, contribution_type='task_complete',
            status='approved', weight=10,
        )
        Contribution.objects.create(
            user=user, project=project, contribution_type='task_complete',
            status='pending', weight=5,
        )

        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        stat = next(s for s in data if s['user_id'] == user.id)
        assert stat['contribution_score'] == 10.0

    def test_statistics_attendance_rate(self, member_client, make_user, make_project, make_task):
        """出勤率（已完成+进行中占总任务比例）"""
        user = make_user(email='attend_user@test.com')
        project = make_project(leader=user)
        make_task(project=project, assignee=user, status='done')
        make_task(project=project, assignee=user, status='doing')
        make_task(project=project, assignee=user, status='cancelled')

        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        stat = next(s for s in data if s['user_id'] == user.id)
        assert stat['total_tasks'] == 3
        # done + doing = 2, total = 3, rate = 66.67
        assert stat['attendance_rate'] == pytest.approx(66.67, abs=0.1)

    def test_statistics_filter_by_user(self, member_client, make_user, make_project, make_task):
        """按 user 筛选"""
        user1 = make_user(email='filter1@test.com')
        user2 = make_user(email='filter2@test.com')
        project = make_project(leader=user1)
        make_task(project=project, assignee=user1, status='done')
        make_task(project=project, assignee=user2, status='todo')

        resp = member_client.get(f'{STATS_URL}?user={user1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 1
        assert data[0]['user_id'] == user1.id

    def test_statistics_no_tasks_zero_rate(self, member_client, make_user):
        """无任务时完成率和出勤率为 0"""
        user = make_user(email='notask@test.com')

        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        stat = next(s for s in data if s['user_id'] == user.id)
        assert stat['task_completion_rate'] == 0.0
        assert stat['attendance_rate'] == 0.0
        assert stat['total_tasks'] == 0

    def test_statistics_collaborative_tasks(self, member_client, make_user, make_project, make_task):
        """协作者任务也计入统计"""
        user = make_user(email='collab_user@test.com')
        project = make_project()
        task = make_task(project=project, assignee=project.leader, status='done')
        task.collaborators.add(user)

        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        stat = next(s for s in data if s['user_id'] == user.id)
        assert stat['total_tasks'] >= 1
        assert stat['completed_tasks'] >= 1
