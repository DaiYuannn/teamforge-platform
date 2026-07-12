"""
N06 项目风险模块测试
- 创建 / 列表 / 更新 / 关闭 / 删除
- 权限：普通成员只读，老师/管理员/项目负责人可写
"""
import pytest

from apps.projects.risk_models import ProjectRisk

RISK_URL = '/api/v1/projects/risks/'


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
class TestProjectRiskAPI:
    """项目风险 API 测试"""

    def test_create_risk(self, teacher_client, make_project):
        """老师可以创建风险，自动设置识别人"""
        project = make_project(leader=teacher_client.user)
        resp = teacher_client.post(RISK_URL, {
            'project': project.id,
            'title': '进度风险',
            'level': 'high',
            'description': '可能延期',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['title'] == '进度风险'
        assert data['level'] == 'high'
        assert data['identified_by'] == teacher_client.user.id

    def test_list_risks(self, member_client, make_project):
        """普通成员可以查看风险列表"""
        project = make_project()
        ProjectRisk.objects.create(project=project, title='可见风险')
        resp = member_client.get(RISK_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1

    def test_filter_risks_by_level(self, member_client, make_project):
        """按级别筛选风险"""
        project = make_project()
        ProjectRisk.objects.create(project=project, title='高风险', level='high')
        ProjectRisk.objects.create(project=project, title='低风险', level='low')
        resp = member_client.get(f'{RISK_URL}?level=high')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['level'] == 'high' for r in results)

    def test_update_risk(self, teacher_client, make_project):
        """老师可以更新风险"""
        project = make_project(leader=teacher_client.user)
        risk = ProjectRisk.objects.create(project=project, title='原风险')
        resp = teacher_client.patch(f'{RISK_URL}{risk.id}/', {
            'status': 'mitigating',
            'mitigation_plan': '增加人手',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == 'mitigating'

    def test_resolve_risk(self, teacher_client, make_project):
        """关闭风险"""
        project = make_project(leader=teacher_client.user)
        risk = ProjectRisk.objects.create(project=project, title='待关闭')
        resp = teacher_client.post(f'{RISK_URL}{risk.id}/resolve/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == 'closed'
        assert data['resolved_at'] is not None

    def test_delete_risk(self, teacher_client, make_project):
        """老师可以删除风险"""
        project = make_project(leader=teacher_client.user)
        risk = ProjectRisk.objects.create(project=project, title='待删除')
        resp = teacher_client.delete(f'{RISK_URL}{risk.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not ProjectRisk.objects.filter(id=risk.id).exists()

    def test_member_cannot_create_risk(self, member_client, make_project):
        """普通成员不能创建风险"""
        project = make_project()
        resp = member_client.post(RISK_URL, {
            'project': project.id,
            'title': '成员尝试创建',
        }, format='json')
        assert resp.status_code in (401, 403)


@pytest.mark.model
@pytest.mark.django_db
class TestProjectRiskModel:
    """项目风险模型测试"""

    def test_default_values(self, make_project):
        """默认级别 medium、状态 open"""
        risk = ProjectRisk.objects.create(project=make_project(), title='默认风险')
        assert risk.level == ProjectRisk.Level.MEDIUM
        assert risk.status == ProjectRisk.Status.OPEN
        assert risk.resolved_at is None

    def test_resolve_sets_time(self, make_project):
        """resolve 设置解决时间"""
        risk = ProjectRisk.objects.create(project=make_project(), title='解决测试')
        risk.resolve()
        assert risk.status == ProjectRisk.Status.CLOSED
        assert risk.resolved_at is not None

    def test_level_choices(self, make_project):
        """级别枚举完整"""
        assert ProjectRisk.Level.LOW == 'low'
        assert ProjectRisk.Level.MEDIUM == 'medium'
        assert ProjectRisk.Level.HIGH == 'high'
        assert ProjectRisk.Level.CRITICAL == 'critical'
