"""Security regressions for small-team tenant and role boundaries."""

from decimal import Decimal

import pytest

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import Competition, CompetitionParticipant
from apps.contributions.models import Contribution, MemberRanking, RankingObjection
from apps.exports.custom_report_models import CustomReport
from apps.exports.scheduled_report_models import ScheduledReport
from apps.finance.models import FinanceExpense
from apps.files.models import FileAsset
from apps.projects.models import Project, ProjectMember
from apps.sensitive.models import SensitiveAccessRequest, SensitiveData
from apps.tasks.models import Task
from apps.users.models import User


CUSTOM_REPORT_URL = '/api/v1/exports/custom-reports/'


def extract_data(response):
    payload = response.json()
    if isinstance(payload, dict) and 'data' in payload:
        return payload['data']
    return payload


def make_root_team(name, code, owner):
    team = Team.objects.create(name=name, code=code, owner=owner)
    TeamMember.objects.create(
        team=team,
        user=owner,
        role=TeamMember.Role.OWNER,
    )
    return team


def make_scoped_project(*, name, code, leader, team, visibility):
    project = Project.objects.create(
        name=name,
        code=code,
        leader=leader,
        visibility=visibility,
    )
    project.teams.add(team)
    ProjectMember.objects.create(
        project=project,
        user=leader,
        role_in_project=ProjectMember.RoleInProject.LEADER,
    )
    return project


@pytest.mark.django_db
def test_sensitive_my_data_includes_subject_owned_record(api_client, make_user):
    owner = make_user(email='sensitive-uploader@security.test')
    subject = make_user(email='sensitive-subject@security.test')
    team = make_root_team('Sensitive root', 'SEC-SENS', owner)
    TeamMember.objects.create(team=team, user=subject)
    record = SensitiveData.objects.create(
        title='Subject identity',
        data_type=SensitiveData.DataType.ID_CARD,
        team=team,
        subject_user=subject,
        uploader=owner,
    )
    record.encrypt_content('110101200001011234')

    api_client.force_authenticate(user=subject)
    response = api_client.get('/api/v1/sensitive/data/my_data/')

    assert response.status_code == 200, response.json()
    rows = extract_data(response)
    if isinstance(rows, dict):
        rows = rows.get('results', [])
    assert record.id in {row['id'] for row in rows}


@pytest.mark.django_db
def test_exited_team_owner_cannot_review_sensitive_request(api_client, make_user):
    owner = make_user(
        email='exited-sensitive-owner@security.test',
        membership_status=User.MembershipStatus.EXITED,
    )
    applicant = make_user(email='sensitive-applicant@security.test')
    team = make_root_team('Exited owner root', 'SEC-EXIT', owner)
    TeamMember.objects.create(team=team, user=applicant)
    record = SensitiveData.objects.create(
        title='Protected identity',
        data_type=SensitiveData.DataType.ID_CARD,
        team=team,
        subject_user=applicant,
        uploader=applicant,
    )
    record.encrypt_content('110101200001011235')
    access_request = SensitiveAccessRequest.objects.create(
        sensitive_data=record,
        applicant=applicant,
        reason='Registration',
    )

    api_client.force_authenticate(user=owner)
    response = api_client.post(
        f'/api/v1/sensitive/requests/{access_request.id}/approve/',
        {'action': 'approve', 'expire_hours': 1},
        format='json',
    )

    assert response.status_code == 403, response.json()
    access_request.refresh_from_db()
    assert access_request.status == SensitiveAccessRequest.Status.PENDING
    assert access_request.approver_id is None


@pytest.mark.django_db
def test_exited_legacy_sensitive_approver_cannot_review_unscoped_record(
    api_client,
    make_user,
):
    approver = make_user(
        email='exited-legacy-approver@security.test',
        global_role=User.GlobalRole.SENS_APPROVER,
        membership_status=User.MembershipStatus.EXITED,
    )
    applicant = make_user(email='legacy-sensitive-applicant@security.test')
    record = SensitiveData.objects.create(
        title='Legacy protected identity',
        data_type=SensitiveData.DataType.ID_CARD,
        subject_user=applicant,
        uploader=applicant,
    )
    record.encrypt_content('110101200001011236')
    access_request = SensitiveAccessRequest.objects.create(
        sensitive_data=record,
        applicant=applicant,
        reason='Legacy registration',
    )

    api_client.force_authenticate(user=approver)
    response = api_client.post(
        f'/api/v1/sensitive/requests/{access_request.id}/approve/',
        {'action': 'approve', 'expire_hours': 1},
        format='json',
    )

    assert response.status_code == 403, response.json()
    access_request.refresh_from_db()
    assert access_request.status == SensitiveAccessRequest.Status.PENDING


@pytest.mark.django_db
def test_external_competition_participant_details_are_minimized(
    api_client,
    make_user,
):
    project_leader = make_user(email='competition-owner@security.test')
    external = make_user(
        email='external-viewer@security.test',
        phone='13800138000',
        school='Should not be returned',
        membership_status=User.MembershipStatus.EXTERNAL,
    )
    participant_user = make_user(
        email='participant-private@security.test',
        phone='13900139000',
        school='Private school',
        grade='2024',
        major='Private major',
    )
    project = Project.objects.create(
        name='External visible project',
        code='SEC-COMP-EXT',
        leader=project_leader,
        visibility=Project.Visibility.PROJECT,
    )
    for user, role in (
        (project_leader, ProjectMember.RoleInProject.LEADER),
        (external, ProjectMember.RoleInProject.EXTERNAL),
        (participant_user, ProjectMember.RoleInProject.PARTICIPANT),
    ):
        ProjectMember.objects.create(
            project=project,
            user=user,
            role_in_project=role,
        )
    competition = Competition.objects.create(
        project=project,
        name='External-safe competition',
    )
    participant = CompetitionParticipant.objects.create(
        competition=competition,
        user=participant_user,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )

    api_client.force_authenticate(user=external)
    response = api_client.get(
        f'/api/v1/competitions/{competition.id}/participants/'
    )

    assert response.status_code == 200, response.json()
    rows = extract_data(response)
    row = next(item for item in rows if item['id'] == participant.id)
    assert set(row['user_detail']) == {
        'id', 'name', 'avatar', 'global_role', 'global_role_display',
    }
    assert {
        'username', 'email', 'phone', 'school', 'grade', 'major',
        'membership_status', 'team_joined_at', 'team_left_at',
    }.isdisjoint(row['user_detail'])


@pytest.mark.django_db
def test_stale_or_exited_competition_leader_cannot_maintain_competition(
    api_client,
    make_user,
):
    root_owner = make_user(email='competition-root-owner@security.test')
    project_leader = make_user(email='competition-project-leader@security.test')
    stale_leader = make_user(email='competition-stale-leader@security.test')
    root = make_root_team('Competition root', 'SEC-COMP-ROOT', root_owner)
    TeamMember.objects.create(team=root, user=stale_leader)
    project = make_scoped_project(
        name='Competition project',
        code='SEC-COMP-STALE',
        leader=project_leader,
        team=root,
        visibility=Project.Visibility.ORGANIZATION,
    )
    stale_membership = ProjectMember.objects.create(
        project=project,
        user=stale_leader,
        role_in_project=ProjectMember.RoleInProject.PARTICIPANT,
        status=ProjectMember.Status.EXITED,
    )
    competition = Competition.objects.create(
        project=project,
        name='Protected competition',
    )
    CompetitionParticipant.objects.create(
        competition=competition,
        user=stale_leader,
        role=CompetitionParticipant.Role.LEADER,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )

    api_client.force_authenticate(user=stale_leader)
    stale_response = api_client.patch(
        f'/api/v1/competitions/{competition.id}/',
        {'name': 'Unauthorized rename'},
        format='json',
    )

    assert stale_membership.status == ProjectMember.Status.EXITED
    assert stale_response.status_code == 403, stale_response.json()

    stale_leader.membership_status = User.MembershipStatus.EXITED
    stale_leader.save(update_fields=['membership_status'])
    exited_response = api_client.patch(
        f'/api/v1/competitions/{competition.id}/',
        {'name': 'Still unauthorized'},
        format='json',
    )

    assert exited_response.status_code in (403, 404), exited_response.json()
    competition.refresh_from_db()
    assert competition.name == 'Protected competition'


@pytest.mark.django_db
def test_team_with_child_cannot_be_patched_under_another_root(
    api_client,
    make_user,
):
    owner = make_user(email='hierarchy-owner@security.test')
    root = make_root_team('Root with child', 'SEC-HIER-A', owner)
    other_root = make_root_team('Other root', 'SEC-HIER-B', owner)
    child = Team.objects.create(
        name='Existing child',
        code='SEC-HIER-CHILD',
        owner=owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(
        team=child,
        user=owner,
        role=TeamMember.Role.OWNER,
    )

    api_client.force_authenticate(user=owner)
    response = api_client.patch(
        f'/api/v1/teams/{root.id}/',
        {'parent': other_root.id},
        format='json',
    )

    assert response.status_code == 400, response.json()
    root.refresh_from_db()
    assert root.parent_id is None


@pytest.mark.django_db
def test_root_ordinary_member_cannot_browse_unrelated_child_team(
    api_client,
    make_user,
):
    owner = make_user(email='root-visibility-owner@security.test')
    ordinary_root_member = make_user(
        email='root-visibility-member@security.test'
    )
    root = make_root_team('Visibility root', 'SEC-VIS-ROOT', owner)
    TeamMember.objects.create(team=root, user=ordinary_root_member)
    child = Team.objects.create(
        name='Unrelated child',
        code='SEC-VIS-CHILD',
        owner=owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(
        team=child,
        user=owner,
        role=TeamMember.Role.OWNER,
    )

    api_client.force_authenticate(user=ordinary_root_member)
    response = api_client.get('/api/v1/teams/')

    assert response.status_code == 200, response.json()
    rows = extract_data(response)
    if isinstance(rows, dict):
        rows = rows.get('results', [])
    visible_ids = {row['id'] for row in rows}
    assert root.id in visible_ids
    assert child.id not in visible_ids


@pytest.mark.django_db
def test_team_co_lead_can_create_only_for_managed_team(api_client, make_user):
    owner = make_user(email='project-create-owner@security.test')
    co_lead = make_user(email='project-create-colead@security.test')
    ordinary = make_user(email='project-create-member@security.test')
    root = make_root_team('Project create root', 'SEC-CREATE-ROOT', owner)
    TeamMember.objects.create(
        team=root,
        user=co_lead,
        role=TeamMember.Role.CO_LEAD,
    )
    TeamMember.objects.create(team=root, user=ordinary)

    payload = {
        'name': 'Core managed project',
        'code': 'SEC-CORE-CREATE',
        'leader': co_lead.id,
        'teams': [root.id],
        'visibility': Project.Visibility.TEAMS,
    }
    api_client.force_authenticate(user=co_lead)
    allowed_response = api_client.post(
        '/api/v1/projects/',
        payload,
        format='json',
    )
    assert allowed_response.status_code == 201, allowed_response.json()

    payload['name'] = 'Ordinary member project'
    payload['code'] = 'SEC-MEMBER-CREATE'
    payload['leader'] = ordinary.id
    api_client.force_authenticate(user=ordinary)
    denied_response = api_client.post(
        '/api/v1/projects/',
        payload,
        format='json',
    )
    assert denied_response.status_code == 403, denied_response.json()


@pytest.mark.django_db
def test_contribution_reviewer_may_cross_squad_but_not_root(
    api_client,
    make_user,
):
    project_leader = make_user(email='review-pool-leader@security.test')
    same_root_reviewer = make_user(
        email='review-pool-same-root@security.test'
    )
    other_root_reviewer = make_user(
        email='review-pool-other-root@security.test'
    )
    root = make_root_team('Review pool root', 'SEC-REVIEW-ROOT', project_leader)
    sibling = Team.objects.create(
        name='Review sibling',
        code='SEC-REVIEW-SIBLING',
        owner=same_root_reviewer,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(
        team=sibling,
        user=same_root_reviewer,
        role=TeamMember.Role.OWNER,
    )
    other_root = make_root_team(
        'Other review root',
        'SEC-REVIEW-OTHER',
        other_root_reviewer,
    )
    project = make_scoped_project(
        name='Review pool project',
        code='SEC-REVIEW-PROJECT',
        leader=project_leader,
        team=root,
        visibility=Project.Visibility.PROJECT,
    )

    api_client.force_authenticate(user=project_leader)
    same_root_response = api_client.post(
        '/api/v1/contributions/project-reviewers/',
        {
            'project': project.id,
            'user': same_root_reviewer.id,
            'is_independent': True,
        },
        format='json',
    )
    assert same_root_response.status_code == 201, same_root_response.json()

    other_root_response = api_client.post(
        '/api/v1/contributions/project-reviewers/',
        {
            'project': project.id,
            'user': other_root_reviewer.id,
            'is_independent': True,
        },
        format='json',
    )
    assert other_root_response.status_code == 400, other_root_response.json()
    assert other_root.owner_id == other_root_reviewer.id


@pytest.mark.django_db
def test_custom_reports_exclude_private_and_other_root_projects(
    api_client,
    make_user,
):
    viewer = make_user(email='report-viewer@security.test')
    root_a_owner = make_user(email='report-root-a-owner@security.test')
    root_b_owner = make_user(email='report-root-b-owner@security.test')
    hidden_private_leader = make_user(
        email='report-private-leader@security.test'
    )
    root_a = make_root_team('Report root A', 'SEC-REPORT-A', root_a_owner)
    root_b = make_root_team('Report root B', 'SEC-REPORT-B', root_b_owner)
    TeamMember.objects.create(team=root_a, user=viewer)

    visible = make_scoped_project(
        name='Visible project',
        code='SEC-REPORT-VISIBLE',
        leader=viewer,
        team=root_a,
        visibility=Project.Visibility.PROJECT,
    )
    hidden_private = make_scoped_project(
        name='Private project',
        code='SEC-REPORT-PRIVATE',
        leader=hidden_private_leader,
        team=root_a,
        visibility=Project.Visibility.PROJECT,
    )
    hidden_other_root = make_scoped_project(
        name='Other root project',
        code='SEC-REPORT-OTHER',
        leader=root_b_owner,
        team=root_b,
        visibility=Project.Visibility.ORGANIZATION,
    )

    for project, suffix, amount in (
        (visible, 'visible', Decimal('10.00')),
        (hidden_private, 'private', Decimal('20.00')),
        (hidden_other_root, 'other-root', Decimal('30.00')),
    ):
        Task.objects.create(
            project=project,
            title=f'Task {suffix}',
            assignee=project.leader,
        )
        FinanceExpense.objects.create(
            project=project,
            title=f'Expense {suffix}',
            amount=amount,
            expense_date='2026-07-29',
        )
        Competition.objects.create(
            project=project,
            name=f'Competition {suffix}',
        )

    api_client.force_authenticate(user=viewer)
    expected_summaries = {
        'task': {'total': 1},
        'finance': {'count': 1, 'total_amount': 10.0},
        'competition': {'total': 1},
        'project': {'total': 1},
    }
    for source, expected in expected_summaries.items():
        report = CustomReport.objects.create(
            name=f'{source} security report',
            report_type=CustomReport.ReportType.SUMMARY,
            config={'data_source': source},
            created_by=viewer,
        )
        response = api_client.post(
            f'{CUSTOM_REPORT_URL}{report.id}/generate/'
        )
        assert response.status_code == 200, response.json()
        summary = extract_data(response)['data']['summary']
        for key, value in expected.items():
            assert summary[key] == value, (source, summary)

    for hidden_project in (hidden_private, hidden_other_root):
        response = api_client.get(
            f'/api/v1/exports/project-report/{hidden_project.id}/'
        )
        assert response.status_code == 404, response.json()


@pytest.mark.django_db
def test_scheduled_report_recipients_must_share_scope(
    api_client,
    make_user,
):
    creator = make_user(email='schedule-creator@security.test')
    same_root_recipient = make_user(
        email='schedule-same-root@security.test'
    )
    other_root_recipient = make_user(
        email='schedule-other-root@security.test'
    )
    root_a = make_root_team(
        'Schedule root A',
        'SEC-SCHEDULE-A',
        creator,
    )
    root_b = make_root_team(
        'Schedule root B',
        'SEC-SCHEDULE-B',
        other_root_recipient,
    )
    TeamMember.objects.create(team=root_a, user=same_root_recipient)
    project = make_scoped_project(
        name='Private scheduled project',
        code='SEC-SCHEDULE-PRIVATE',
        leader=creator,
        team=root_a,
        visibility=Project.Visibility.PROJECT,
    )
    report = CustomReport.objects.create(
        name='Private scheduled report',
        report_type=CustomReport.ReportType.SUMMARY,
        config={'data_source': 'project'},
        created_by=creator,
    )

    api_client.force_authenticate(user=creator)
    cross_root_response = api_client.post(
        '/api/v1/exports/scheduled-reports/',
        {
            'report': report.id,
            'frequency': ScheduledReport.Frequency.DAILY,
            'recipient_ids': [other_root_recipient.id],
        },
        format='json',
    )
    assert cross_root_response.status_code == 400, cross_root_response.json()

    private_scope_response = api_client.post(
        '/api/v1/exports/scheduled-reports/',
        {
            'report': report.id,
            'frequency': ScheduledReport.Frequency.DAILY,
            'recipient_ids': [same_root_recipient.id],
        },
        format='json',
    )
    assert private_scope_response.status_code == 400, private_scope_response.json()

    ProjectMember.objects.create(
        project=project,
        user=same_root_recipient,
        role_in_project=ProjectMember.RoleInProject.PARTICIPANT,
    )
    allowed_response = api_client.post(
        '/api/v1/exports/scheduled-reports/',
        {
            'report': report.id,
            'frequency': ScheduledReport.Frequency.DAILY,
            'recipient_ids': [same_root_recipient.id],
        },
        format='json',
    )
    assert allowed_response.status_code == 201, allowed_response.json()

    # Keep the second root referenced so accidental fixture cleanup is visible.
    assert root_b.owner_id == other_root_recipient.id


@pytest.mark.django_db
def test_project_cannot_move_or_add_internal_member_across_root(
    api_client,
    make_user,
):
    leader = make_user(email='project-boundary-leader@security.test')
    other_owner = make_user(email='project-boundary-other@security.test')
    root_a = make_root_team('Project boundary A', 'SEC-PROJECT-A', leader)
    root_b = make_root_team(
        'Project boundary B',
        'SEC-PROJECT-B',
        other_owner,
    )
    project = make_scoped_project(
        name='Project boundary',
        code='SEC-PROJECT-BOUNDARY',
        leader=leader,
        team=root_a,
        visibility=Project.Visibility.ORGANIZATION,
    )

    api_client.force_authenticate(user=leader)
    move_response = api_client.patch(
        f'/api/v1/projects/{project.id}/',
        {
            'leader': other_owner.id,
            'teams': [root_b.id],
        },
        format='json',
    )
    assert move_response.status_code == 400, move_response.json()

    add_response = api_client.post(
        f'/api/v1/projects/{project.id}/members/',
        {'user_id': other_owner.id, 'role_in_project': 'participant'},
        format='json',
    )
    assert add_response.status_code == 400, add_response.json()
    assert not ProjectMember.objects.filter(
        project=project,
        user=other_owner,
    ).exists()

    project.refresh_from_db()
    assert project.leader_id == leader.id
    assert set(project.teams.values_list('id', flat=True)) == {root_a.id}


@pytest.mark.django_db
def test_project_cannot_span_two_root_organizations(
    api_client,
    make_user,
):
    admin = make_user(
        email='project-multi-root-admin@security.test',
        global_role=User.GlobalRole.SYS_ADMIN,
    )
    owner_a = make_user(email='project-multi-root-a@security.test')
    owner_b = make_user(email='project-multi-root-b@security.test')
    root_a = make_root_team('Multi root A', 'SEC-MULTI-A', owner_a)
    root_b = make_root_team('Multi root B', 'SEC-MULTI-B', owner_b)

    api_client.force_authenticate(user=admin)
    response = api_client.post(
        '/api/v1/projects/',
        {
            'name': 'Invalid multi-root project',
            'code': 'SEC-MULTI-PROJECT',
            'leader': owner_a.id,
            'teams': [root_a.id, root_b.id],
            'visibility': Project.Visibility.ORGANIZATION,
        },
        format='json',
    )

    assert response.status_code == 400, response.json()
    assert not Project.objects.filter(code='SEC-MULTI-PROJECT').exists()


@pytest.mark.django_db
def test_legacy_project_member_add_still_works_without_team_models(
    api_client,
    make_user,
):
    leader = make_user(email='legacy-project-leader@security.test')
    member = make_user(email='legacy-project-member@security.test')
    project = Project.objects.create(
        name='Legacy project',
        code='SEC-LEGACY-MEMBER',
        leader=leader,
    )
    ProjectMember.objects.create(
        project=project,
        user=leader,
        role_in_project=ProjectMember.RoleInProject.LEADER,
    )

    api_client.force_authenticate(user=leader)
    response = api_client.post(
        f'/api/v1/projects/{project.id}/members/',
        {'user_id': member.id, 'role_in_project': 'participant'},
        format='json',
    )

    assert response.status_code == 201, response.json()
    assert ProjectMember.objects.filter(project=project, user=member).exists()


@pytest.mark.django_db
def test_child_manager_cannot_detach_or_browse_other_root_candidates(
    api_client,
    make_user,
):
    root_owner = make_user(email='child-boundary-root@security.test')
    child_owner = make_user(email='child-boundary-owner@security.test')
    other_owner = make_user(email='child-boundary-other@security.test')
    root = make_root_team('Child boundary root', 'SEC-CHILD-ROOT', root_owner)
    child = Team.objects.create(
        name='Child boundary squad',
        code='SEC-CHILD-SQUAD',
        owner=child_owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(
        team=child,
        user=child_owner,
        role=TeamMember.Role.OWNER,
    )
    make_root_team('Child other root', 'SEC-CHILD-OTHER', other_owner)

    api_client.force_authenticate(user=child_owner)
    detach_response = api_client.patch(
        f'/api/v1/teams/{child.id}/',
        {'parent': None},
        format='json',
    )
    assert detach_response.status_code == 400, detach_response.json()

    candidates_response = api_client.get(
        f'/api/v1/teams/{child.id}/candidates/'
    )
    assert candidates_response.status_code == 200, candidates_response.json()
    candidates = extract_data(candidates_response)
    candidate_ids = {row['id'] for row in candidates}
    assert root_owner.id in candidate_ids
    assert other_owner.id not in candidate_ids

    add_response = api_client.post(
        f'/api/v1/teams/{child.id}/members/',
        {'user': other_owner.id, 'role': TeamMember.Role.MEMBER},
        format='json',
    )
    assert add_response.status_code == 400, add_response.json()
    assert not TeamMember.objects.filter(team=child, user=other_owner).exists()

    child.refresh_from_db()
    assert child.parent_id == root.id


@pytest.mark.django_db
def test_public_rankings_are_scoped_to_root_organization(
    api_client,
    make_user,
):
    viewer = make_user(email='ranking-scope-viewer@security.test')
    other_owner = make_user(email='ranking-scope-other@security.test')
    root_a = make_root_team('Ranking scope A', 'SEC-RANK-A', viewer)
    root_b = make_root_team('Ranking scope B', 'SEC-RANK-B', other_owner)
    project_a = make_scoped_project(
        name='Ranking visible',
        code='SEC-RANK-VISIBLE',
        leader=viewer,
        team=root_a,
        visibility=Project.Visibility.ORGANIZATION,
    )
    project_b = make_scoped_project(
        name='Ranking hidden',
        code='SEC-RANK-HIDDEN',
        leader=other_owner,
        team=root_b,
        visibility=Project.Visibility.ORGANIZATION,
    )
    visible = MemberRanking.objects.create(
        project=project_a,
        user=viewer,
        period='2026-07',
        status=MemberRanking.Status.CONFIRMED,
        is_public=True,
        rank=1,
    )
    hidden = MemberRanking.objects.create(
        project=project_b,
        user=other_owner,
        period='2026-07',
        status=MemberRanking.Status.CONFIRMED,
        is_public=True,
        rank=1,
    )

    api_client.force_authenticate(user=viewer)
    response = api_client.get('/api/v1/contributions/rankings/')
    assert response.status_code == 200, response.json()
    rows = extract_data(response)
    if isinstance(rows, dict):
        rows = rows.get('results', [])
    ranking_ids = {row['id'] for row in rows}
    assert visible.id in ranking_ids
    assert hidden.id not in ranking_ids

    hidden_response = api_client.get(
        f'/api/v1/contributions/rankings/by_project/?project={project_b.id}'
    )
    assert hidden_response.status_code == 200, hidden_response.json()
    hidden_rows = extract_data(hidden_response)
    if isinstance(hidden_rows, dict):
        hidden_rows = hidden_rows.get('results', [])
    assert hidden_rows == []


@pytest.mark.django_db
def test_contribution_cannot_bind_existing_file_asset(
    api_client,
    make_user,
):
    leader = make_user(email='proof-boundary-leader@security.test')
    contributor = make_user(email='proof-boundary-member@security.test')
    other_owner = make_user(email='proof-boundary-other@security.test')
    root_a = make_root_team('Proof boundary A', 'SEC-PROOF-A', leader)
    root_b = make_root_team('Proof boundary B', 'SEC-PROOF-B', other_owner)
    TeamMember.objects.create(team=root_a, user=contributor)
    project = make_scoped_project(
        name='Proof target',
        code='SEC-PROOF-TARGET',
        leader=leader,
        team=root_a,
        visibility=Project.Visibility.PROJECT,
    )
    ProjectMember.objects.create(project=project, user=contributor)
    other_project = make_scoped_project(
        name='Proof source',
        code='SEC-PROOF-SOURCE',
        leader=other_owner,
        team=root_b,
        visibility=Project.Visibility.PROJECT,
    )
    other_file = FileAsset.objects.create(
        project=other_project,
        name='other-proof.txt',
        file='files/other-proof.txt',
        level=FileAsset.Level.INTERNAL,
        uploader=other_owner,
    )

    api_client.force_authenticate(user=contributor)
    response = api_client.post(
        '/api/v1/contributions/contributions/',
        {
            'project': project.id,
            'user': contributor.id,
            'contribution_type': 'other',
            'content': 'Attempted file rebinding',
            'proof_file': other_file.id,
        },
        format='json',
    )

    assert response.status_code == 400, response.json()
    assert not Contribution.objects.filter(
        project=project,
        user=contributor,
    ).exists()


@pytest.mark.django_db
def test_ranking_objection_notifies_only_same_root_teachers(
    monkeypatch,
    make_user,
):
    leader = make_user(email='objection-scope-leader@security.test')
    objector = make_user(email='objection-scope-member@security.test')
    same_root_teacher = make_user(
        email='objection-scope-teacher@security.test',
        global_role=User.GlobalRole.TEACHER,
    )
    other_root_teacher = make_user(
        email='objection-other-teacher@security.test',
        global_role=User.GlobalRole.TEACHER,
    )
    root_a = make_root_team('Objection scope A', 'SEC-OBJ-A', leader)
    root_b = make_root_team(
        'Objection scope B',
        'SEC-OBJ-B',
        other_root_teacher,
    )
    TeamMember.objects.create(team=root_a, user=objector)
    TeamMember.objects.create(
        team=root_a,
        user=same_root_teacher,
        role=TeamMember.Role.TEACHER,
    )
    project = make_scoped_project(
        name='Objection project',
        code='SEC-OBJ-PROJECT',
        leader=leader,
        team=root_a,
        visibility=Project.Visibility.PROJECT,
    )
    ProjectMember.objects.create(project=project, user=objector)
    ranking = MemberRanking.objects.create(
        project=project,
        user=objector,
        period='2026-07',
        status=MemberRanking.Status.CONFIRMED,
        is_public=True,
        rank=1,
    )
    objection = RankingObjection.objects.create(
        ranking=ranking,
        objector=objector,
        content='Please review the evidence',
    )

    captured_recipients = []

    def capture_notifications(*, recipients, **kwargs):
        captured_recipients.extend(recipients)
        return len(recipients)

    from apps.contributions.views import _notify_ranking_objection
    from apps.notifications.services import NotificationService

    monkeypatch.setattr(
        NotificationService,
        'bulk_create_and_send_email',
        capture_notifications,
    )
    _notify_ranking_objection(objection, 'created', objector)

    recipient_ids = {user.id for user in captured_recipients}
    assert leader.id in recipient_ids
    assert same_root_teacher.id in recipient_ids
    assert other_root_teacher.id not in recipient_ids
    assert root_b.owner_id == other_root_teacher.id
