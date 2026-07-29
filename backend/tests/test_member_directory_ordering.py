import pytest
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember


ROLE_PRIORITY = [
    TeamMember.Role.TEACHER,
    TeamMember.Role.OWNER,
    TeamMember.Role.CO_LEAD,
    TeamMember.Role.ADMIN,
    TeamMember.Role.ADVISOR,
    TeamMember.Role.MEMBER,
    TeamMember.Role.EXTERNAL,
]


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def response_rows(response):
    assert response.status_code == 200, response.json()
    payload = response.json()
    data = payload.get('data', payload)
    return data.get('results', data)


def make_root(make_user, *, code, owner_name='Owner'):
    owner = make_user(
        email=f'{code.lower()}-owner@members.test',
        name=owner_name,
    )
    root = Team.objects.create(
        name=f'{code} Root',
        code=f'{code}-ROOT',
        owner=owner,
    )
    TeamMember.objects.create(
        team=root,
        user=owner,
        role=TeamMember.Role.OWNER,
    )
    return root, owner


def make_squad(root, owner, *, code, name=None):
    squad = Team.objects.create(
        name=name or f'{code} Squad',
        code=f'{code}-SQUAD',
        owner=owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    return squad


@pytest.mark.api
@pytest.mark.django_db
def test_member_directory_defaults_to_team_role_priority_and_name(
    make_user,
):
    root, viewer = make_root(make_user, code='ORDER', owner_name='B Owner')
    expected = []
    for role, name in (
        (TeamMember.Role.TEACHER, 'Teacher'),
        (TeamMember.Role.CO_LEAD, 'Co Lead'),
        (TeamMember.Role.ADMIN, 'Admin'),
        (TeamMember.Role.ADVISOR, 'Advisor'),
        (TeamMember.Role.MEMBER, 'B Member'),
        (TeamMember.Role.MEMBER, 'A Member'),
        (TeamMember.Role.EXTERNAL, 'External'),
    ):
        user = make_user(
            email=f'{role}-{name.replace(" ", "-").lower()}@members.test',
            name=name,
            membership_status=(
                'external'
                if role == TeamMember.Role.EXTERNAL
                else 'active'
            ),
        )
        TeamMember.objects.create(team=root, user=user, role=role)
        expected.append((role, name, user.id))

    rows = response_rows(client_for(viewer).get('/api/v1/members/'))
    expected_ids = [
        user_id
        for _role, _name, user_id in sorted(
            expected + [(TeamMember.Role.OWNER, viewer.name, viewer.id)],
            key=lambda item: (
                ROLE_PRIORITY.index(item[0]),
                item[1],
            ),
        )
    ]

    assert [row['id'] for row in rows] == expected_ids
    assert [row['team_role'] for row in rows] == [
        next(
            role
            for role, _name, user_id in (
                expected
                + [(TeamMember.Role.OWNER, viewer.name, viewer.id)]
            )
            if user_id == row['id']
        )
        for row in rows
    ]
    assert rows[0]['team_role_display'] == '指导老师'


@pytest.mark.api
@pytest.mark.django_db
def test_highest_role_and_team_context_ignore_other_root_memberships(
    make_user,
):
    root_a, viewer = make_root(make_user, code='CONTEXT')
    squad_a = make_squad(root_a, viewer, code='CONTEXT-A')
    squad_b = make_squad(root_a, viewer, code='CONTEXT-B')
    root_b, other_owner = make_root(make_user, code='OTHER')

    multi_role = make_user(
        email='multi-role@members.test',
        name='Multi Role',
    )
    TeamMember.objects.create(
        team=squad_a,
        user=multi_role,
        role=TeamMember.Role.MEMBER,
    )
    TeamMember.objects.create(
        team=squad_b,
        user=multi_role,
        role=TeamMember.Role.TEACHER,
    )

    advisor = make_user(
        email='context-advisor@members.test',
        name='Context Advisor',
    )
    TeamMember.objects.create(
        team=squad_a,
        user=advisor,
        role=TeamMember.Role.ADVISOR,
    )

    cross_root = make_user(
        email='cross-root-role@members.test',
        name='Cross Root',
    )
    TeamMember.objects.create(
        team=squad_a,
        user=cross_root,
        role=TeamMember.Role.MEMBER,
    )
    TeamMember.objects.create(
        team=root_b,
        user=cross_root,
        role=TeamMember.Role.TEACHER,
    )

    default_rows = response_rows(
        client_for(viewer).get('/api/v1/members/')
    )
    by_id = {row['id']: row for row in default_rows}
    assert by_id[multi_role.id]['team_role'] == TeamMember.Role.TEACHER
    assert by_id[cross_root.id]['team_role'] == TeamMember.Role.MEMBER
    assert [
        membership['team_id']
        for membership in by_id[cross_root.id]['team_memberships']
    ] == [squad_a.id]
    assert [row['id'] for row in default_rows].index(advisor.id) < (
        [row['id'] for row in default_rows].index(cross_root.id)
    )
    assert other_owner.id not in by_id

    teacher_rows = response_rows(
        client_for(viewer).get(
            '/api/v1/members/',
            {'team_role': TeamMember.Role.TEACHER},
        )
    )
    assert [row['id'] for row in teacher_rows] == [multi_role.id]
    overall_member_rows = response_rows(
        client_for(viewer).get(
            '/api/v1/members/',
            {'team_role': TeamMember.Role.MEMBER},
        )
    )
    assert [row['id'] for row in overall_member_rows] == [cross_root.id]

    team_rows = response_rows(
        client_for(viewer).get(
            '/api/v1/members/',
            {'team': squad_a.id},
        )
    )
    team_by_id = {row['id']: row for row in team_rows}
    assert team_by_id[multi_role.id]['team_role'] == TeamMember.Role.MEMBER
    assert team_by_id[cross_root.id]['team_role'] == TeamMember.Role.MEMBER
    assert [row['id'] for row in team_rows].index(advisor.id) < (
        [row['id'] for row in team_rows].index(multi_role.id)
    )

    advisor_rows = response_rows(
        client_for(viewer).get(
            '/api/v1/members/',
            {
                'team': squad_a.id,
                'team_role': TeamMember.Role.ADVISOR,
            },
        )
    )
    assert [row['id'] for row in advisor_rows] == [advisor.id]

    member_rows = response_rows(
        client_for(viewer).get(
            '/api/v1/members/',
            {
                'team': squad_a.id,
                'role': TeamMember.Role.MEMBER,
            },
        )
    )
    assert {row['id'] for row in member_rows} == {
        multi_role.id,
        cross_root.id,
    }


@pytest.mark.api
@pytest.mark.django_db
def test_on_leave_relationships_are_current_and_memberships_are_stable(
    make_user,
):
    root, viewer = make_root(make_user, code='CURRENT')
    child_teacher = make_squad(
        root,
        viewer,
        code='CURRENT-TEACHER',
        name='A Teacher Squad',
    )
    child_advisor = make_squad(
        root,
        viewer,
        code='CURRENT-ADVISOR',
        name='B Advisor Squad',
    )
    child_member = make_squad(
        root,
        viewer,
        code='CURRENT-MEMBER',
        name='C Member Squad',
    )
    child_exited = make_squad(
        root,
        viewer,
        code='CURRENT-EXITED',
        name='D Exited Squad',
    )
    subject = make_user(
        email='current-subject@members.test',
        name='Current Subject',
        school='Current School',
        membership_status='on_leave',
    )
    TeamMember.objects.create(
        team=root,
        user=subject,
        role=TeamMember.Role.MEMBER,
    )
    TeamMember.objects.create(
        team=child_teacher,
        user=subject,
        role=TeamMember.Role.TEACHER,
        status=TeamMember.Status.ON_LEAVE,
    )
    TeamMember.objects.create(
        team=child_advisor,
        user=subject,
        role=TeamMember.Role.ADVISOR,
    )
    TeamMember.objects.create(
        team=child_member,
        user=subject,
        role=TeamMember.Role.MEMBER,
    )
    TeamMember.objects.create(
        team=child_exited,
        user=subject,
        role=TeamMember.Role.TEACHER,
        status=TeamMember.Status.EXITED,
    )

    rows = response_rows(
        client_for(viewer).get(
            '/api/v1/members/',
            {
                'school': subject.school,
                'membership_status': 'on_leave',
            },
        )
    )
    assert [row['id'] for row in rows] == [subject.id]
    assert rows[0]['team_role'] == TeamMember.Role.TEACHER
    assert [
        (item['team_id'], item['role'], item['status'])
        for item in rows[0]['team_memberships']
    ] == [
        (
            root.id,
            TeamMember.Role.MEMBER,
            TeamMember.Status.ACTIVE,
        ),
        (
            child_teacher.id,
            TeamMember.Role.TEACHER,
            TeamMember.Status.ON_LEAVE,
        ),
        (
            child_advisor.id,
            TeamMember.Role.ADVISOR,
            TeamMember.Status.ACTIVE,
        ),
        (
            child_member.id,
            TeamMember.Role.MEMBER,
            TeamMember.Status.ACTIVE,
        ),
    ]

    team_rows = response_rows(
        client_for(viewer).get(
            '/api/v1/members/',
            {'team': child_teacher.id},
        )
    )
    assert team_rows[0]['id'] == subject.id
    assert team_rows[0]['team_role'] == TeamMember.Role.TEACHER
    assert {row['id'] for row in team_rows} == {subject.id, viewer.id}
    assert next(
        row for row in team_rows if row['id'] == viewer.id
    )['team_role'] == TeamMember.Role.OWNER

    detail = client_for(viewer).get(
        f'/api/v1/members/{subject.id}/'
    )
    assert detail.status_code == 200, detail.json()
    detail_payload = detail.json()
    detail_data = detail_payload.get('data', detail_payload)
    assert [
        item['team_id']
        for item in detail_data['team_memberships']
    ] == [
        root.id,
        child_teacher.id,
        child_advisor.id,
        child_member.id,
    ]

    expanded_detail = client_for(viewer).get(
        '/api/v1/members/member-detail/',
        {'user_id': subject.id},
    )
    assert expanded_detail.status_code == 200, expanded_detail.json()
    expanded_payload = expanded_detail.json()
    expanded_data = expanded_payload.get('data', expanded_payload)
    assert [
        item['team_id']
        for item in expanded_data['team_memberships']
    ] == [
        root.id,
        child_teacher.id,
        child_advisor.id,
        child_member.id,
    ]


@pytest.mark.api
@pytest.mark.django_db
def test_team_filter_rejects_another_root(make_user):
    root_a, viewer = make_root(make_user, code='VISIBLE')
    root_b, other_owner = make_root(make_user, code='HIDDEN')
    visible_member = make_user(
        email='visible-member@members.test',
        name='Visible Member',
    )
    TeamMember.objects.create(team=root_a, user=visible_member)

    response = client_for(viewer).get(
        '/api/v1/members/',
        {'team': root_b.id},
    )
    assert response.status_code == 200
    assert response_rows(response) == []
    assert other_owner.id != viewer.id
