import pytest
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.competitions.member_search import (
    member_matches_search,
    name_pinyin_forms,
)
from apps.competitions.models import Competition, CompetitionEvent
from common.project_access import scope_project_queryset


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


@pytest.mark.parametrize(
    ('query', 'name'),
    [
        ('刘', '刘宇成'),
        ('宇', '刘宇成'),
        ('liuyucheng', '刘宇成'),
        ('LIU', '刘宇成'),
        ('lyc', '刘宇成'),
        ('L', '刘宇成'),
        ('shanxiaozhi', '单小智'),
        ('sxz', '单小智'),
        ('danxiaozhi', '单小智'),
        ('DXZ', '单小智'),
    ],
)
def test_member_search_supports_chinese_pinyin_initials_and_case(query, name):
    assert member_matches_search(query=query, values=[name], name=name)


def test_polyphonic_name_generates_multiple_search_forms():
    forms = name_pinyin_forms('单小智')
    assert 'shanxiaozhi' in forms
    assert 'sxz' in forms
    assert 'danxiaozhi' in forms
    assert 'dxz' in forms


@pytest.mark.api
@pytest.mark.django_db
def test_event_groups_project_entries_and_candidates_come_from_root_team(
    make_project,
    make_user,
):
    root_owner = make_user(email='root-owner@test.com', name='总团队负责人')
    project_leader = make_user(email='project-leader@test.com', name='项目负责人')
    candidate = make_user(
        email='liu-yucheng@test.com',
        name='刘宇成',
        school='示例大学',
        grade='大三',
        major='软件工程',
    )
    outsider = make_user(
        email='outsider-root@test.com',
        name='外部根团队成员',
        school='其他大学',
    )
    root = Team.objects.create(
        name='总团队',
        code='ROOT-COMP-ORG',
        owner=root_owner,
    )
    squad = Team.objects.create(
        name='历史固定小组',
        code='LEGACY-SQUAD-COMP-ORG',
        owner=project_leader,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    other_root = Team.objects.create(
        name='其他总团队',
        code='OTHER-ROOT-COMP-ORG',
        owner=outsider,
    )
    TeamMember.objects.create(
        team=root,
        user=root_owner,
        role=TeamMember.Role.OWNER,
    )
    TeamMember.objects.create(
        team=root,
        user=project_leader,
        role=TeamMember.Role.CO_LEAD,
    )
    TeamMember.objects.create(
        team=root,
        user=candidate,
        role=TeamMember.Role.MEMBER,
    )
    TeamMember.objects.create(
        team=other_root,
        user=outsider,
        role=TeamMember.Role.OWNER,
    )

    first_project = make_project(
        leader=project_leader,
        name='项目甲',
        code='COMP-EVENT-A',
    )
    second_project = make_project(
        leader=project_leader,
        name='项目乙',
        code='COMP-EVENT-B',
    )
    first_project.teams.add(squad)
    second_project.teams.add(squad)
    event = CompetitionEvent.objects.create(
        name='创新创业大赛',
        edition='2026',
        organizer='示例主办方',
    )
    first_entry = Competition.objects.create(
        event=event,
        project=first_project,
        name=event.name,
        organizer=event.organizer,
        entry_name='项目甲参赛队',
    )
    Competition.objects.create(
        event=event,
        project=second_project,
        name=event.name,
        organizer=event.organizer,
        entry_name='项目乙参赛队',
    )

    manager_client = client_for(project_leader)
    assert first_entry.id in set(
        scope_project_queryset(
            Competition.objects.all(),
            project_leader,
            project_lookup='project',
        ).values_list('id', flat=True)
    )
    events_response = manager_client.get('/api/v1/competitions/events/')
    entries_response = manager_client.get(
        f'/api/v1/competitions/?event={event.id}&page_size=100'
    )
    candidates_response = manager_client.get(
        f'/api/v1/competitions/{first_entry.id}/participant-candidates/',
        {
            'search': 'LYC',
            'school': '示例大学',
            'team_role': TeamMember.Role.MEMBER,
            'membership_status': 'active',
        },
    )

    assert events_response.status_code == 200, events_response.json()
    assert entries_response.status_code == 200, entries_response.json()
    assert candidates_response.status_code == 200, candidates_response.json()
    assert response_results(events_response)[0]['entry_count'] == 2
    assert {
        row['project_name'] for row in response_results(entries_response)
    } == {'项目甲', '项目乙'}
    candidates = response_data(candidates_response)
    assert [row['id'] for row in candidates] == [candidate.id]
    assert candidates[0]['school'] == '示例大学'
    assert candidates[0]['team_role'] == TeamMember.Role.MEMBER

    added = manager_client.post(
        f'/api/v1/competitions/{first_entry.id}/participants/',
        {
            'user': candidate.id,
            'role': 'member',
            'participation_status': 'confirmed',
        },
        format='json',
    )
    assert added.status_code == 201, added.json()
    assert not first_project.members.filter(user=candidate).exists()

    # A competition roster assignment does not mutate the total-team directory.
    assert TeamMember.objects.filter(
        team=root,
        user=candidate,
        role=TeamMember.Role.MEMBER,
    ).exists()

    after_add = manager_client.get(
        f'/api/v1/competitions/{first_entry.id}/participant-candidates/',
        {'search': '刘'},
    )
    assert candidate.id not in {
        row['id'] for row in response_data(after_add)
    }


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_operating_teacher_can_manage_candidates_but_legacy_event_stays_invalid(
    make_project,
    make_user,
):
    first_owner = make_user(email='first-root-owner@test.com')
    second_teacher = make_user(
        email='second-root-teacher@test.com',
        global_role='teacher',
    )
    first_root = Team.objects.create(
        name='第一总团队',
        code='FIRST-ROOT-CANDIDATE-BOUNDARY',
        owner=first_owner,
    )
    second_root = Team.objects.create(
        name='第二总团队',
        code='SECOND-ROOT-CANDIDATE-BOUNDARY',
        owner=second_teacher,
    )
    TeamMember.objects.create(
        team=first_root,
        user=first_owner,
        role=TeamMember.Role.OWNER,
    )
    TeamMember.objects.create(
        team=second_root,
        user=second_teacher,
        role=TeamMember.Role.TEACHER,
    )
    project = make_project(
        leader=first_owner,
        code='CROSS-ROOT-CANDIDATE-PROJECT',
    )
    project.teams.add(first_root)
    entry = Competition.objects.create(
        project=project,
        name='跨组织边界测试赛',
    )

    teacher_response = client_for(second_teacher).get(
        f'/api/v1/competitions/{entry.id}/participant-candidates/'
    )
    assert teacher_response.status_code == 200, teacher_response.json()

    legacy_event = CompetitionEvent.objects.create(
        name='无组织旧比赛',
        edition='2026',
    )
    attach_response = client_for(first_owner).patch(
        f'/api/v1/competitions/{entry.id}/',
        {'event': legacy_event.id},
        format='json',
    )
    assert attach_response.status_code == 400, attach_response.json()
    entry.refresh_from_db()
    assert entry.event_id != legacy_event.id
