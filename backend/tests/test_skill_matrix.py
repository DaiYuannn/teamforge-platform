import pytest
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import (
    Competition,
    CompetitionEvent,
    CompetitionParticipant,
)
from apps.members.models import MemberSkill, SkillTag
from apps.users.models import User


MATRIX_URL = '/api/v1/skill-matrix/matrix/'
RECOMMENDATION_URL = '/api/v1/skill-matrix/recommendations/'


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def data_of(response):
    payload = response.json()
    return payload.get('data', payload)


def add_team_member(team, user, role=TeamMember.Role.MEMBER, status='active'):
    return TeamMember.objects.create(
        team=team,
        user=user,
        role=role,
        status=status,
    )


@pytest.fixture
def skill_matrix_context(make_project, make_user):
    owner = make_user(
        email='skill-owner@test.com',
        name='总负责人',
        school='示例大学',
    )
    viewer = make_user(
        email='skill-viewer@test.com',
        name='内部查看者',
        school='示例大学',
    )
    liu = make_user(
        email='skill-liu@test.com',
        name='刘宇成',
        school='示例大学计算机学院',
        major='计算机科学与技术',
    )
    member_without_match = make_user(
        email='skill-other@test.com',
        name='其他成员',
        school='示例大学',
        major='工业设计',
    )
    viewing_teacher = make_user(
        email='skill-viewing-teacher@test.com',
        name='查看老师',
        school='示例大学',
    )
    outsider = make_user(
        email='skill-outsider@test.com',
        name='跨团队人员',
        school='其他学校',
    )
    root = Team.objects.create(
        name='技能矩阵总团队',
        code='SKILL-MATRIX-ROOT',
        owner=owner,
    )
    other_root = Team.objects.create(
        name='其他总团队',
        code='SKILL-MATRIX-OTHER',
        owner=outsider,
    )
    add_team_member(root, owner, TeamMember.Role.OWNER)
    add_team_member(root, viewer, TeamMember.Role.MEMBER)
    add_team_member(root, liu, TeamMember.Role.MEMBER)
    add_team_member(root, member_without_match, TeamMember.Role.MEMBER)
    add_team_member(root, viewing_teacher, TeamMember.Role.TEACHER)
    add_team_member(other_root, outsider, TeamMember.Role.OWNER)

    python = SkillTag.objects.create(name='Python')
    vue = SkillTag.objects.create(name='Vue')
    design = SkillTag.objects.create(name='产品设计')
    MemberSkill.objects.create(user=liu, skill=python, proficiency=5)
    MemberSkill.objects.create(user=liu, skill=vue, proficiency=3)
    MemberSkill.objects.create(
        user=member_without_match,
        skill=design,
        proficiency=5,
    )
    return {
        'root': root,
        'owner': owner,
        'viewer': viewer,
        'liu': liu,
        'other': member_without_match,
        'viewing_teacher': viewing_teacher,
        'outsider': outsider,
        'python': python,
        'vue': vue,
        'design': design,
    }


@pytest.mark.api
@pytest.mark.django_db
def test_matrix_combines_pinyin_partial_fields_role_status_and_skill_filters(
    skill_matrix_context,
):
    context = skill_matrix_context
    response = client_for(context['viewer']).get(MATRIX_URL, {
        'search': 'LYC',
        'school': '大学计算',
        'major': '计算机科学',
        'team_role': '成员',
        'member_status': '在队',
        'skill': 'yth',
        'min_proficiency': 4,
    })

    assert response.status_code == 200, response.json()
    payload = data_of(response)
    assert payload['scope']['type'] == 'organization'
    assert [row['user_id'] for row in payload['members']] == [
        context['liu'].id
    ]
    assert payload['members'][0]['skills'][0] == {
        'id': context['liu'].skills.get(skill=context['python']).id,
        'skill_id': context['python'].id,
        'name': 'Python',
        'proficiency': 5,
    }
    assert context['outsider'].id not in {
        row['user_id'] for row in payload['members']
    }


@pytest.mark.api
@pytest.mark.django_db
def test_matrix_defaults_to_teacher_then_owner_then_members(
    skill_matrix_context,
):
    context = skill_matrix_context
    response = client_for(context['viewer']).get(MATRIX_URL)

    assert response.status_code == 200, response.json()
    member_ids = [row['user_id'] for row in data_of(response)['members']]
    assert member_ids.index(context['viewing_teacher'].id) < member_ids.index(
        context['owner'].id
    )
    assert member_ids.index(context['owner'].id) < member_ids.index(
        context['liu'].id
    )


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_viewing_teacher_can_read_but_matrix_has_no_write_method(
    skill_matrix_context,
):
    teacher = skill_matrix_context['viewing_teacher']
    client = client_for(teacher)

    assert client.get(MATRIX_URL).status_code == 200
    assert client.post(MATRIX_URL, {}, format='json').status_code == 405


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_external_matrix_is_self_only_without_an_entry(
    skill_matrix_context,
    make_user,
):
    context = skill_matrix_context
    external = make_user(
        email='matrix-external@test.com',
        name='外部协作者',
        membership_status=User.MembershipStatus.EXTERNAL,
    )
    response = client_for(external).get(MATRIX_URL)

    assert response.status_code == 200, response.json()
    payload = data_of(response)
    assert payload['scope']['type'] == 'self'
    assert [row['user_id'] for row in payload['members']] == [external.id]


@pytest.mark.api
@pytest.mark.django_db
def test_recommendations_rank_only_active_members_of_exact_entry(
    skill_matrix_context,
    make_project,
    make_user,
):
    context = skill_matrix_context
    project = make_project(
        leader=context['owner'],
        name='技能推荐项目',
        code='SKILL-RECOMMEND-PROJECT',
    )
    project.teams.add(context['root'])
    event = CompetitionEvent.objects.create(
        organization=context['root'],
        name='创新实践赛',
        edition='2026',
    )
    entry = Competition.objects.create(
        event=event,
        project=project,
        name=event.name,
        entry_name='项目技能队',
    )
    weaker = make_user(
        email='skill-weaker@test.com',
        name='只会 Python',
    )
    withdrawn = make_user(
        email='skill-withdrawn@test.com',
        name='已退出参赛',
    )
    exited = make_user(
        email='skill-exited@test.com',
        name='已离队成员',
        membership_status=User.MembershipStatus.EXITED,
    )
    non_participant = make_user(
        email='skill-nonparticipant@test.com',
        name='没有参赛',
    )
    for user in (weaker, withdrawn, exited, non_participant):
        add_team_member(context['root'], user)
    MemberSkill.objects.create(
        user=weaker,
        skill=context['python'],
        proficiency=4,
    )
    MemberSkill.objects.create(
        user=withdrawn,
        skill=context['python'],
        proficiency=5,
    )
    MemberSkill.objects.create(
        user=withdrawn,
        skill=context['vue'],
        proficiency=5,
    )
    MemberSkill.objects.create(
        user=exited,
        skill=context['python'],
        proficiency=5,
    )
    MemberSkill.objects.create(
        user=exited,
        skill=context['vue'],
        proficiency=5,
    )
    MemberSkill.objects.create(
        user=non_participant,
        skill=context['python'],
        proficiency=5,
    )
    MemberSkill.objects.create(
        user=non_participant,
        skill=context['vue'],
        proficiency=5,
    )
    CompetitionParticipant.objects.create(
        competition=entry,
        user=context['liu'],
        role=CompetitionParticipant.Role.LEADER,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )
    CompetitionParticipant.objects.create(
        competition=entry,
        user=weaker,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )
    CompetitionParticipant.objects.create(
        competition=entry,
        user=withdrawn,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.WITHDRAWN
        ),
    )
    CompetitionParticipant.objects.create(
        competition=entry,
        user=exited,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )

    response = client_for(context['viewer']).get(RECOMMENDATION_URL, {
        'competition_event': event.id,
        'competition_entry': entry.id,
        'required_skill_ids': (
            f"{context['python'].id},{context['vue'].id}"
        ),
        'min_proficiency': 3,
    })

    assert response.status_code == 200, response.json()
    payload = data_of(response)
    recommendations = payload['recommendations']
    assert [row['user_id'] for row in recommendations] == [
        context['liu'].id,
        weaker.id,
    ]
    assert recommendations[0]['rank'] == 1
    assert recommendations[0]['matched_count'] == 2
    assert recommendations[0]['missing_skills'] == []
    assert recommendations[1]['matched_count'] == 1
    assert recommendations[1]['missing_skills'][0]['name'] == 'Vue'
    assert '技能覆盖率' in payload['ranking_formula']


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_external_can_see_own_entry_but_not_another_entry(
    skill_matrix_context,
    make_project,
    make_user,
):
    context = skill_matrix_context
    project = make_project(
        leader=context['owner'],
        name='外部协作项目',
        code='EXTERNAL-SKILL-PROJECT',
    )
    project.teams.add(context['root'])
    event = CompetitionEvent.objects.create(
        organization=context['root'],
        name='外部协作赛',
        edition='2026',
    )
    own_entry = Competition.objects.create(
        event=event,
        project=project,
        name=event.name,
        entry_name='外部参与队',
    )
    other_entry = Competition.objects.create(
        event=event,
        project=project,
        name=event.name,
        entry_name='未参与队',
    )
    external = make_user(
        email='entry-external@test.com',
        name='参赛外部协作者',
        membership_status=User.MembershipStatus.EXTERNAL,
    )
    CompetitionParticipant.objects.create(
        competition=own_entry,
        user=external,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )
    CompetitionParticipant.objects.create(
        competition=own_entry,
        user=context['liu'],
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )
    client = client_for(external)

    own_response = client.get(MATRIX_URL, {
        'competition_event': event.id,
        'competition_entry': own_entry.id,
    })
    forbidden_response = client.get(MATRIX_URL, {
        'competition_event': event.id,
        'competition_entry': other_entry.id,
    })

    assert own_response.status_code == 200, own_response.json()
    assert {
        row['user_id'] for row in data_of(own_response)['members']
    } == {external.id, context['liu'].id}
    assert forbidden_response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_recommendations_accept_skill_name_and_reject_mismatched_event(
    skill_matrix_context,
    make_project,
):
    context = skill_matrix_context
    project = make_project(
        leader=context['owner'],
        name='名称技能项目',
        code='NAME-SKILL-PROJECT',
    )
    project.teams.add(context['root'])
    event = CompetitionEvent.objects.create(
        organization=context['root'],
        name='名称技能赛',
        edition='2026',
    )
    other_event = CompetitionEvent.objects.create(
        organization=context['root'],
        name='其他技能赛',
        edition='2026',
    )
    entry = Competition.objects.create(
        event=event,
        project=project,
        name=event.name,
        entry_name='名称技能队',
    )
    CompetitionParticipant.objects.create(
        competition=entry,
        user=context['liu'],
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )
    client = client_for(context['viewer'])

    named_response = client.get(RECOMMENDATION_URL, {
        'competition_event': event.id,
        'competition_entry': entry.id,
        'required_skills': 'python',
    })
    mismatch_response = client.get(RECOMMENDATION_URL, {
        'competition_event': other_event.id,
        'competition_entry': entry.id,
        'required_skills': 'Python',
    })

    assert named_response.status_code == 200, named_response.json()
    assert data_of(named_response)['required_skills'][0]['name'] == 'Python'
    assert mismatch_response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_skill_matrix_requires_authentication(api_client):
    assert api_client.get(MATRIX_URL).status_code in (401, 403)
    assert api_client.get(RECOMMENDATION_URL).status_code in (401, 403)
