"""
N19 比赛对比测试
- 多个比赛横向对比
"""
import pytest
from datetime import date

from apps.competitions.models import Competition

COMPARISON_URL = '/api/v1/competitions/comparison/'


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
class TestCompetitionComparison:
    """比赛对比 API 测试"""

    def test_comparison_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.get(COMPARISON_URL)
        assert resp.status_code == 401

    def test_comparison_missing_ids(self, member_client):
        """缺少 ids 参数"""
        resp = member_client.get(COMPARISON_URL)
        assert resp.status_code == 400

    def test_comparison_single_id(self, member_client, make_project):
        """仅一个 ID 时需报错（至少 2 个）"""
        project = make_project()
        comp = make_competition(project, name='比赛A')
        resp = member_client.get(f'{COMPARISON_URL}?ids={comp.id}')
        assert resp.status_code == 400

    def test_comparison_basic(self, member_client, make_project):
        """基本对比"""
        project = make_project()
        c1 = make_competition(project, name='比赛A', level='school', is_awarded=True)
        c2 = make_competition(project, name='比赛B', level='national', is_promoted=True)
        resp = member_client.get(f'{COMPARISON_URL}?ids={c1.id},{c2.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == 2
        assert len(data['items']) == 2

    def test_comparison_summary(self, member_client, make_project):
        """对比汇总统计"""
        project = make_project()
        c1 = make_competition(project, name='比赛A', is_awarded=True, is_promoted=True)
        c2 = make_competition(project, name='比赛B', is_awarded=False, is_promoted=True)
        c3 = make_competition(project, name='比赛C', is_awarded=False, is_promoted=False)
        resp = member_client.get(f'{COMPARISON_URL}?ids={c1.id},{c2.id},{c3.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['awarded_count'] == 1
        assert data['promoted_count'] == 2

    def test_comparison_too_many_ids(self, member_client, make_project):
        """超过 10 个 ID 报错"""
        project = make_project()
        ids = []
        for i in range(11):
            c = make_competition(project, name=f'比赛{i}')
            ids.append(str(c.id))
        resp = member_client.get(f'{COMPARISON_URL}?ids={",".join(ids)}')
        assert resp.status_code == 400

    def test_comparison_invalid_ids(self, member_client):
        """非法 ids 参数"""
        resp = member_client.get(f'{COMPARISON_URL}?ids=abc,def')
        assert resp.status_code == 400
