"""Regression coverage for account-state and project-scope authorization."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.approval_models import ApprovalFlow
from apps.competitions.models import Competition
from apps.contributions.models import Contribution
from apps.files.tag_models import FileTag
from apps.projects.discussion_models import DiscussionTopic
from apps.projects.knowledge_models import KnowledgeArticle
from apps.projects.milestone_models import Milestone
from apps.projects.models import ProjectMember
from apps.tasks.comment_models import TaskComment
from apps.tasks.subtask_models import SubTask
from apps.users.models import User


def client_for(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    client.user = user
    return client


def extract_data(response):
    body = response.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def extract_results(response):
    data = extract_data(response)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


@pytest.mark.api
@pytest.mark.django_db
def test_exited_account_cannot_login_refresh_or_use_existing_token(
    api_client,
    make_user,
):
    exited = make_user(
        email='exited-boundary@test.com',
        membership_status=User.MembershipStatus.EXITED,
        is_active=True,
    )
    refresh = RefreshToken.for_user(exited)

    login = api_client.post(
        '/api/v1/auth/login/',
        {'email': exited.email, 'password': 'TestPass123!'},
        format='json',
    )
    assert login.status_code == 403

    refreshed = api_client.post(
        '/api/v1/auth/refresh/',
        {'refresh': str(refresh)},
        format='json',
    )
    assert refreshed.status_code in (401, 403)

    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}',
    )
    existing = api_client.get('/api/v1/projects/')
    assert existing.status_code in (401, 403)


@pytest.mark.api
@pytest.mark.django_db
def test_external_collaborator_is_scoped_across_child_resources_and_writes(
    make_user,
    make_project,
    make_task,
    make_file,
):
    external = make_user(
        email='external-boundary@test.com',
        membership_status=User.MembershipStatus.EXTERNAL,
    )
    client = client_for(external)
    assigned = make_project(name='已授权项目')
    hidden = make_project(name='未授权项目')
    ProjectMember.objects.create(
        project=assigned,
        user=external,
        role_in_project=ProjectMember.RoleInProject.PARTICIPANT,
        status=ProjectMember.Status.ACTIVE,
    )

    assigned_topic = DiscussionTopic.objects.create(
        project=assigned,
        author=assigned.leader,
        title='已授权讨论',
        content='可见',
    )
    hidden_topic = DiscussionTopic.objects.create(
        project=hidden,
        author=hidden.leader,
        title='未授权讨论',
        content='不可见',
    )
    KnowledgeArticle.objects.create(
        project=assigned,
        author=assigned.leader,
        title='已授权知识',
        content='可见',
    )
    KnowledgeArticle.objects.create(
        project=hidden,
        author=hidden.leader,
        title='未授权知识',
        content='不可见',
    )
    assigned_milestone = Milestone.objects.create(
        project=assigned,
        title='已授权里程碑',
    )
    hidden_milestone = Milestone.objects.create(
        project=hidden,
        title='未授权里程碑',
    )
    assigned_task = make_task(project=assigned, title='已授权任务')
    hidden_task = make_task(project=hidden, title='未授权任务')
    assigned_subtask = SubTask.objects.create(
        parent=assigned_task,
        title='已授权子任务',
    )
    hidden_subtask = SubTask.objects.create(
        parent=hidden_task,
        title='未授权子任务',
    )
    TaskComment.objects.create(
        task=assigned_task,
        author=assigned.leader,
        content='已授权评论',
    )
    TaskComment.objects.create(
        task=hidden_task,
        author=hidden.leader,
        content='未授权评论',
    )
    assigned_competition = Competition.objects.create(
        project=assigned,
        name='已授权比赛',
        level=Competition.Level.SCHOOL,
        status=Competition.Status.PREPARING,
    )
    hidden_competition = Competition.objects.create(
        project=hidden,
        name='未授权比赛',
        level=Competition.Level.SCHOOL,
        status=Competition.Status.PREPARING,
    )
    Contribution.objects.create(
        project=assigned,
        user=assigned.leader,
        contribution_type=Contribution.ContributionType.TASK_COMPLETE,
        weight=Decimal('10'),
        status=Contribution.Status.APPROVED,
    )
    Contribution.objects.create(
        project=hidden,
        user=hidden.leader,
        contribution_type=Contribution.ContributionType.TASK_COMPLETE,
        weight=Decimal('99'),
        status=Contribution.Status.APPROVED,
    )
    assigned_tag = FileTag.objects.create(
        project=assigned,
        name='已授权标签',
        created_by=assigned.leader,
    )
    hidden_tag = FileTag.objects.create(
        project=hidden,
        name='未授权标签',
        created_by=hidden.leader,
    )
    assigned_file = make_file(
        project=assigned,
        uploader=assigned.leader,
        level='internal',
    )
    hidden_file = make_file(
        project=hidden,
        uploader=hidden.leader,
        level='internal',
    )

    member_rows = extract_results(client.get('/api/v1/projects/members/'))
    assert {row['project'] for row in member_rows} == {assigned.id}
    assert {
        row['id']
        for row in extract_results(client.get('/api/v1/projects/discussions/'))
    } == {assigned_topic.id}
    assert {
        row['project']
        for row in extract_results(client.get('/api/v1/projects/knowledge/'))
    } == {assigned.id}
    assert {
        row['id']
        for row in extract_results(client.get('/api/v1/projects/milestones/'))
    } == {assigned_milestone.id}
    assert {
        row['id']
        for row in extract_results(client.get('/api/v1/tasks/subtasks/'))
    } == {assigned_subtask.id}
    assert all(
        row['task'] == assigned_task.id
        for row in extract_results(client.get('/api/v1/tasks/comments/'))
    )
    assert {
        row['id']
        for row in extract_results(client.get('/api/v1/files/tags/'))
    } == {assigned_tag.id}

    timeline = client.get(
        f'/api/v1/competitions/timeline/?competition={hidden_competition.id}',
    )
    assert timeline.status_code != 200
    allowed_timeline = client.get(
        f'/api/v1/competitions/timeline/?competition={assigned_competition.id}',
    )
    assert allowed_timeline.status_code == 200
    assert extract_data(
        client.get('/api/v1/competitions/statistics/'),
    )['total'] == 1
    leaderboard = extract_data(
        client.get('/api/v1/contributions/leaderboard/'),
    )['leaderboard']
    assert [row['user_id'] for row in leaderboard] == [assigned.leader_id]

    assert client.post(
        '/api/v1/projects/discussions/',
        {'project': hidden.id, 'title': '越权', 'content': '禁止'},
        format='json',
    ).status_code == 403
    assert client.post(
        '/api/v1/projects/discussions/',
        {'project': assigned.id, 'title': '协作', 'content': '允许'},
        format='json',
    ).status_code in (200, 201)
    assert client.post(
        '/api/v1/tasks/comments/',
        {'task': hidden_task.id, 'content': '越权'},
        format='json',
    ).status_code == 403
    assert client.post(
        '/api/v1/tasks/comments/',
        {'task': assigned_task.id, 'content': '协作'},
        format='json',
    ).status_code in (200, 201)
    assert client.post(
        f'/api/v1/projects/milestones/{hidden_milestone.id}/toggle/',
        {},
        format='json',
    ).status_code in (403, 404)
    assert client.post(
        f'/api/v1/projects/milestones/{assigned_milestone.id}/toggle/',
        {},
        format='json',
    ).status_code == 200
    assert client.post(
        f'/api/v1/tasks/subtasks/{hidden_subtask.id}/toggle/',
        {},
        format='json',
    ).status_code in (403, 404)

    assert client.get(
        f'/api/v1/files/tags/by-file/?file={hidden_file.id}',
    ).status_code == 403
    assert client.post(
        '/api/v1/files/tags/assign/',
        {'file': hidden_file.id, 'tags': [hidden_tag.id]},
        format='json',
    ).status_code == 403
    assert client.post(
        '/api/v1/files/tags/assign/',
        {'file': assigned_file.id, 'tags': [assigned_tag.id]},
        format='json',
    ).status_code == 200


@pytest.mark.api
@pytest.mark.django_db
def test_on_leave_keeps_internal_reads_but_project_writes_require_membership(
    make_user,
    make_project,
):
    on_leave = make_user(
        email='on-leave-boundary@test.com',
        membership_status=User.MembershipStatus.ON_LEAVE,
    )
    client = client_for(on_leave)
    assigned = make_project(name='暂离仍参与')
    hidden = make_project(name='暂离未参与')
    ProjectMember.objects.create(
        project=assigned,
        user=on_leave,
        role_in_project=ProjectMember.RoleInProject.PARTICIPANT,
        status=ProjectMember.Status.ACTIVE,
    )
    DiscussionTopic.objects.create(
        project=hidden,
        author=hidden.leader,
        title='团队透明讨论',
        content='内部可读',
    )

    assert client.get('/api/v1/members/').status_code == 200
    assert len(extract_results(
        client.get('/api/v1/projects/discussions/'),
    )) == 1
    assert client.post(
        '/api/v1/projects/discussions/',
        {'project': hidden.id, 'title': '暂离越权写', 'content': '禁止'},
        format='json',
    ).status_code == 403
    assert client.post(
        '/api/v1/projects/discussions/',
        {'project': assigned.id, 'title': '暂离协作写', 'content': '允许'},
        format='json',
    ).status_code in (200, 201)


@pytest.mark.api
@pytest.mark.django_db
def test_generic_approval_rejects_self_and_matches_current_step_reviewer(
    make_user,
):
    applicant = make_user(email='approval-applicant@test.com')
    reviewer = make_user(email='approval-reviewer@test.com')
    outsider = make_user(email='approval-outsider@test.com')
    flow = ApprovalFlow.objects.create(
        name='指定审批人流程',
        flow_type='generic',
        steps=[{'name': '指定审批', 'reviewer_id': reviewer.id}],
    )
    applicant_client = client_for(applicant)
    reviewer_client = client_for(reviewer)
    outsider_client = client_for(outsider)

    created = applicant_client.post(
        '/api/v1/approvals/requests/',
        {'flow': flow.id, 'title': '不能自批', 'content': ''},
        format='json',
    )
    assert created.status_code in (200, 201)
    request_id = extract_data(created)['id']

    assert applicant_client.post(
        f'/api/v1/approvals/requests/{request_id}/approve/',
        {'opinion': '自批'},
        format='json',
    ).status_code == 403
    assert outsider_client.post(
        f'/api/v1/approvals/requests/{request_id}/approve/',
        {'opinion': '越权'},
        format='json',
    ).status_code in (403, 404)
    approved = reviewer_client.post(
        f'/api/v1/approvals/requests/{request_id}/approve/',
        {'opinion': '同意'},
        format='json',
    )
    assert approved.status_code == 200
    assert extract_data(approved)['status'] == 'approved'

    assert applicant_client.post(
        '/api/v1/approvals/flows/',
        {'name': '越权流程', 'flow_type': 'generic', 'steps': []},
        format='json',
    ).status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_system_metadata_role_boundaries(make_user):
    member = client_for(make_user(email='metadata-member@test.com'))
    teacher = client_for(make_user(
        email='metadata-teacher@test.com',
        global_role='teacher',
    ))
    admin = client_for(make_user(
        email='metadata-admin@test.com',
        global_role='sys_admin',
        is_staff=True,
        is_superuser=True,
    ))
    teacher_or_admin_urls = (
        '/api/v1/common/security-scan/',
        '/api/v1/common/api-docs/',
    )
    admin_only_urls = (
        '/api/v1/common/openapi/schema/',
        '/api/v1/common/openapi/endpoints/',
        '/api/v1/common/accessibility/report/',
    )
    for url in teacher_or_admin_urls:
        assert member.get(url).status_code == 403
        assert teacher.get(url).status_code == 200
        assert admin.get(url).status_code == 200
    for url in admin_only_urls:
        assert member.get(url).status_code == 403
        assert teacher.get(url).status_code == 403
        assert admin.get(url).status_code == 200
