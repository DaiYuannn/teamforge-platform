import importlib
from types import SimpleNamespace

import pytest
from django.apps import apps as django_apps
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.notifications.models import Announcement
from apps.notifications.announcement_access import announcement_management_scope
from apps.notifications.serializers import AnnouncementSerializer
from apps.projects.models import ProjectMember


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


def _results(response):
    payload = response.json()
    data = payload.get('data', payload)
    return data.get('results', data) if isinstance(data, dict) else data


def _make_root(make_user, code):
    owner = make_user(email=f'{code.lower()}-owner@test.com')
    root = Team.objects.create(
        name=f'{code}实践团队',
        code=f'{code}-ROOT',
        owner=owner,
    )
    TeamMember.objects.create(
        team=root,
        user=owner,
        role=TeamMember.Role.OWNER,
    )
    return root, owner


def _make_squad(root, owner, code):
    squad = Team.objects.create(
        name=f'{code}小团队',
        code=f'{code}-SQUAD',
        owner=owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(
        team=squad,
        user=owner,
        role=TeamMember.Role.OWNER,
    )
    return squad


@pytest.mark.api
@pytest.mark.django_db
class TestAnnouncementAudienceVisibility:
    def test_published_audiences_follow_root_squad_and_project_membership(
        self,
        make_user,
        make_project,
    ):
        root_a, owner_a = _make_root(make_user, 'A')
        root_b, owner_b = _make_root(make_user, 'B')
        squad_a1 = _make_squad(root_a, owner_a, 'A1')
        squad_a2 = _make_squad(root_a, owner_a, 'A2')
        squad_b = _make_squad(root_b, owner_b, 'B1')
        member_a1 = make_user(email='audience-a1@test.com')
        member_a2 = make_user(email='audience-a2@test.com')
        member_b = make_user(email='audience-b@test.com')
        TeamMember.objects.create(team=squad_a1, user=member_a1)
        TeamMember.objects.create(team=squad_a2, user=member_a2)
        TeamMember.objects.create(team=squad_b, user=member_b)

        organization_announcement = Announcement.objects.create(
            title='A全团队公告',
            content='A',
            status=Announcement.Status.PUBLISHED,
            audience=Announcement.Audience.ORGANIZATION,
            organization=root_a,
            author=owner_a,
        )
        team_announcement = Announcement.objects.create(
            title='A1小团队公告',
            content='A1',
            status=Announcement.Status.PUBLISHED,
            audience=Announcement.Audience.TEAMS,
            organization=root_a,
            author=owner_a,
        )
        team_announcement.target_teams.add(squad_a1)

        project = make_project(leader=owner_a, code='ANN-PROJ')
        project.teams.add(squad_a1)
        ProjectMember.objects.create(project=project, user=member_a1)
        project_announcement = Announcement.objects.create(
            title='A项目公告',
            content='project',
            status=Announcement.Status.PUBLISHED,
            audience=Announcement.Audience.PROJECTS,
            organization=root_a,
            author=owner_a,
        )
        project_announcement.target_projects.add(project)

        public_announcement = Announcement.objects.create(
            title='公开公告',
            content='public',
            status=Announcement.Status.PUBLISHED,
            audience=Announcement.Audience.PUBLIC,
            organization=root_a,
            author=owner_a,
        )

        titles_a1 = {
            item['title']
            for item in _results(
                _client(member_a1).get('/api/v1/notifications/announcements/')
            )
        }
        assert titles_a1 == {
            organization_announcement.title,
            team_announcement.title,
            project_announcement.title,
            public_announcement.title,
        }

        titles_a2 = {
            item['title']
            for item in _results(
                _client(member_a2).get('/api/v1/notifications/announcements/')
            )
        }
        assert titles_a2 == {'A全团队公告', '公开公告'}

        titles_b = {
            item['title']
            for item in _results(
                _client(member_b).get('/api/v1/notifications/announcements/')
            )
        }
        assert titles_b == {'公开公告'}

    def test_drafts_are_tenant_and_management_scoped(self, make_user):
        root_a, owner_a = _make_root(make_user, 'DA')
        root_b, owner_b = _make_root(make_user, 'DB')
        squad_a = _make_squad(root_a, owner_a, 'DA1')
        member_a = make_user(email='draft-member-a@test.com')
        TeamMember.objects.create(team=squad_a, user=member_a)

        root_draft = Announcement.objects.create(
            title='A根团队草稿',
            content='root draft',
            status=Announcement.Status.DRAFT,
            audience=Announcement.Audience.ORGANIZATION,
            organization=root_a,
            author=owner_a,
        )
        squad_draft = Announcement.objects.create(
            title='A子队草稿',
            content='squad draft',
            status=Announcement.Status.DRAFT,
            audience=Announcement.Audience.TEAMS,
            organization=root_a,
            author=owner_a,
        )
        squad_draft.target_teams.add(squad_a)
        Announcement.objects.create(
            title='B团队草稿',
            content='other tenant',
            status=Announcement.Status.DRAFT,
            audience=Announcement.Audience.ORGANIZATION,
            organization=root_b,
            author=owner_b,
        )

        owner_titles = {
            item['title']
            for item in _results(
                _client(owner_a).get('/api/v1/notifications/announcements/')
            )
        }
        assert owner_titles == {root_draft.title, squad_draft.title}
        assert _results(
            _client(member_a).get('/api/v1/notifications/announcements/')
        ) == []

    def test_unbound_global_manager_gets_no_tenant_access_once_roots_exist(
        self,
        make_user,
    ):
        root_a, owner_a = _make_root(make_user, 'BOUND')
        teacher = make_user(
            email='unbound-announcement-teacher@test.com',
            global_role='teacher',
        )
        Announcement.objects.create(
            title='绑定团队草稿',
            content='private',
            status=Announcement.Status.DRAFT,
            audience=Announcement.Audience.ORGANIZATION,
            organization=root_a,
            author=owner_a,
        )

        response = _client(teacher).get('/api/v1/notifications/announcements/')
        assert response.status_code == 200
        assert _results(response) == []

        create_response = _client(teacher).post(
            '/api/v1/notifications/announcements/',
            {
                'title': '越界公告',
                'content': 'should fail',
                'status': 'draft',
                'audience': 'organization',
                'organization': root_a.id,
            },
            format='json',
        )
        assert create_response.status_code == 400

    def test_each_row_reports_whether_current_manager_can_operate_it(
        self,
        make_user,
    ):
        root, root_owner = _make_root(make_user, 'ROW')
        squad = _make_squad(root, root_owner, 'ROW1')
        squad_lead = make_user(email='row-squad-lead@test.com')
        TeamMember.objects.create(
            team=squad,
            user=squad_lead,
            role=TeamMember.Role.CO_LEAD,
        )
        Announcement.objects.create(
            title='根团队已发布公告',
            content='root',
            status=Announcement.Status.PUBLISHED,
            audience=Announcement.Audience.ORGANIZATION,
            organization=root,
            author=root_owner,
        )
        squad_draft = Announcement.objects.create(
            title='子队草稿',
            content='squad',
            status=Announcement.Status.DRAFT,
            audience=Announcement.Audience.TEAMS,
            organization=root,
            author=root_owner,
        )
        squad_draft.target_teams.add(squad)

        rows = {
            item['title']: item
            for item in _results(
                _client(squad_lead).get('/api/v1/notifications/announcements/')
            )
        }
        assert rows['根团队已发布公告']['can_manage'] is False
        assert rows['子队草稿']['can_manage'] is True

    def test_cannot_publish_to_another_root(self, make_user):
        root_a, owner_a = _make_root(make_user, 'CA')
        root_b, _ = _make_root(make_user, 'CB')
        response = _client(owner_a).post(
            '/api/v1/notifications/announcements/',
            {
                'title': '跨根公告',
                'content': 'blocked',
                'status': 'published',
                'audience': 'organization',
                'organization': root_b.id,
            },
            format='json',
        )
        assert response.status_code == 400
        assert not Announcement.objects.filter(title='跨根公告').exists()


@pytest.mark.django_db
def test_no_team_deployment_keeps_legacy_announcement_behaviour(
    make_user,
):
    teacher = make_user(
        email='legacy-announcement-teacher@test.com',
        global_role='teacher',
    )
    member = make_user(email='legacy-announcement-member@test.com')
    published = Announcement.objects.create(
        title='旧部署已发布',
        content='published',
        status=Announcement.Status.PUBLISHED,
        author=teacher,
    )
    draft = Announcement.objects.create(
        title='旧部署草稿',
        content='draft',
        status=Announcement.Status.DRAFT,
        author=teacher,
    )

    member_titles = {
        item['title']
        for item in _results(
            _client(member).get('/api/v1/notifications/announcements/')
        )
    }
    assert member_titles == {published.title}
    teacher_titles = {
        item['title']
        for item in _results(
            _client(teacher).get('/api/v1/notifications/announcements/')
        )
    }
    assert teacher_titles == {published.title, draft.title}


@pytest.mark.django_db
def test_audience_data_migration_maps_public_and_author_root(make_user):
    root, owner = _make_root(make_user, 'MIG')
    announcement = Announcement.objects.create(
        title='迁移前公开公告',
        content='legacy',
        author=owner,
    )
    Announcement.objects.filter(pk=announcement.pk).update(
        audience=Announcement.Audience.ORGANIZATION,
        organization=None,
        is_public=True,
    )

    migration = importlib.import_module(
        'apps.notifications.migrations.0008_announcement_audience'
    )
    migration.populate_announcement_audience(django_apps, None)

    announcement.refresh_from_db()
    assert announcement.audience == Announcement.Audience.PUBLIC
    assert announcement.organization_id == root.id


@pytest.mark.django_db
def test_list_can_manage_serialization_has_no_per_row_queries(
    make_user,
    django_assert_num_queries,
):
    root, owner = _make_root(make_user, 'QUERY')
    for index in range(8):
        Announcement.objects.create(
            title=f'公告{index}',
            content='fixed query count',
            status=Announcement.Status.PUBLISHED,
            audience=Announcement.Audience.ORGANIZATION,
            organization=root,
            author=owner,
        )
    rows = list(
        Announcement.objects.select_related(
            'author',
            'organization',
        ).prefetch_related(
            'target_teams',
            'target_projects',
        )
    )
    scope = announcement_management_scope(owner)
    serializer = AnnouncementSerializer(
        rows,
        many=True,
        context={
            'request': SimpleNamespace(user=owner),
            '_announcement_management_scope': scope,
        },
    )
    with django_assert_num_queries(0):
        data = serializer.data
    assert all(item['can_manage'] for item in data)
