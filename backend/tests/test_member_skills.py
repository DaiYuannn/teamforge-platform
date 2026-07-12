"""
N14 成员技能矩阵测试
- 技能 CRUD、权限、唯一约束、级别校验
"""
import pytest

from apps.users.skill_models import MemberSkill

SKILL_URL = '/api/v1/users/skills/'


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
class TestMemberSkillAPI:
    """成员技能 API 测试"""

    def test_create_skill(self, teacher_client, make_user):
        """老师可以创建技能"""
        user = make_user(email='skill_user@test.com')
        resp = teacher_client.post(SKILL_URL, {
            'user': user.id,
            'name': 'Python',
            'level': 3,
            'certified': True,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['name'] == 'Python'
        assert data['level'] == 3
        assert data['certified'] is True

    def test_list_skills(self, member_client, make_user):
        """普通成员可以查看技能列表"""
        user = make_user(email='list_skill@test.com')
        MemberSkill.objects.create(user=user, name='Java', level=4)
        resp = member_client.get(SKILL_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_filter_skills_by_user(self, member_client, make_user):
        """按用户筛选技能"""
        u1 = make_user(email='skill_u1@test.com')
        u2 = make_user(email='skill_u2@test.com')
        MemberSkill.objects.create(user=u1, name='Go')
        MemberSkill.objects.create(user=u2, name='Rust')
        resp = member_client.get(f'{SKILL_URL}?user={u1.id}')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['user'] == u1.id for r in results)

    def test_update_skill(self, teacher_client, make_user):
        """老师可以更新技能"""
        user = make_user(email='update_skill@test.com')
        skill = MemberSkill.objects.create(user=user, name='Django', level=2)
        resp = teacher_client.patch(f'{SKILL_URL}{skill.id}/', {
            'level': 5,
            'certified': True,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['level'] == 5
        assert data['certified'] is True

    def test_delete_skill(self, teacher_client, make_user):
        """老师可以删除技能"""
        user = make_user(email='del_skill@test.com')
        skill = MemberSkill.objects.create(user=user, name='Flask')
        resp = teacher_client.delete(f'{SKILL_URL}{skill.id}/')
        assert resp.status_code in (200, 204)
        assert not MemberSkill.objects.filter(id=skill.id).exists()

    def test_member_cannot_create_skill(self, member_client, make_user):
        """普通成员不能创建技能"""
        user = make_user(email='member_skill@test.com')
        resp = member_client.post(SKILL_URL, {
            'user': user.id,
            'name': 'C++',
        }, format='json')
        assert resp.status_code in (401, 403)


@pytest.mark.model
@pytest.mark.django_db
class TestMemberSkillModel:
    """成员技能模型测试"""

    def test_default_values(self, make_user):
        """默认值"""
        user = make_user(email='model_skill1@test.com')
        skill = MemberSkill.objects.create(user=user, name='Linux')
        assert skill.level == 1
        assert skill.certified is False

    def test_unique_together(self, make_user):
        """同一用户同一技能名称唯一"""
        user = make_user(email='model_skill2@test.com')
        MemberSkill.objects.create(user=user, name='Docker')
        with pytest.raises(Exception):
            MemberSkill.objects.create(user=user, name='Docker')

    def test_related_name(self, make_user):
        """反向关系 user.skill_matrix"""
        user = make_user(email='model_skill3@test.com')
        MemberSkill.objects.create(user=user, name='Kubernetes')
        assert user.skill_matrix.count() == 1

    def test_str_representation(self, make_user):
        """字符串表示"""
        user = make_user(email='model_skill4@test.com', name='张三')
        skill = MemberSkill.objects.create(user=user, name='React', level=4)
        assert '张三' in str(skill)
        assert 'React' in str(skill)
