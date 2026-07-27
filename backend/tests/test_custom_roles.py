"""
N36: 自定义角色测试
- /api/v1/users/roles/             角色 CRUD
- /api/v1/users/role-assignments/  角色分配 CRUD
"""
import pytest
from rest_framework.test import APIClient

from apps.finance.models import FinanceBudget
from apps.exports.custom_report_models import CustomReport
from apps.users.role_models import CustomRole, UserRoleAssignment


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestCustomRole:
    """自定义角色接口测试"""

    def test_list_roles(self, admin_client):
        """管理员列出角色"""
        CustomRole.objects.create(name='开发者', permissions=['task.read'])
        resp = admin_client.get('/api/v1/users/roles/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert any(r['name'] == '开发者' for r in items)

    def test_create_role(self, admin_client):
        """管理员创建角色"""
        resp = admin_client.post('/api/v1/users/roles/', {
            'name': '测试角色', 'description': '描述',
            'permissions': ['project.create', 'task.delete'],
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        role = CustomRole.objects.get(name='测试角色')
        assert role.permissions == ['project.create', 'task.delete']
        assert role.is_system is False

    def test_create_role_duplicate_name(self, admin_client):
        """角色名唯一"""
        CustomRole.objects.create(name='重复角色')
        resp = admin_client.post('/api/v1/users/roles/', {'name': '重复角色'}, format='json')
        assert resp.status_code in (400, 409)

    def test_member_cannot_create_role(self, member_client):
        """普通成员不能创建角色"""
        resp = member_client.post('/api/v1/users/roles/', {'name': '越权'}, format='json')
        assert resp.status_code in (403, 401)

    def test_member_can_list_roles(self, member_client):
        """普通成员可查看角色"""
        CustomRole.objects.create(name='可读角色')
        resp = member_client.get('/api/v1/users/roles/')
        assert resp.status_code == 200

    def test_update_role(self, admin_client):
        """更新角色"""
        role = CustomRole.objects.create(name='待更新')
        resp = admin_client.patch(f'/api/v1/users/roles/{role.id}/', {
            'description': '新描述',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        role.refresh_from_db()
        assert role.description == '新描述'

    def test_delete_role(self, admin_client):
        """删除普通角色"""
        role = CustomRole.objects.create(name='待删除')
        resp = admin_client.delete(f'/api/v1/users/roles/{role.id}/')
        assert resp.status_code == 200
        assert not CustomRole.objects.filter(id=role.id).exists()

    def test_cannot_delete_system_role(self, admin_client):
        """系统角色不可删除"""
        role = CustomRole.objects.create(name='系统角色', is_system=True)
        resp = admin_client.delete(f'/api/v1/users/roles/{role.id}/')
        assert resp.status_code in (400, 403)
        assert CustomRole.objects.filter(id=role.id).exists()


@pytest.mark.api
@pytest.mark.django_db
class TestUserRoleAssignment:
    """用户角色分配测试"""

    def test_assign_role(self, admin_client, make_user):
        """管理员分配角色"""
        role = CustomRole.objects.create(name='负责人', permissions=['project.manage'])
        user = make_user(email='assign@test.com')
        resp = admin_client.post('/api/v1/users/role-assignments/', {
            'user': user.id, 'role': role.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['assigned_by'] == admin_client.user.id

    def test_assign_role_with_project(self, admin_client, make_user, make_project):
        """分配项目级角色"""
        role = CustomRole.objects.create(name='项目成员')
        user = make_user(email='p@test.com')
        project = make_project()
        resp = admin_client.post('/api/v1/users/role-assignments/', {
            'user': user.id, 'role': role.id, 'project': project.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        assert UserRoleAssignment.objects.filter(
            user=user, role=role, project=project,
        ).exists()

    def test_duplicate_assignment_rejected(self, admin_client, make_user):
        """重复分配被拒"""
        role = CustomRole.objects.create(name='唯一角色')
        user = make_user(email='dup@test.com')
        admin_client.post('/api/v1/users/role-assignments/', {
            'user': user.id, 'role': role.id,
        }, format='json')
        resp = admin_client.post('/api/v1/users/role-assignments/', {
            'user': user.id, 'role': role.id,
        }, format='json')
        assert resp.status_code in (400, 409)

    def test_list_assignments(self, admin_client, make_user):
        """列出角色分配"""
        role = CustomRole.objects.create(name='列出角色')
        user = make_user(email='list@test.com')
        UserRoleAssignment.objects.create(user=user, role=role, assigned_by=admin_client.user)
        resp = admin_client.get('/api/v1/users/role-assignments/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert any(a['user'] == user.id for a in items)

    def test_delete_assignment(self, admin_client, make_user):
        """撤销角色分配"""
        role = CustomRole.objects.create(name='撤销角色')
        user = make_user(email='del@test.com')
        assignment = UserRoleAssignment.objects.create(
            user=user, role=role, assigned_by=admin_client.user,
        )
        resp = admin_client.delete(f'/api/v1/users/role-assignments/{assignment.id}/')
        assert resp.status_code in (200, 204)
        assert not UserRoleAssignment.objects.filter(id=assignment.id).exists()


def assigned_client(user, permissions, *, project=None, name='runtime-role'):
    role = CustomRole.objects.create(name=name, permissions=permissions)
    UserRoleAssignment.objects.create(user=user, role=role, project=project)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.api
@pytest.mark.django_db
class TestCustomRoleEffects:
    def test_global_project_create_permission_creates_project(self, make_user):
        user = make_user(email='project-create@test.com')
        client = assigned_client(user, ['project.create'])

        response = client.post('/api/v1/projects/', {
            'name': 'Created by custom role',
            'code': 'CUSTOM-CREATE',
            'leader': user.id,
        }, format='json')

        assert response.status_code == 201, response.json()

    def test_project_manage_is_limited_to_assigned_project(
        self, make_user, make_project
    ):
        user = make_user(email='project-manager@test.com')
        allowed = make_project(name='Allowed project')
        denied = make_project(name='Denied project')
        client = assigned_client(user, ['project.manage'], project=allowed)

        allowed_response = client.patch(
            f'/api/v1/projects/{allowed.id}/', {'intro': 'updated'}, format='json'
        )
        denied_response = client.patch(
            f'/api/v1/projects/{denied.id}/', {'intro': 'forbidden'}, format='json'
        )

        assert allowed_response.status_code == 200, allowed_response.json()
        assert denied_response.status_code == 403

    def test_task_create_and_manage_are_distinct_and_project_scoped(
        self, make_user, make_project, make_task
    ):
        user = make_user(email='task-role@test.com')
        allowed = make_project(name='Task role project')
        denied = make_project(name='Other task project')
        create_client = assigned_client(
            user, ['task.create'], project=allowed, name='task-creator'
        )

        created = create_client.post('/api/v1/tasks/', {
            'project': allowed.id,
            'title': 'Custom role task',
            'assignee': user.id,
        }, format='json')
        rejected = create_client.post('/api/v1/tasks/', {
            'project': denied.id,
            'title': 'Cross-project task',
            'assignee': user.id,
        }, format='json')

        assert created.status_code == 201, created.json()
        assert rejected.status_code == 403

        task = make_task(project=allowed)
        manage_client = assigned_client(
            user, ['task.manage'], project=allowed, name='task-manager'
        )
        updated = manage_client.patch(
            f'/api/v1/tasks/{task.id}/', {'description': 'managed'}, format='json'
        )
        assert updated.status_code == 200, updated.json()

    def test_finance_manage_is_limited_to_assigned_project(
        self, make_user, make_project
    ):
        user = make_user(email='finance-role@test.com')
        allowed = make_project(name='Finance role project')
        denied = make_project(name='Other finance project')
        allowed_budget = FinanceBudget.objects.create(project=allowed)
        denied_budget = FinanceBudget.objects.create(project=denied)
        client = assigned_client(user, ['finance.manage'], project=allowed)

        allowed_response = client.patch(
            f'/api/v1/finance/budgets/{allowed_budget.id}/',
            {'period': '2026-Q3'}, format='json',
        )
        denied_response = client.patch(
            f'/api/v1/finance/budgets/{denied_budget.id}/',
            {'period': '2026-Q4'}, format='json',
        )

        assert allowed_response.status_code == 200, allowed_response.json()
        assert denied_response.status_code == 403

    def test_member_permissions_require_global_assignment(self, make_user):
        viewer = make_user(email='member-viewer@test.com')
        target = make_user(email='member-target@test.com')
        view_client = assigned_client(viewer, ['member.view'], name='member-viewer')
        assert view_client.get('/api/v1/users/').status_code == 200

        manager = make_user(email='member-manager@test.com')
        manage_client = assigned_client(
            manager, ['member.manage'], name='member-manager'
        )
        response = manage_client.patch(
            f'/api/v1/users/{target.id}/', {'name': 'Managed user'}, format='json'
        )
        assert response.status_code == 200, response.json()

    def test_report_permissions_expose_and_manage_other_reports(
        self, make_user
    ):
        owner = make_user(email='report-role-owner@test.com')
        report = CustomReport.objects.create(
            name='Shared report', report_type='summary', config={}, created_by=owner
        )
        viewer = make_user(email='report-role-viewer@test.com')
        view_client = assigned_client(viewer, ['report.view'], name='report-viewer')
        assert view_client.get(
            f'/api/v1/exports/custom-reports/{report.id}/'
        ).status_code == 200

        manager = make_user(email='report-role-manager@test.com')
        manage_client = assigned_client(
            manager, ['report.manage'], name='report-manager'
        )
        response = manage_client.patch(
            f'/api/v1/exports/custom-reports/{report.id}/',
            {'description': 'managed'}, format='json',
        )
        assert response.status_code == 200, response.json()
