"""
N05 项目里程碑模块测试
- 创建 / 列表 / 更新 / 完成切换 / 删除
- 权限：普通成员只读，老师/管理员/项目负责人可写
"""
import pytest

from apps.projects.milestone_models import Milestone

MILESTONE_URL = '/api/v1/projects/milestones/'


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
class TestMilestoneAPI:
    """项目里程碑 API 测试"""

    def test_create_milestone(self, teacher_client, make_project):
        """老师可以创建里程碑"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post(MILESTONE_URL, {
            'project': project.id,
            'title': '里程碑1',
            'due_date': '2026-12-31',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['title'] == '里程碑1'
        assert data['is_completed'] is False

    def test_list_milestones(self, member_client, make_project):
        """普通成员可以查看里程碑列表"""
        project = make_project()
        Milestone.objects.create(project=project, title='可见里程碑')
        resp = member_client.get(MILESTONE_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_filter_milestones_by_project(self, member_client, make_project):
        """按项目筛选里程碑"""
        p1 = make_project()
        p2 = make_project()
        Milestone.objects.create(project=p1, title='A')
        Milestone.objects.create(project=p2, title='B')
        resp = member_client.get(f'{MILESTONE_URL}?project={p1.id}')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['project'] == p1.id for r in results)

    def test_update_milestone(self, teacher_client, make_project):
        """老师可以更新里程碑"""
        project = make_project(leader=teacher_client.user)
        ms = Milestone.objects.create(project=project, title='原标题')
        resp = teacher_client.patch(f'{MILESTONE_URL}{ms.id}/', {
            'title': '新标题',
            'description': '更新描述',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['title'] == '新标题'

    def test_toggle_milestone_complete(self, teacher_client, make_project):
        """切换里程碑完成状态"""
        project = make_project(leader=teacher_client.user)
        ms = Milestone.objects.create(project=project, title='待完成')
        resp = teacher_client.post(f'{MILESTONE_URL}{ms.id}/toggle/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['is_completed'] is True
        assert data['completed_at'] is not None

    def test_delete_milestone(self, teacher_client, make_project):
        """老师可以删除里程碑"""
        project = make_project(leader=teacher_client.user)
        ms = Milestone.objects.create(project=project, title='待删除')
        resp = teacher_client.delete(f'{MILESTONE_URL}{ms.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not Milestone.objects.filter(id=ms.id).exists()

    def test_member_cannot_create_milestone(self, member_client, make_project):
        """普通成员不能创建里程碑"""
        project = make_project()
        resp = member_client.post(MILESTONE_URL, {
            'project': project.id,
            'title': '成员尝试创建',
        }, format='json')
        assert resp.status_code in (401, 403)


@pytest.mark.model
@pytest.mark.django_db
class TestMilestoneModel:
    """项目里程碑模型测试"""

    def test_default_values(self, make_project):
        """默认值"""
        ms = Milestone.objects.create(project=make_project(), title='默认')
        assert ms.is_completed is False
        assert ms.sort_order == 0
        assert ms.completed_at is None

    def test_mark_completed(self, make_project):
        """mark_completed 设置完成时间"""
        ms = Milestone.objects.create(project=make_project(), title='完成测试')
        ms.mark_completed()
        assert ms.is_completed is True
        assert ms.completed_at is not None

    def test_related_name_milestones(self, make_project):
        """反向关系 project.milestones 可访问"""
        project = make_project()
        Milestone.objects.create(project=project, title='反向关系')
        assert project.milestones.count() == 1
