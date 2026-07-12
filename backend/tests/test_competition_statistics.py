"""
N17 比赛统计测试
- 比赛总数、按级别、按状态、获奖率、晋级率
"""
import pytest

from apps.competitions.models import Competition

STATS_URL = '/api/v1/competitions/statistics/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def make_competition(project, **kwargs):
    """创建比赛的辅助函数"""
    defaults = {
        'name': '测试比赛',
        'level': 'school',
        'status': 'preparing',
        'is_promoted': False,
        'is_awarded': False,
    }
    defaults.update(kwargs)
    return Competition.objects.create(project=project, **defaults)


@pytest.mark.api
@pytest.mark.django_db
class TestCompetitionStatistics:
    """比赛统计 API 测试"""

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
        assert data['award_rate'] == 0.0

    def test_statistics_total(self, member_client, make_project):
        """比赛总数"""
        project = make_project()
        make_competition(project, name='比赛1')
        make_competition(project, name='比赛2')
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == 2

    def test_statistics_by_level(self, member_client, make_project):
        """按级别统计"""
        project = make_project()
        make_competition(project, level='school')
        make_competition(project, level='national')
        make_competition(project, level='national')
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['by_level']['school'] == 1
        assert data['by_level']['national'] == 2

    def test_statistics_award_rate(self, member_client, make_project):
        """获奖率"""
        project = make_project()
        make_competition(project, is_awarded=True)
        make_competition(project, is_awarded=True)
        make_competition(project, is_awarded=False)
        make_competition(project, is_awarded=False)
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['awarded_count'] == 2
        assert data['award_rate'] == 50.0

    def test_statistics_promotion_rate(self, member_client, make_project):
        """晋级率"""
        project = make_project()
        make_competition(project, is_promoted=True)
        make_competition(project, is_promoted=False)
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['promoted_count'] == 1
        assert data['promotion_rate'] == 50.0

    def test_statistics_filter_by_project(self, member_client, make_project):
        """按项目筛选"""
        p1 = make_project()
        p2 = make_project()
        make_competition(p1, name='P1比赛')
        make_competition(p2, name='P2比赛')
        resp = member_client.get(f'{STATS_URL}?project={p1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == 1

    def test_statistics_by_status(self, member_client, make_project):
        """按状态统计"""
        project = make_project()
        make_competition(project, status='preparing')
        make_competition(project, status='ongoing')
        make_competition(project, status='completed')
        resp = member_client.get(STATS_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['by_status']['preparing'] == 1
        assert data['by_status']['ongoing'] == 1
        assert data['by_status']['completed'] == 1
