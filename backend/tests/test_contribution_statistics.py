"""
N24 贡献度统计测试
- 按成员、按项目统计贡献得分
"""
import pytest
from decimal import Decimal

from apps.contributions.models import Contribution

STATS_URL = '/api/v1/contributions/statistics/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def make_contribution(user, project, weight=10, status='approved', ctype='task_complete', period='2026-Q1'):
    """创建贡献记录的辅助函数"""
    return Contribution.objects.create(
        user=user,
        project=project,
        contribution_type=ctype,
        weight=Decimal(str(weight)),
        status=status,
        period=period,
        content='测试贡献',
    )


@pytest.mark.api
@pytest.mark.django_db
class TestContributionStatistics:
    """贡献度统计 API 测试"""

    def test_statistics_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.get(STATS_URL)
        assert resp.status_code == 401

    def test_statistics_empty(self, member_client):
        """无数据时返回零值"""
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == 0
        assert data['total_score'] == 0.0

    def test_statistics_total(self, member_client, make_user, make_project):
        """贡献总数"""
        user = make_user(email='cs_user@test.com')
        project = make_project(leader=user)
        make_contribution(user, project, status='approved')
        make_contribution(user, project, status='pending')
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == 2
        assert data['approved_count'] == 1

    def test_statistics_total_score(self, member_client, make_user, make_project):
        """总贡献得分（仅已通过）"""
        user = make_user(email='cs_score@test.com')
        project = make_project(leader=user)
        make_contribution(user, project, weight=10, status='approved')
        make_contribution(user, project, weight=20, status='approved')
        make_contribution(user, project, weight=5, status='pending')
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total_score'] == 30.0

    def test_statistics_by_member(self, member_client, make_user, make_project):
        """按成员统计"""
        u1 = make_user(email='cs_m1@test.com')
        u2 = make_user(email='cs_m2@test.com')
        project = make_project()
        make_contribution(u1, project, weight=15, status='approved')
        make_contribution(u2, project, weight=25, status='approved')
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        member_stats = {m['user_id']: m for m in data['by_member']}
        assert member_stats[u1.id]['contribution_score'] == 15.0
        assert member_stats[u2.id]['contribution_score'] == 25.0

    def test_statistics_by_project(self, member_client, make_user, make_project):
        """按项目统计"""
        user = make_user(email='cs_proj@test.com')
        p1 = make_project()
        p2 = make_project()
        make_contribution(user, p1, weight=30, status='approved')
        make_contribution(user, p2, weight=40, status='approved')
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        proj_stats = {p['project_id']: p for p in data['by_project']}
        assert proj_stats[p1.id]['contribution_score'] == 30.0
        assert proj_stats[p2.id]['contribution_score'] == 40.0

    def test_statistics_by_type(self, member_client, make_user, make_project):
        """按类型统计"""
        user = make_user(email='cs_type@test.com')
        project = make_project(leader=user)
        make_contribution(user, project, weight=10, ctype='task_complete', status='approved')
        make_contribution(user, project, weight=20, ctype='competition', status='approved')
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['by_type']['task_complete']['count'] == 1
        assert data['by_type']['task_complete']['score'] == 10.0
        assert data['by_type']['competition']['count'] == 1

    def test_statistics_filter_by_project(self, member_client, make_user, make_project):
        """按项目筛选"""
        user = make_user(email='cs_filter@test.com')
        p1 = make_project()
        p2 = make_project()
        make_contribution(user, p1, weight=10, status='approved')
        make_contribution(user, p2, weight=20, status='approved')
        resp = member_client.get(f'{STATS_URL}?project={p1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == 1
