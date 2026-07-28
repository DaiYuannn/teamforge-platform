import pytest
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import Competition, CompetitionParticipant
from apps.contributions.models import Contribution
from apps.projects.models import ProjectMember


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def response_data(response):
    payload = response.json()
    return payload.get('data', payload) if isinstance(payload, dict) else payload


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_competition_execution_detail_explains_roles_and_reusable_evidence(
    make_project,
    make_user,
):
    project_leader = make_user(
        email='execution-project-leader@test.com',
        name='项目牵头人',
    )
    execution_leader = make_user(
        email='execution-competition-leader@test.com',
        name='比赛执行人',
    )
    project = make_project(
        leader=project_leader,
        name='安全创新项目',
    )
    ProjectMember.objects.create(
        project=project,
        user=execution_leader,
        role_in_project=ProjectMember.RoleInProject.LEADER,
    )
    squad = Team.objects.create(
        name='安全比赛小组',
        code='COMP-EXEC-SQUAD',
        owner=project_leader,
    )
    TeamMember.objects.create(team=squad, user=execution_leader)
    project.teams.add(squad)

    competition = Competition.objects.create(
        project=project,
        name='安全创新挑战赛',
    )
    CompetitionParticipant.objects.create(
        competition=competition,
        user=execution_leader,
        role=CompetitionParticipant.Role.LEADER,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
        responsibility='负责材料统筹与现场答辩',
    )
    direct = Contribution.objects.create(
        project=project,
        user=execution_leader,
        contribution_type=Contribution.ContributionType.COMPETITION,
        source_type=Contribution.SourceType.COMPETITION,
        related_object_id=competition.id,
        content='完成本场比赛答辩稿',
        status=Contribution.Status.PENDING,
        source_verified=False,
    )
    reusable_same_project = Contribution.objects.create(
        project=project,
        user=execution_leader,
        contribution_type=Contribution.ContributionType.STAGE_TASK,
        source_type=Contribution.SourceType.TASK,
        related_object_id=9001,
        content='已核验的用户调研数据',
        status=Contribution.Status.APPROVED,
        source_verified=True,
    )

    reusable_project = make_project(
        leader=project_leader,
        name='历史材料项目',
    )
    ProjectMember.objects.create(
        project=reusable_project,
        user=execution_leader,
    )
    origin_competition = Competition.objects.create(
        project=reusable_project,
        name='往届安全赛事',
    )
    reusable_other_project = Contribution.objects.create(
        project=reusable_project,
        user=execution_leader,
        contribution_type=Contribution.ContributionType.COMPETITION,
        source_type=Contribution.SourceType.COMPETITION,
        related_object_id=origin_competition.id,
        content='往届已核验答辩图表',
        status=Contribution.Status.APPROVED,
        source_verified=True,
    )
    unverified = Contribution.objects.create(
        project=project,
        user=execution_leader,
        contribution_type=Contribution.ContributionType.RESOURCE,
        content='尚未核验的参考资料',
        status=Contribution.Status.APPROVED,
        source_verified=False,
    )

    response = client_for(project_leader).get(
        f'/api/v1/competitions/{competition.id}/'
    )

    assert response.status_code == 200, response.json()
    detail = response_data(response)
    assert detail['project_leader_names'] == ['项目牵头人', '比赛执行人']
    assert detail['leader_names'] == ['比赛执行人']
    assert detail['project_team_names'] == ['安全比赛小组']
    assert detail['participants'][0]['responsibility'] == (
        '负责材料统筹与现场答辩'
    )

    assert [item['id'] for item in detail['competition_contributions']] == [
        direct.id
    ]
    assert detail['competition_contributions'][0]['reuse_eligible'] is False
    reusable_by_id = {
        item['id']: item
        for item in detail['reusable_contributions']
    }
    assert set(reusable_by_id) == {
        reusable_same_project.id,
        reusable_other_project.id,
    }
    assert reusable_by_id[reusable_same_project.id]['reuse_scope'] == (
        'same_project'
    )
    assert reusable_by_id[reusable_other_project.id]['reuse_scope'] == (
        'visible_other_project'
    )
    assert reusable_by_id[
        reusable_other_project.id
    ]['origin_competition_name'] == '往届安全赛事'
    assert unverified.id not in reusable_by_id
    assert '重复计分' in detail['contribution_reuse_note']


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_reusable_evidence_does_not_leak_invisible_project_contributions(
    make_project,
    make_user,
):
    viewer = make_user(email='execution-viewer@test.com')
    participant = make_user(email='execution-participant@test.com')
    project = make_project(leader=viewer, visibility='project')
    ProjectMember.objects.create(project=project, user=participant)
    competition = Competition.objects.create(project=project, name='当前比赛')
    CompetitionParticipant.objects.create(
        competition=competition,
        user=participant,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )

    hidden_leader = make_user(email='hidden-project-leader@test.com')
    hidden_project = make_project(
        leader=hidden_leader,
        visibility='project',
    )
    ProjectMember.objects.create(project=hidden_project, user=participant)
    hidden_contribution = Contribution.objects.create(
        project=hidden_project,
        user=participant,
        contribution_type=Contribution.ContributionType.RESOURCE,
        content='其他私密项目的材料',
        status=Contribution.Status.APPROVED,
        source_verified=True,
    )

    response = client_for(viewer).get(
        f'/api/v1/competitions/{competition.id}/'
    )

    assert response.status_code == 200, response.json()
    reusable_ids = {
        item['id']
        for item in response_data(response)['reusable_contributions']
    }
    assert hidden_contribution.id not in reusable_ids
