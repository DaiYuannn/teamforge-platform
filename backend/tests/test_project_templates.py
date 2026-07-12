"""
N07 项目模板模块测试
- 创建 / 列表 / 更新 / 删除
- instantiate：从模板实例化项目（创建里程碑与任务）
- 权限：普通成员只读，老师/管理员可写
"""
import pytest

from apps.projects.template_models import ProjectTemplate
from apps.projects.models import Project
from apps.projects.milestone_models import Milestone
from apps.tasks.models import Task

TEMPLATE_URL = '/api/v1/projects/templates/'


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
class TestProjectTemplateAPI:
    """项目模板 API 测试"""

    def test_create_template(self, teacher_client):
        """老师可以创建模板，自动设置创建人"""
        resp = teacher_client.post(TEMPLATE_URL, {
            'name': '竞赛模板',
            'description': '适用于各类竞赛',
            'category': '竞赛',
            'config': {'milestones': [], 'tasks': []},
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['name'] == '竞赛模板'
        assert data['created_by'] == teacher_client.user.id
        assert data['is_active'] is True

    def test_list_templates(self, member_client):
        """普通成员可以查看模板列表"""
        ProjectTemplate.objects.create(name='可见模板')
        resp = member_client.get(TEMPLATE_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_update_template(self, teacher_client):
        """老师可以更新模板"""
        tpl = ProjectTemplate.objects.create(name='原名')
        resp = teacher_client.patch(f'{TEMPLATE_URL}{tpl.id}/', {
            'name': '新名',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['name'] == '新名'

    def test_delete_template(self, teacher_client):
        """老师可以删除模板"""
        tpl = ProjectTemplate.objects.create(name='待删除')
        resp = teacher_client.delete(f'{TEMPLATE_URL}{tpl.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not ProjectTemplate.objects.filter(id=tpl.id).exists()

    def test_instantiate_creates_project(self, teacher_client, make_user):
        """从模板实例化项目，自动创建里程碑与任务"""
        leader = make_user(email='tpl_leader@test.com', name='模板负责人')
        tpl = ProjectTemplate.objects.create(
            name='实例化模板',
            config={
                'milestones': [
                    {'title': '立项', 'sort_order': 0},
                    {'title': '答辩', 'due_date': '2026-12-31', 'sort_order': 1},
                ],
                'tasks': [
                    {'title': '材料准备', 'priority': 'high'},
                    {'title': '报名提交'},
                ],
            },
        )
        resp = teacher_client.post(f'{TEMPLATE_URL}{tpl.id}/instantiate/', {
            'name': '模板项目',
            'code': 'TPL-0001',
            'leader': leader.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        # 项目已创建
        assert Project.objects.filter(code='TPL-0001').exists()
        # 里程碑已创建
        assert Milestone.objects.filter(project__code='TPL-0001').count() == 2
        # 任务已创建
        assert Task.objects.filter(project__code='TPL-0001').count() == 2
        assert data['_instantiated']['milestones'] == 2
        assert data['_instantiated']['tasks'] == 2

    def test_instantiate_inactive_template_fails(self, teacher_client, make_user):
        """停用模板无法实例化"""
        leader = make_user(email='tpl_leader2@test.com')
        tpl = ProjectTemplate.objects.create(name='停用模板', is_active=False)
        resp = teacher_client.post(f'{TEMPLATE_URL}{tpl.id}/instantiate/', {
            'name': '失败项目',
            'code': 'TPL-FAIL',
            'leader': leader.id,
        }, format='json')
        assert resp.status_code in (400, 403), resp.json()

    def test_member_cannot_create_template(self, member_client):
        """普通成员不能创建模板"""
        resp = member_client.post(TEMPLATE_URL, {
            'name': '成员尝试创建',
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_member_cannot_instantiate(self, member_client, make_user):
        """普通成员不能实例化模板"""
        leader = make_user(email='tpl_leader3@test.com')
        tpl = ProjectTemplate.objects.create(name='成员实例化测试')
        resp = member_client.post(f'{TEMPLATE_URL}{tpl.id}/instantiate/', {
            'name': '成员项目',
            'code': 'TPL-MEM',
            'leader': leader.id,
        }, format='json')
        assert resp.status_code in (401, 403)


@pytest.mark.model
@pytest.mark.django_db
class TestProjectTemplateModel:
    """项目模板模型测试"""

    def test_default_values(self):
        """默认值"""
        tpl = ProjectTemplate.objects.create(name='默认模板')
        assert tpl.is_active is True
        assert tpl.config == {}
        assert tpl.category == ''

    def test_config_json_field(self):
        """config 支持复杂 JSON 结构"""
        config = {'milestones': [{'title': 'M1'}], 'tasks': [{'title': 'T1'}]}
        tpl = ProjectTemplate.objects.create(name='JSON模板', config=config)
        tpl.refresh_from_db()
        assert tpl.config == config
        assert tpl.config['milestones'][0]['title'] == 'M1'
