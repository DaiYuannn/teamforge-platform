"""
N18 比赛时间线测试
- 返回比赛关键节点的时间线事件
"""
import pytest
from datetime import date

from apps.competitions.models import Competition

TIMELINE_URL = '/api/v1/competitions/timeline/'


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
    }
    defaults.update(kwargs)
    return Competition.objects.create(project=project, **defaults)


@pytest.mark.api
@pytest.mark.django_db
class TestCompetitionTimeline:
    """比赛时间线 API 测试"""

    def test_timeline_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.get(TIMELINE_URL)
        assert resp.status_code == 401

    def test_timeline_missing_param(self, member_client):
        """缺少 competition 参数"""
        resp = member_client.get(TIMELINE_URL)
        assert resp.status_code == 400

    def test_timeline_not_found(self, member_client):
        """比赛不存在"""
        resp = member_client.get(f'{TIMELINE_URL}?competition=99999')
        assert resp.status_code == 400

    def test_timeline_basic(self, member_client, make_project):
        """基本时间线返回"""
        project = make_project()
        comp = make_competition(
            project,
            name='挑战杯',
            register_date=date(2026, 3, 1),
            defense_date=date(2026, 5, 15),
            result_date=date(2026, 6, 30),
        )
        resp = member_client.get(f'{TIMELINE_URL}?competition={comp.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['competition_name'] == '挑战杯'
        assert len(data['events']) == 3

    def test_timeline_sorted_by_date(self, member_client, make_project):
        """事件按日期排序"""
        project = make_project()
        comp = make_competition(
            project,
            register_date=date(2026, 5, 1),
            defense_date=date(2026, 3, 1),
            result_date=date(2026, 4, 1),
        )
        resp = member_client.get(f'{TIMELINE_URL}?competition={comp.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        dates = [e['date'] for e in data['events']]
        assert dates == sorted(dates)

    def test_timeline_event_types(self, member_client, make_project):
        """包含正确的事件类型"""
        project = make_project()
        comp = make_competition(
            project,
            register_date=date(2026, 3, 1),
            review_date=date(2026, 4, 1),
            defense_date=date(2026, 5, 1),
        )
        resp = member_client.get(f'{TIMELINE_URL}?competition={comp.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        event_types = [e['event_type'] for e in data['events']]
        assert 'registration' in event_types
        assert 'review' in event_types
        assert 'defense' in event_types

    def test_timeline_no_dates(self, member_client, make_project):
        """无日期的比赛返回空事件列表"""
        project = make_project()
        comp = make_competition(project)
        resp = member_client.get(f'{TIMELINE_URL}?competition={comp.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['events']) == 0
