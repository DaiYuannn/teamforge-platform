import pytest
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import (
    Competition,
    CompetitionEvent,
    CompetitionParticipant,
)
from apps.projects.models import ProjectMember
from apps.tasks.models import Task


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def result_rows(response):
    payload = response.json()
    data = payload.get('data', payload)
    return data.get('results', data)


def make_root_and_squad(*, root_owner, squad_owner, suffix):
    root = Team.objects.create(
        name=f'总团队 {suffix}',
        code=f'ROOT-{suffix}',
        owner=root_owner,
    )
    squad = Team.objects.create(
        name=f'小团队 {suffix}',
        code=f'SQUAD-{suffix}',
        owner=squad_owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    return root, squad


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_teacher_my_teams_scope_does_not_mix_other_organizations(
    make_project,
    make_user,
):
    teacher = make_user(
        email='focused-teacher@test.com',
        global_role='teacher',
    )
    first_owner = make_user(email='first-root-owner@test.com')
    first_squad_owner = make_user(email='first-squad-owner@test.com')
    first_root, first_squad = make_root_and_squad(
        root_owner=first_owner,
        squad_owner=first_squad_owner,
        suffix='TEACHER-A',
    )
    TeamMember.objects.create(
        team=first_root,
        user=teacher,
        role=TeamMember.Role.TEACHER,
    )
    own_project = make_project(name='老师指导团队的项目')
    own_project.teams.add(first_squad)

    second_owner = make_user(email='second-root-owner@test.com')
    second_squad_owner = make_user(email='second-squad-owner@test.com')
    _, second_squad = make_root_and_squad(
        root_owner=second_owner,
        squad_owner=second_squad_owner,
        suffix='TEACHER-B',
    )
    other_project = make_project(name='其他组织的项目')
    other_project.teams.add(second_squad)

    focused = client_for(teacher).get(
        '/api/v1/projects/?scope=my_teams&page_size=100'
    )
    all_visible = client_for(teacher).get(
        '/api/v1/projects/?scope=visible&page_size=100'
    )

    assert focused.status_code == 200
    assert {row['id'] for row in result_rows(focused)} == {own_project.id}
    assert {own_project.id, other_project.id}.issubset(
        {row['id'] for row in result_rows(all_visible)}
    )


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_legacy_teacher_without_team_relation_gets_visible_fallback(
    make_project,
    make_user,
):
    teacher = make_user(
        email='legacy-teacher-without-team@test.com',
        global_role='teacher',
    )
    first = make_project(name='旧教师可见项目一')
    second = make_project(name='旧教师可见项目二')

    response = client_for(teacher).get(
        '/api/v1/projects/?scope=my_teams&page_size=100'
    )

    assert response.status_code == 200
    assert {first.id, second.id}.issubset(
        {row['id'] for row in result_rows(response)}
    )


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_project_perspectives_separate_team_management_and_participation(
    make_project,
    make_user,
):
    root_owner = make_user(email='perspective-root-owner@test.com')
    manager = make_user(email='perspective-manager@test.com')
    other_squad_owner = make_user(email='other-squad-owner@test.com')
    root, managed_squad = make_root_and_squad(
        root_owner=root_owner,
        squad_owner=manager,
        suffix='PERSPECTIVE-A',
    )
    participating_squad = Team.objects.create(
        name='参与项目小团队',
        code='SQUAD-PERSPECTIVE-B',
        owner=other_squad_owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )

    managed_project = make_project(name='我管理的小团队项目')
    managed_project.teams.add(managed_squad)
    participating_project = make_project(name='我参与但不管理的项目')
    participating_project.teams.add(participating_squad)
    ProjectMember.objects.create(
        project=participating_project,
        user=manager,
        role_in_project=ProjectMember.RoleInProject.CORE,
    )
    client = client_for(manager)

    scopes = {
        scope: {
            row['id']
            for row in result_rows(client.get(
                f'/api/v1/projects/?scope={scope}&page_size=100'
            ))
        }
        for scope in ('my_teams', 'managed', 'participating', 'visible')
    }

    assert scopes['my_teams'] == {managed_project.id}
    assert scopes['managed'] == {managed_project.id}
    assert scopes['participating'] == {participating_project.id}
    assert scopes['visible'] == {managed_project.id, participating_project.id}

    root_filter = client.get(
        f'/api/v1/projects/?scope=visible&team={root.id}&page_size=100'
    )
    squad_filter = client.get(
        f'/api/v1/projects/?scope=visible&team={managed_squad.id}&page_size=100'
    )
    assert {
        row['id'] for row in result_rows(root_filter)
    } == {managed_project.id, participating_project.id}
    assert {
        row['id'] for row in result_rows(squad_filter)
    } == {managed_project.id}


@pytest.mark.api
@pytest.mark.django_db
def test_project_list_explains_team_project_and_competition_responsibility(
    make_project,
    make_user,
):
    root_owner = make_user(email='summary-root-owner@test.com')
    squad_owner = make_user(
        email='summary-squad-owner@test.com',
        name='小团队负责人',
    )
    co_lead = make_user(email='summary-co-lead@test.com', name='共同负责人')
    worker = make_user(email='summary-worker@test.com', name='任务执行人')
    _, squad = make_root_and_squad(
        root_owner=root_owner,
        squad_owner=squad_owner,
        suffix='SUMMARY',
    )
    TeamMember.objects.create(
        team=squad,
        user=co_lead,
        role=TeamMember.Role.CO_LEAD,
    )
    project = make_project(name='责任清晰项目')
    project.teams.add(squad)
    ProjectMember.objects.create(
        project=project,
        user=co_lead,
        role_in_project=ProjectMember.RoleInProject.LEADER,
    )
    ProjectMember.objects.create(
        project=project,
        user=worker,
        role_in_project=ProjectMember.RoleInProject.CORE,
    )
    Task.objects.create(
        project=project,
        title='完成安全赛计划书',
        assignee=worker,
        status=Task.Status.DOING,
    )
    event = CompetitionEvent.objects.create(
        name='安全创新比赛',
        edition='2026',
    )
    competition = Competition.objects.create(
        project=project,
        name='安全创新比赛',
        event=event,
        entry_name='星火参赛队',
    )
    CompetitionParticipant.objects.create(
        competition=competition,
        user=co_lead,
        role=CompetitionParticipant.Role.LEADER,
        participation_status=CompetitionParticipant.ParticipationStatus.CONFIRMED,
    )
    CompetitionParticipant.objects.create(
        competition=competition,
        user=worker,
        responsibility='负责计划书与演示',
        participation_status=CompetitionParticipant.ParticipationStatus.CONFIRMED,
    )

    response = client_for(project.leader).get(
        '/api/v1/projects/?scope=participating&page_size=100'
    )
    assert response.status_code == 200
    row = next(item for item in result_rows(response) if item['id'] == project.id)

    assert row['leader_name'] == project.leader.name
    assert row['co_leader_names'] == ['共同负责人']
    assert row['team_details'][0]['leader_names'] == [
        '小团队负责人',
        '共同负责人',
    ]
    assert row['competition_summaries'][0]['leader_names'] == ['共同负责人']
    assert row['competition_summaries'][0]['event_name'] == '安全创新比赛'
    assert row['competition_summaries'][0]['event_edition'] == '2026'
    assert row['competition_summaries'][0]['entry_name'] == '星火参赛队'
    assert (
        row['competition_summaries'][0]['display_name']
        == '安全创新比赛（2026） / 星火参赛队'
    )
    worker_summary = next(
        item
        for item in row['member_work_summary']
        if item['user_id'] == worker.id
    )
    assert worker_summary['active_task_titles'] == ['完成安全赛计划书']
    assert worker_summary['competition_names'] == [
        '安全创新比赛（2026） / 星火参赛队',
    ]
    assert worker_summary['competition_responsibilities'] == [{
        'competition_name': '安全创新比赛（2026） / 星火参赛队',
        'responsibility': '负责计划书与演示',
    }]
