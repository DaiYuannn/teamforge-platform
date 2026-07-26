"""真实团队人员流转、交接和账户偏好契约。"""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.competitions.models import Competition
from apps.projects.models import ProjectMember, ProjectMembershipEvent
from apps.tasks.models import Task
from apps.users.models import User, UserLifecycleEvent, UserPreference


def extract_data(response):
    body = response.json()
    return body.get('data') if isinstance(body, dict) and 'code' in body else body


@pytest.mark.api
@pytest.mark.django_db
class TestMembershipLifecycle:
    def test_non_leader_exit_preserves_project_history(
        self, admin_client, make_user, make_project
    ):
        project = make_project()
        user = make_user(email='leaving-member@test.com')
        membership = ProjectMember.objects.create(
            project=project,
            user=user,
            role_in_project=ProjectMember.RoleInProject.CORE,
        )

        response = admin_client.post(
            f'/api/v1/users/{user.id}/transition/',
            {'status': 'exited', 'reason': '毕业离队', 'handover_notes': '资料已归档'},
            format='json',
        )

        assert response.status_code == 200, response.json()
        user.refresh_from_db()
        membership.refresh_from_db()
        assert user.membership_status == User.MembershipStatus.EXITED
        assert user.is_active is False
        assert membership.status == ProjectMember.Status.EXITED
        assert ProjectMember.objects.filter(pk=membership.pk).exists()
        assert ProjectMembershipEvent.objects.filter(
            membership=membership,
            event_type=ProjectMembershipEvent.EventType.EXITED,
        ).exists()
        assert UserLifecycleEvent.objects.filter(
            user=user,
            to_status=User.MembershipStatus.EXITED,
        ).exists()

    def test_project_leader_exit_requires_valid_handover(
        self, admin_client, make_project
    ):
        project = make_project()
        leader = project.leader

        response = admin_client.post(
            f'/api/v1/users/{leader.id}/transition/',
            {'status': 'exited', 'reason': '毕业离队'},
            format='json',
        )

        assert response.status_code == 400
        leader.refresh_from_db()
        project.refresh_from_db()
        assert leader.membership_status == User.MembershipStatus.ACTIVE
        assert project.leader_id == leader.id

    def test_project_leader_handover_changes_owner_and_keeps_old_membership(
        self, admin_client, make_user, make_project
    ):
        project = make_project()
        old_leader = project.leader
        successor = make_user(email='successor@test.com')
        successor_membership = ProjectMember.objects.create(
            project=project,
            user=successor,
            role_in_project=ProjectMember.RoleInProject.CORE,
        )

        response = admin_client.post(
            f'/api/v1/users/{old_leader.id}/transition/',
            {
                'status': 'exited',
                'reason': '毕业离队',
                'handover_to': successor.id,
                'handover_notes': '代码、经费与材料均已交接',
            },
            format='json',
        )

        assert response.status_code == 200, response.json()
        project.refresh_from_db()
        successor_membership.refresh_from_db()
        old_membership = ProjectMember.objects.get(project=project, user=old_leader)
        assert project.leader_id == successor.id
        assert successor_membership.role_in_project == ProjectMember.RoleInProject.LEADER
        assert old_membership.status == ProjectMember.Status.EXITED
        assert old_membership.handover_to_id == successor_membership.id

    def test_project_member_delete_is_a_traceable_exit(
        self, admin_client, make_user, make_project
    ):
        project = make_project()
        user = make_user(email='project-exit@test.com')
        membership = ProjectMember.objects.create(project=project, user=user)

        response = admin_client.delete(
            f'/api/v1/projects/{project.id}/members/?user_id={user.id}',
            {'reason': '工作调整'},
            format='json',
        )

        assert response.status_code == 200, response.json()
        membership.refresh_from_db()
        assert membership.status == ProjectMember.Status.EXITED
        assert membership.exit_reason == '工作调整'

    def test_account_preferences_store_scope_favorites_filters_and_quiet_hours(
        self, admin_client
    ):
        payload = {
            'default_scope': 'team',
            'sidebar_order': ['execution', 'workspace', 'resources'],
            'favorite_routes': ['/projects', '/tasks'],
            'saved_filters': {'tasks': {'status': ['todo', 'overdue']}},
            'notification_preferences': {
                'categories': {'finance': False, 'task': True},
                'channels': {'in_app': True, 'email': False},
                'quiet_hours': {'enabled': True, 'start': '22:00', 'end': '07:30'},
                'digest': 'daily',
            },
        }

        response = admin_client.patch('/api/v1/users/preference/', payload, format='json')

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert data['default_scope'] == 'team'
        assert data['favorite_routes'] == ['/projects', '/tasks']
        preference = UserPreference.objects.get(user=admin_client.user)
        assert preference.saved_filters['tasks']['status'] == ['todo', 'overdue']
        assert preference.notification_preferences['digest'] == 'daily'

    def test_external_collaborator_is_limited_to_assigned_projects(
        self, make_user, make_project
    ):
        external = make_user(
            email='external@test.com',
            membership_status=User.MembershipStatus.EXTERNAL,
        )
        assigned = make_project(name='外协可见项目', code='EXT-001')
        hidden = make_project(name='团队内部项目', code='INT-001')
        ProjectMember.objects.create(
            project=assigned,
            user=external,
            role_in_project=ProjectMember.RoleInProject.EXTERNAL,
        )
        Task.objects.create(
            project=assigned,
            title='外协任务',
            assignee=external,
        )
        Task.objects.create(
            project=hidden,
            title='内部任务',
            assignee=hidden.leader,
        )
        Competition.objects.create(
            project=assigned,
            name='外协比赛',
            level=Competition.Level.SCHOOL,
        )
        Competition.objects.create(
            project=hidden,
            name='内部比赛',
            level=Competition.Level.SCHOOL,
        )
        client = APIClient()
        token = RefreshToken.for_user(external)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

        projects = extract_data(client.get('/api/v1/projects/'))
        project_rows = projects.get('results', projects)
        assert [row['id'] for row in project_rows] == [assigned.id]

        tasks = extract_data(client.get('/api/v1/tasks/'))
        task_rows = tasks.get('results', tasks)
        assert {row['project'] for row in task_rows} == {assigned.id}

        competitions = extract_data(client.get('/api/v1/competitions/'))
        competition_rows = competitions.get('results', competitions)
        assert {row['project'] for row in competition_rows} == {assigned.id}

        assert client.get('/api/v1/members/').status_code == 403
        assert client.get('/api/v1/finance/expenses/').status_code == 403
        assert client.get('/api/v1/dashboard/public-portal/').status_code == 200

    def test_mine_scope_only_returns_related_projects_and_tasks(
        self, make_user, make_project
    ):
        user = make_user(email='scope-member@test.com')
        led_project = make_project(leader=user, name='我负责的项目', code='MINE-001')
        joined_project = make_project(name='我参与的项目', code='MINE-002')
        unrelated_project = make_project(name='无关项目', code='TEAM-001')
        ProjectMember.objects.create(
            project=joined_project,
            user=user,
            role_in_project=ProjectMember.RoleInProject.CORE,
        )
        my_task = Task.objects.create(
            project=joined_project,
            title='我的任务',
            assignee=user,
        )
        created_task = Task.objects.create(
            project=led_project,
            title='我创建的任务',
            assignee=led_project.leader,
            creator=user,
        )
        Task.objects.create(
            project=unrelated_project,
            title='团队其他任务',
            assignee=unrelated_project.leader,
        )

        client = APIClient()
        token = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

        projects = extract_data(client.get('/api/v1/projects/?scope=mine'))
        project_rows = projects.get('results', projects)
        assert {row['id'] for row in project_rows} == {
            led_project.id,
            joined_project.id,
        }

        tasks = extract_data(client.get('/api/v1/tasks/?scope=mine'))
        task_rows = tasks.get('results', tasks)
        assert {row['id'] for row in task_rows} == {my_task.id, created_task.id}
