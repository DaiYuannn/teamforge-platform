"""
N16 成员成长记录测试
- 成长记录 CRUD、权限、唯一约束、排序
"""
import pytest
from decimal import Decimal

from apps.users.growth_models import MemberGrowth

GROWTH_URL = '/api/v1/users/growth/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def extract_results(resp):
    data = extract_data(resp)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    if isinstance(data, list):
        return data
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestMemberGrowthAPI:
    """成员成长记录 API 测试"""

    def test_create_growth(self, teacher_client, make_user):
        """老师可以创建成长记录"""
        user = make_user(email='growth_user@test.com')
        resp = teacher_client.post(GROWTH_URL, {
            'user': user.id,
            'period': '2026-Q1',
            'project_count': 3,
            'task_count': 15,
            'contribution_score': '85.50',
            'skill_count': 5,
            'notes': '表现优秀',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['period'] == '2026-Q1'
        assert data['project_count'] == 3
        assert data['task_count'] == 15

    def test_list_growth(self, member_client, make_user):
        """普通成员可以查看成长记录"""
        user = make_user(email='list_growth@test.com')
        MemberGrowth.objects.create(user=user, period='2026-Q1', task_count=10)
        resp = member_client.get(GROWTH_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_filter_growth_by_user(self, member_client, make_user):
        """按用户筛选成长记录"""
        u1 = make_user(email='growth_u1@test.com')
        u2 = make_user(email='growth_u2@test.com')
        MemberGrowth.objects.create(user=u1, period='2026-Q1')
        MemberGrowth.objects.create(user=u2, period='2026-Q1')
        resp = member_client.get(f'{GROWTH_URL}?user={u1.id}')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['user'] == u1.id for r in results)

    def test_filter_growth_by_period(self, member_client, make_user):
        """按周期筛选成长记录"""
        user = make_user(email='growth_period@test.com')
        MemberGrowth.objects.create(user=user, period='2026-Q1')
        MemberGrowth.objects.create(user=user, period='2026-Q2')
        resp = member_client.get(f'{GROWTH_URL}?period=2026-Q1')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['period'] == '2026-Q1' for r in results)

    def test_update_growth(self, teacher_client, make_user):
        """老师可以更新成长记录"""
        user = make_user(email='update_growth@test.com')
        growth = MemberGrowth.objects.create(user=user, period='2026-Q1', task_count=5)
        resp = teacher_client.patch(f'{GROWTH_URL}{growth.id}/', {
            'task_count': 20,
            'contribution_score': '95.00',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['task_count'] == 20

    def test_delete_growth(self, teacher_client, make_user):
        """老师可以删除成长记录"""
        user = make_user(email='del_growth@test.com')
        growth = MemberGrowth.objects.create(user=user, period='2026-Q1')
        resp = teacher_client.delete(f'{GROWTH_URL}{growth.id}/')
        assert resp.status_code in (200, 204)
        assert not MemberGrowth.objects.filter(id=growth.id).exists()

    def test_member_cannot_create_growth(self, member_client, make_user):
        """普通成员不能创建成长记录"""
        user = make_user(email='member_growth@test.com')
        resp = member_client.post(GROWTH_URL, {
            'user': user.id,
            'period': '2026-Q1',
        }, format='json')
        assert resp.status_code in (401, 403)


@pytest.mark.model
@pytest.mark.django_db
class TestMemberGrowthModel:
    """成员成长记录模型测试"""

    def test_default_values(self, make_user):
        """默认值"""
        user = make_user(email='model_growth1@test.com')
        growth = MemberGrowth.objects.create(user=user, period='2026-Q1')
        assert growth.project_count == 0
        assert growth.task_count == 0
        assert growth.contribution_score == Decimal('0')
        assert growth.skill_count == 0
        assert growth.notes == ''

    def test_unique_together(self, make_user):
        """同一用户同一周期唯一"""
        user = make_user(email='model_growth2@test.com')
        MemberGrowth.objects.create(user=user, period='2026-Q1')
        with pytest.raises(Exception):
            MemberGrowth.objects.create(user=user, period='2026-Q1')

    def test_ordering(self, make_user):
        """按周期倒序排列"""
        user = make_user(email='model_growth3@test.com')
        MemberGrowth.objects.create(user=user, period='2026-Q1')
        MemberGrowth.objects.create(user=user, period='2026-Q3')
        MemberGrowth.objects.create(user=user, period='2026-Q2')
        records = list(MemberGrowth.objects.all())
        periods = [r.period for r in records]
        assert periods == sorted(periods, reverse=True)

    def test_related_name(self, make_user):
        """反向关系 user.growth_records"""
        user = make_user(email='model_growth4@test.com')
        MemberGrowth.objects.create(user=user, period='2026-Q1')
        assert user.growth_records.count() == 1
