"""
N25 贡献度排行榜测试
- 按贡献得分排名的成员列表
"""
import pytest
from decimal import Decimal

from apps.contributions.models import Contribution

LEADERBOARD_URL = '/api/v1/contributions/leaderboard/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def make_contribution(user, project, weight=10, status='approved', period='2026-Q1'):
    """创建贡献记录的辅助函数"""
    return Contribution.objects.create(
        user=user,
        project=project,
        contribution_type='task_complete',
        weight=Decimal(str(weight)),
        status=status,
        period=period,
        content='测试贡献',
    )


@pytest.mark.api
@pytest.mark.django_db
class TestContributionLeaderboard:
    """贡献度排行榜 API 测试"""

    def test_leaderboard_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.get(LEADERBOARD_URL)
        assert resp.status_code == 401

    def test_leaderboard_empty(self, member_client):
        """无数据时返回空"""
        resp = member_client.get(LEADERBOARD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total_members'] == 0
        assert len(data['leaderboard']) == 0

    def test_leaderboard_ranking(self, member_client, make_user, make_project):
        """按贡献得分降序排名"""
        project = make_project()
        u1 = make_user(email='lb1@test.com', name='成员A')
        u2 = make_user(email='lb2@test.com', name='成员B')
        u3 = make_user(email='lb3@test.com', name='成员C')
        make_contribution(u1, project, weight=10, status='approved')
        make_contribution(u2, project, weight=30, status='approved')
        make_contribution(u3, project, weight=20, status='approved')

        resp = member_client.get(LEADERBOARD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        lb = data['leaderboard']
        assert lb[0]['user_id'] == u2.id
        assert lb[0]['rank'] == 1
        assert lb[0]['contribution_score'] == 30.0
        assert lb[1]['user_id'] == u3.id
        assert lb[1]['rank'] == 2
        assert lb[2]['user_id'] == u1.id
        assert lb[2]['rank'] == 3

    def test_leaderboard_excludes_non_approved(self, member_client, make_user, make_project):
        """仅包含已通过的贡献"""
        project = make_project()
        u1 = make_user(email='lb_pending@test.com')
        make_contribution(u1, project, weight=100, status='pending')
        resp = member_client.get(LEADERBOARD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total_members'] == 0

    def test_leaderboard_filter_by_project(self, member_client, make_user, make_project):
        """按项目筛选"""
        p1 = make_project()
        p2 = make_project()
        u1 = make_user(email='lb_p1@test.com')
        u2 = make_user(email='lb_p2@test.com')
        make_contribution(u1, p1, weight=10, status='approved')
        make_contribution(u2, p2, weight=20, status='approved')
        resp = member_client.get(f'{LEADERBOARD_URL}?project={p1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total_members'] == 1
        assert data['leaderboard'][0]['user_id'] == u1.id

    def test_leaderboard_filter_by_period(self, member_client, make_user, make_project):
        """按周期筛选"""
        project = make_project()
        u1 = make_user(email='lb_period@test.com')
        make_contribution(u1, project, weight=10, status='approved', period='2026-Q1')
        make_contribution(u1, project, weight=20, status='approved', period='2026-Q2')
        resp = member_client.get(f'{LEADERBOARD_URL}?period=2026-Q1')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['leaderboard'][0]['contribution_score'] == 10.0

    def test_leaderboard_limit(self, member_client, make_user, make_project):
        """limit 限制返回数量"""
        project = make_project()
        for i in range(5):
            u = make_user(email=f'lb_limit{i}@test.com')
            make_contribution(u, project, weight=(i + 1) * 10, status='approved')
        resp = member_client.get(f'{LEADERBOARD_URL}?limit=3')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['leaderboard']) == 3

    def test_leaderboard_contribution_count(self, member_client, make_user, make_project):
        """贡献次数统计"""
        project = make_project()
        u1 = make_user(email='lb_count@test.com')
        make_contribution(u1, project, weight=10, status='approved')
        make_contribution(u1, project, weight=15, status='approved')
        resp = member_client.get(LEADERBOARD_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        lb = data['leaderboard']
        assert lb[0]['contribution_count'] == 2
        assert lb[0]['contribution_score'] == 25.0
