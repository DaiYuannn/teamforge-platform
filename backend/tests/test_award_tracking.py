"""
N20 比赛获奖记录追踪测试
- 获奖记录 CRUD（通过 CompetitionViewSet award_tracking action）
"""
import pytest
from datetime import date

from apps.competitions.models import Competition
from apps.competitions.award_models import CompetitionAward


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
class TestAwardTracking:
    """比赛获奖记录追踪 API 测试"""

    def test_get_awards_empty(self, member_client, make_project):
        """获取无获奖记录的比赛"""
        project = make_project()
        comp = make_competition(project)
        resp = member_client.get(f'/api/v1/competitions/{comp.id}/award_tracking/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_award(self, teacher_client, make_project, make_user):
        """老师可以创建获奖记录"""
        project = make_project(leader=teacher_client.user)
        comp = make_competition(project)
        user = make_user(email='recipient@test.com')
        resp = teacher_client.post(f'/api/v1/competitions/{comp.id}/award_tracking/', {
            'award_name': '一等奖',
            'award_level': '校级',
            'award_date': '2026-07-01',
            'recipients': [user.id],
            'notes': '表现突出',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['award_name'] == '一等奖'
        assert data['award_level'] == '校级'

    def test_get_awards_after_create(self, member_client, make_project, make_user):
        """创建后可查询"""
        project = make_project()
        comp = make_competition(project)
        user = make_user(email='recipient2@test.com')
        CompetitionAward.objects.create(
            competition=comp,
            award_name='特等奖',
            award_level='省级',
            award_date=date(2026, 6, 15),
        )
        resp = member_client.get(f'/api/v1/competitions/{comp.id}/award_tracking/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 1
        assert data[0]['award_name'] == '特等奖'

    def test_create_award_with_recipients(self, teacher_client, make_project, make_user):
        """创建带获奖人的记录"""
        project = make_project(leader=teacher_client.user)
        comp = make_competition(project)
        u1 = make_user(email='rec_a@test.com')
        u2 = make_user(email='rec_b@test.com')
        resp = teacher_client.post(f'/api/v1/competitions/{comp.id}/award_tracking/', {
            'award_name': '金奖',
            'recipients': [u1.id, u2.id],
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert len(data['recipient_details']) == 2

    def test_member_cannot_create_award(self, member_client, make_project):
        """普通成员不能创建获奖记录"""
        project = make_project()
        comp = make_competition(project)
        resp = member_client.post(f'/api/v1/competitions/{comp.id}/award_tracking/', {
            'award_name': '二等奖',
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_leader_can_create_award(self, leader_client, make_project):
        """项目负责人可以创建获奖记录"""
        project = make_project(leader=leader_client.user)
        comp = make_competition(project)
        resp = leader_client.post(f'/api/v1/competitions/{comp.id}/award_tracking/', {
            'award_name': '三等奖',
            'award_level': '校级',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()

    def test_award_requires_name(self, teacher_client, make_project):
        """获奖名称必填"""
        project = make_project(leader=teacher_client.user)
        comp = make_competition(project)
        resp = teacher_client.post(f'/api/v1/competitions/{comp.id}/award_tracking/', {
            'award_level': '校级',
        }, format='json')
        assert resp.status_code == 400

    def test_award_recipients_relation(self, make_project, make_user):
        """获奖人 M2M 关系"""
        project = make_project()
        comp = make_competition(project)
        u1 = make_user(email='m2m_a@test.com')
        u2 = make_user(email='m2m_b@test.com')
        award = CompetitionAward.objects.create(
            competition=comp, award_name='银奖',
        )
        award.recipients.set([u1, u2])
        assert award.recipients.count() == 2
        assert u1.competition_awards.count() == 1
