import pytest
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember


MEMBERS_URL = '/api/v1/members/'


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def response_rows(response):
    assert response.status_code == 200, response.json()
    payload = response.json()
    data = payload.get('data', payload)
    return data.get('results', data)


@pytest.fixture
def searchable_directory(make_user):
    viewer = make_user(
        email='directory-owner@search.test',
        name='Directory Owner',
    )
    root = Team.objects.create(
        name='Search Root',
        code='SEARCH-DIRECTORY-ROOT',
        owner=viewer,
    )
    squad = Team.objects.create(
        name='Alpha Research Squad',
        code='SEARCH-DIRECTORY-SQUAD',
        owner=viewer,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(
        team=root,
        user=viewer,
        role=TeamMember.Role.OWNER,
    )

    target = make_user(
        email='MixedCase.Member@Search.Test',
        name='刘宇成',
        phone='13876543210',
        school='South China Tech University',
        major='Computer Science and Engineering',
        grade='Grade 2024',
        membership_status='on_leave',
    )
    target.username = 'LiuYC_Profile'
    target.save(update_fields=['username'])
    TeamMember.objects.create(
        team=squad,
        user=target,
        role=TeamMember.Role.ADVISOR,
        status=TeamMember.Status.ON_LEAVE,
    )

    distractor = make_user(
        email='unrelated@search.test',
        name='无关成员',
        phone='15500001111',
        school='North Design College',
        major='Visual Design',
        grade='Grade 2023',
    )
    distractor.username = 'unrelated_profile'
    distractor.save(update_fields=['username'])
    TeamMember.objects.create(
        team=root,
        user=distractor,
        role=TeamMember.Role.MEMBER,
    )

    other_owner = make_user(
        email='other-owner@search.test',
        name='Other Root Owner',
    )
    other_root = Team.objects.create(
        name='Other Search Root',
        code='OTHER-SEARCH-DIRECTORY-ROOT',
        owner=other_owner,
    )
    TeamMember.objects.create(
        team=other_root,
        user=other_owner,
        role=TeamMember.Role.OWNER,
    )
    hidden_match = make_user(
        email='hidden-match@search.test',
        name='刘宇成',
        school=target.school,
        major=target.major,
        grade=target.grade,
    )
    TeamMember.objects.create(
        team=other_root,
        user=hidden_match,
        role=TeamMember.Role.ADVISOR,
        status=TeamMember.Status.ON_LEAVE,
    )
    return {
        'viewer': viewer,
        'root': root,
        'squad': squad,
        'target': target,
        'distractor': distractor,
        'hidden_match': hidden_match,
    }


@pytest.mark.api
@pytest.mark.parametrize(
    'keyword',
    [
        '宇',
        'LIUYUCHENG',
        'LYC',
        'yC_Pro',
        '876543',
        'mixedcase.member',
        'china tech',
        'science and engineering',
        '2024',
        '顾问',
        '暂离',
        'research squad',
    ],
)
@pytest.mark.django_db
def test_general_keyword_covers_identity_profile_role_status_and_pinyin(
    searchable_directory,
    keyword,
):
    ctx = searchable_directory
    rows = response_rows(
        client_for(ctx['viewer']).get(
            MEMBERS_URL,
            {'search': keyword},
        ),
    )
    ids = {row['id'] for row in rows}
    assert ctx['target'].id in ids
    assert ctx['distractor'].id not in ids
    assert ctx['hidden_match'].id not in ids


@pytest.mark.api
@pytest.mark.django_db
def test_general_keyword_uses_and_semantics_and_supports_aliases(
    searchable_directory,
):
    ctx = searchable_directory
    client = client_for(ctx['viewer'])

    combined = response_rows(
        client.get(MEMBERS_URL, {'search': 'LIU science 2024'}),
    )
    assert [row['id'] for row in combined] == [ctx['target'].id]

    keyword_alias = response_rows(
        client.get(MEMBERS_URL, {'keyword': 'LYC'}),
    )
    assert [row['id'] for row in keyword_alias] == [ctx['target'].id]

    q_alias = response_rows(
        client.get(MEMBERS_URL, {'q': '宇'}),
    )
    assert [row['id'] for row in q_alias] == [ctx['target'].id]


@pytest.mark.api
@pytest.mark.django_db
def test_profile_text_fields_are_case_insensitive_partial_matches(
    searchable_directory,
):
    ctx = searchable_directory
    client = client_for(ctx['viewer'])

    rows = response_rows(
        client.get(
            MEMBERS_URL,
            {
                'school': 'CHINA TECH',
                'major': 'SCIENCE AND',
                'grade': '202',
            },
        ),
    )
    assert [row['id'] for row in rows] == [ctx['target'].id]

    exact_alias = response_rows(
        client.get(
            MEMBERS_URL,
            {'school_exact': 'south china tech university'},
        ),
    )
    assert [row['id'] for row in exact_alias] == [ctx['target'].id]


@pytest.mark.api
@pytest.mark.django_db
def test_role_and_status_text_search_coexist_with_exact_dropdown_filters(
    searchable_directory,
):
    ctx = searchable_directory
    client = client_for(ctx['viewer'])

    text_rows = response_rows(
        client.get(
            MEMBERS_URL,
            {
                'role_search': 'ADVIS',
                'status_search': 'LEAV',
            },
        ),
    )
    assert [row['id'] for row in text_rows] == [ctx['target'].id]

    display_rows = response_rows(
        client.get(
            MEMBERS_URL,
            {
                'role_text': '顾',
                'status_text': '暂',
            },
        ),
    )
    assert [row['id'] for row in display_rows] == [ctx['target'].id]

    exact_rows = response_rows(
        client.get(
            MEMBERS_URL,
            {
                'team': ctx['squad'].id,
                'team_role': TeamMember.Role.ADVISOR,
                'membership_status': 'on_leave',
            },
        ),
    )
    assert [row['id'] for row in exact_rows] == [ctx['target'].id]

    wrong_exact_role = response_rows(
        client.get(
            MEMBERS_URL,
            {
                'team': ctx['squad'].id,
                'team_role': TeamMember.Role.MEMBER,
            },
        ),
    )
    assert ctx['target'].id not in {
        row['id'] for row in wrong_exact_role
    }


@pytest.mark.api
@pytest.mark.django_db
def test_selected_team_search_uses_only_that_team_role_context(make_user):
    viewer = make_user(
        email='context-search-owner@test.com',
        name='上下文负责人',
    )
    root = Team.objects.create(
        name='上下文总团队',
        code='CONTEXT-SEARCH-ROOT',
        owner=viewer,
    )
    team_a = Team.objects.create(
        name='A 项目队',
        code='CONTEXT-SEARCH-A',
        owner=viewer,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    team_b = Team.objects.create(
        name='B 项目队',
        code='CONTEXT-SEARCH-B',
        owner=viewer,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(
        team=root,
        user=viewer,
        role=TeamMember.Role.OWNER,
    )
    subject = make_user(
        email='multi-team-search@test.com',
        name='跨队成员',
        membership_status='on_leave',
    )
    TeamMember.objects.create(
        team=team_a,
        user=subject,
        role=TeamMember.Role.MEMBER,
    )
    TeamMember.objects.create(
        team=team_b,
        user=subject,
        role=TeamMember.Role.ADVISOR,
    )

    client = client_for(viewer)
    team_a_rows = response_rows(
        client.get(
            MEMBERS_URL,
            {'team': team_a.id, 'search': '顾问'},
        ),
    )
    assert subject.id not in {row['id'] for row in team_a_rows}

    global_values_rows = response_rows(
        client.get(
            MEMBERS_URL,
            {
                'team': team_a.id,
                'search': '普通成员 暂离',
            },
        ),
    )
    assert [row['id'] for row in global_values_rows] == [subject.id]

    team_b_rows = response_rows(
        client.get(
            MEMBERS_URL,
            {'team': team_b.id, 'search': '顾问'},
        ),
    )
    assert [row['id'] for row in team_b_rows] == [subject.id]
    assert {
        membership['team_id']
        for membership in team_b_rows[0]['team_memberships']
    } == {team_a.id, team_b.id}
