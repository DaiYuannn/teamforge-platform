import pytest
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import Competition
from apps.contributions.models import Contribution, ProjectContributionReviewer
from apps.intellectual_property.models import (
    IntellectualPropertyApplication,
    IPApplicationCandidate,
    IPApplicationProjectLink,
)
from apps.projects.models import ProjectMember


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def response_data(response):
    payload = response.json()
    return payload.get('data', payload) if isinstance(payload, dict) else payload


def response_results(response):
    data = response_data(response)
    return data.get('results', data) if isinstance(data, dict) else data


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_linked_team_visibility_and_active_co_lead_management(
    make_project,
    make_user,
):
    leader = make_user(email='scope-leader@test.com')
    co_leader = make_user(email='scope-co-leader@test.com')
    linked_member = make_user(email='scope-linked@test.com')
    outsider = make_user(email='scope-outsider@test.com')
    project = make_project(leader=leader, visibility='teams')
    ProjectMember.objects.create(
        project=project,
        user=co_leader,
        role_in_project=ProjectMember.RoleInProject.LEADER,
    )
    squad = Team.objects.create(
        name='项目执行小组',
        code='SCOPE-SQUAD',
        owner=leader,
    )
    TeamMember.objects.create(team=squad, user=linked_member)
    project.teams.add(squad)

    linked_rows = response_results(client_for(linked_member).get('/api/v1/projects/'))
    outsider_rows = response_results(client_for(outsider).get('/api/v1/projects/'))
    updated = client_for(co_leader).patch(
        f'/api/v1/projects/{project.id}/',
        {'intro': '共同负责人已更新'},
        format='json',
    )

    assert project.id in {row['id'] for row in linked_rows}
    assert project.id not in {row['id'] for row in outsider_rows}
    assert updated.status_code == 200, updated.json()


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_competition_roster_exposes_actual_members_and_leaders(
    make_project,
    make_user,
):
    project = make_project()
    competition_leader = make_user(email='competition-leader@test.com')
    ProjectMember.objects.create(project=project, user=competition_leader)
    competition = Competition.objects.create(project=project, name='创新比赛')
    leader_client = client_for(project.leader)

    added = leader_client.post(
        f'/api/v1/competitions/{competition.id}/participants/',
        {
            'user': competition_leader.id,
            'role': 'leader',
            'participation_status': 'confirmed',
            'responsibility': '统筹材料与答辩',
        },
        format='json',
    )
    detail = leader_client.get(f'/api/v1/competitions/{competition.id}/')
    managed = client_for(competition_leader).patch(
        f'/api/v1/competitions/{competition.id}/',
        {'current_stage': '材料准备'},
        format='json',
    )

    assert added.status_code == 201, added.json()
    assert response_data(detail)['participant_count'] == 1
    assert response_data(detail)['leader_names'] == [competition_leader.name]
    assert managed.status_code == 200, managed.json()


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_ip_application_supports_multiple_projects_and_candidate_identity_state(
    make_project,
    make_user,
):
    leader = make_user(email='ip-multi-leader@test.com')
    candidate = make_user(email='ip-multi-candidate@test.com')
    primary = make_project(leader=leader, name='主项目')
    reused_by = make_project(leader=leader, name='复用项目')
    ProjectMember.objects.create(project=reused_by, user=candidate)
    leader_client = client_for(leader)

    created = leader_client.post(
        '/api/v1/intellectual-property/applications/',
        {
            'title': '跨项目软著',
            'application_code': 'IP-MULTI-001',
            'ip_type': 'software_copyright',
            'related_project': primary.id,
            'related_project_ids': [primary.id, reused_by.id],
            'main_writer': leader.id,
        },
        format='json',
    )
    assert created.status_code == 201, created.json()
    application = IntellectualPropertyApplication.objects.get(
        application_code='IP-MULTI-001'
    )

    added = leader_client.post(
        f'/api/v1/intellectual-property/applications/{application.id}/candidates/',
        {
            'user': candidate.id,
            'legal_role': 'author',
            'planned_order': 2,
            'status': 'identity_pending',
            'identity_check_status': 'mismatched',
            'note': '姓名与证件待学校系统修正',
        },
        format='json',
    )
    detail = leader_client.get(
        f'/api/v1/intellectual-property/applications/{application.id}/'
    )

    assert added.status_code == 201, added.json()
    assert set(response_data(detail)['related_project_ids']) == {
        primary.id,
        reused_by.id,
    }
    assert response_data(added)['identity_check_status'] == 'mismatched'
    assert 'id_card' not in response_data(added)


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_reused_project_leader_has_read_only_ip_access_and_external_detail_is_limited(
    make_project,
    make_user,
):
    primary = make_project(name='知识产权主项目')
    reused_by = make_project(name='成果复用项目')
    external = make_user(
        email='ip-external-reader@test.com',
        membership_status='external',
    )
    candidate = make_user(email='ip-private-candidate@test.com')
    ProjectMember.objects.create(project=reused_by, user=external)
    ProjectMember.objects.create(project=primary, user=candidate)
    application = IntellectualPropertyApplication.objects.create(
        title='只读复用成果',
        application_code='IP-READONLY-001',
        ip_type='software_copyright',
        related_project=primary,
        main_writer=primary.leader,
        created_by=primary.leader,
    )
    IPApplicationProjectLink.objects.create(
        application=application,
        project=primary,
        relation_type='primary',
    )
    IPApplicationProjectLink.objects.create(
        application=application,
        project=reused_by,
        relation_type='used_by',
    )
    IPApplicationCandidate.objects.create(
        application=application,
        user=candidate,
        legal_role='author',
    )

    reused_leader_client = client_for(reused_by.leader)
    forbidden_candidate = reused_leader_client.post(
        f'/api/v1/intellectual-property/applications/{application.id}/candidates/',
        {'user': reused_by.leader.id, 'legal_role': 'author'},
        format='json',
    )
    forbidden_transition = reused_leader_client.post(
        f'/api/v1/intellectual-property/applications/{application.id}/transition/',
        {'target_status': 'writing'},
        format='json',
    )
    external_roster = client_for(external).get(
        f'/api/v1/intellectual-property/applications/{application.id}/candidates/'
    )

    assert forbidden_candidate.status_code == 403
    assert forbidden_transition.status_code == 403
    roster = response_data(external_roster)
    assert roster[0]['user_detail']['name'] == candidate.name
    assert 'email' not in roster[0]['user_detail']


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_contribution_is_routed_to_configured_reviewer_not_every_teacher(
    make_project,
    make_user,
):
    project = make_project()
    contributor = make_user(email='contribution-member@test.com')
    reviewer = make_user(email='contribution-reviewer@test.com')
    unrelated_teacher = make_user(
        email='unrelated-teacher@test.com',
        global_role='teacher',
    )
    for member in (contributor, reviewer):
        ProjectMember.objects.create(project=project, user=member)

    configured = client_for(project.leader).post(
        '/api/v1/contributions/project-reviewers/',
        {
            'project': project.id,
            'user': reviewer.id,
            'priority': 10,
            'is_independent': True,
        },
        format='json',
    )
    created = client_for(contributor).post(
        '/api/v1/contributions/contributions/',
        {
            'project': project.id,
            'contribution_type': 'stage_task',
            'content': '完成比赛计划书校对',
        },
        format='json',
    )
    reviewer_queue = client_for(reviewer).get(
        '/api/v1/contributions/contributions/pending_review/'
    )
    teacher_queue = client_for(unrelated_teacher).get(
        '/api/v1/contributions/contributions/pending_review/'
    )

    assert configured.status_code == 201, configured.json()
    assert created.status_code == 201, created.json()
    contribution = Contribution.objects.get(pk=response_data(created)['id'])
    assert contribution.reviewer_id == reviewer.id
    assert contribution.id in {row['id'] for row in response_results(reviewer_queue)}
    assert contribution.id not in {row['id'] for row in response_results(teacher_queue)}
    forbidden_review = client_for(unrelated_teacher).patch(
        f'/api/v1/contributions/contributions/{contribution.id}/review/',
        {
            'status': 'approved',
            'review_opinion': '未被分派的老师不应审核',
        },
        format='json',
    )
    invalid_target = client_for(project.leader).post(
        '/api/v1/contributions/contributions/',
        {
            'project': project.id,
            'user': unrelated_teacher.id,
            'contribution_type': 'stage_task',
            'content': '非项目成员不应被登记贡献',
        },
        format='json',
    )
    assert forbidden_review.status_code == 403
    assert invalid_target.status_code == 400


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_contribution_reviewer_assignment_cannot_be_moved_to_another_project(
    make_project,
    make_user,
):
    own_project = make_project(name='审核配置所属项目')
    other_project = make_project(name='无权项目')
    reviewer = make_user(email='reviewer-rebind@test.com')
    assignment = ProjectContributionReviewer.objects.create(
        project=own_project,
        user=reviewer,
    )

    response = client_for(own_project.leader).patch(
        f'/api/v1/contributions/project-reviewers/{assignment.id}/',
        {'project': other_project.id},
        format='json',
    )

    assert response.status_code in (400, 403)
    assignment.refresh_from_db()
    assert assignment.project_id == own_project.id


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_projectless_legacy_contribution_review_never_crashes(make_user):
    contributor = make_user(email='projectless-contributor@test.com')
    teacher = make_user(
        email='projectless-teacher@test.com',
        global_role='teacher',
    )
    admin = make_user(
        email='projectless-admin@test.com',
        global_role='sys_admin',
    )
    contribution = Contribution.objects.create(
        project=None,
        user=contributor,
        contribution_type='other',
        content='历史无项目贡献',
        status='pending',
    )

    teacher_response = client_for(teacher).patch(
        f'/api/v1/contributions/contributions/{contribution.id}/review/',
        {'status': 'approved', 'review_opinion': '未分派老师'},
        format='json',
    )
    admin_response = client_for(admin).patch(
        f'/api/v1/contributions/contributions/{contribution.id}/review/',
        {'status': 'approved', 'review_opinion': '管理员兜底'},
        format='json',
    )

    assert teacher_response.status_code == 403
    assert admin_response.status_code == 200


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_legacy_unassigned_pending_contribution_stays_in_manager_queue(
    make_project,
    make_user,
):
    project = make_project()
    co_leader = make_user(email='legacy-co-leader@test.com')
    member = make_user(email='legacy-contributor@test.com')
    unrelated_teacher = make_user(
        email='legacy-unrelated-teacher@test.com',
        global_role='teacher',
    )
    ProjectMember.objects.create(
        project=project,
        user=co_leader,
        role_in_project=ProjectMember.RoleInProject.LEADER,
    )
    ProjectMember.objects.create(project=project, user=member)
    member_record = Contribution.objects.create(
        project=project,
        user=member,
        filled_by=member,
        contribution_type='stage_task',
        content='历史成员贡献',
        status='pending',
    )
    leader_self_record = Contribution.objects.create(
        project=project,
        user=project.leader,
        filled_by=project.leader,
        contribution_type='project_leader',
        content='历史负责人自报',
        status='pending',
    )

    leader_queue = response_results(client_for(project.leader).get(
        '/api/v1/contributions/contributions/pending_review/'
    ))
    co_leader_queue = response_results(client_for(co_leader).get(
        '/api/v1/contributions/contributions/pending_review/'
    ))
    teacher_queue = response_results(client_for(unrelated_teacher).get(
        '/api/v1/contributions/contributions/pending_review/'
    ))

    assert member_record.id in {row['id'] for row in leader_queue}
    assert leader_self_record.id not in {row['id'] for row in leader_queue}
    assert {member_record.id, leader_self_record.id}.issubset(
        {row['id'] for row in co_leader_queue}
    )
    assert not {member_record.id, leader_self_record.id}.intersection(
        {row['id'] for row in teacher_queue}
    )


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_explicit_cross_team_reviewer_can_only_access_assigned_contribution(
    make_project,
    make_user,
):
    project = make_project(visibility='project')
    contributor = make_user(email='private-project-contributor@test.com')
    cross_team_reviewer = make_user(email='cross-team-reviewer@test.com')
    ProjectMember.objects.create(project=project, user=contributor)
    ProjectContributionReviewer.objects.create(
        project=project,
        user=cross_team_reviewer,
        priority=1,
    )

    created = client_for(contributor).post(
        '/api/v1/contributions/contributions/',
        {
            'project': project.id,
            'contribution_type': 'stage_task',
            'content': '需要跨团队独立复核的贡献',
        },
        format='json',
    )
    contribution_id = response_data(created)['id']
    reviewer_client = client_for(cross_team_reviewer)
    queue = reviewer_client.get(
        '/api/v1/contributions/contributions/pending_review/'
    )
    project_list = reviewer_client.get('/api/v1/projects/')
    reviewed = reviewer_client.patch(
        f'/api/v1/contributions/contributions/{contribution_id}/review/',
        {'status': 'approved', 'review_opinion': '跨团队复核通过'},
        format='json',
    )

    assert created.status_code == 201, created.json()
    assert contribution_id in {row['id'] for row in response_results(queue)}
    assert project.id not in {row['id'] for row in response_results(project_list)}
    assert reviewed.status_code == 200, reviewed.json()


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_exited_cross_team_reviewer_loses_assignment_access(
    make_project,
    make_user,
):
    project = make_project(visibility='project')
    contributor = make_user(email='exited-review-contributor@test.com')
    reviewer = make_user(email='exited-cross-reviewer@test.com')
    ProjectMember.objects.create(project=project, user=contributor)
    ProjectContributionReviewer.objects.create(project=project, user=reviewer)
    contribution = Contribution.objects.create(
        project=project,
        user=contributor,
        filled_by=contributor,
        reviewer=reviewer,
        contribution_type='stage_task',
        content='审核人退出后的待审贡献',
        status='pending',
    )
    reviewer.membership_status = 'exited'
    reviewer.save(update_fields=['membership_status'])
    reviewer_client = client_for(reviewer)

    queue = reviewer_client.get(
        '/api/v1/contributions/contributions/pending_review/'
    )
    review = reviewer_client.patch(
        f'/api/v1/contributions/contributions/{contribution.id}/review/',
        {'status': 'approved', 'review_opinion': '退出后不应通过'},
        format='json',
    )

    assert response_results(queue) == []
    assert review.status_code in (403, 404)
