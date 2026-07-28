"""文件中心根组织隔离回归测试。"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.common.team_models import Team, TeamMember
from apps.files.models import FileAsset
from apps.files.share_models import FileShareLink
from apps.projects.models import Project, ProjectMember


FILES_URL = '/api/v1/files/'
SHARES_URL = '/api/v1/files/shares/'


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


def make_root(name, code, owner):
    team = Team.objects.create(
        name=name,
        code=code,
        owner=owner,
        team_type=Team.TeamType.ORGANIZATION,
    )
    TeamMember.objects.create(
        team=team,
        user=owner,
        role=TeamMember.Role.OWNER,
    )
    return team


def make_project(name, code, leader, team=None):
    project = Project.objects.create(
        name=name,
        code=code,
        leader=leader,
        visibility=Project.Visibility.ORGANIZATION,
    )
    ProjectMember.objects.create(
        project=project,
        user=leader,
        role_in_project=ProjectMember.RoleInProject.LEADER,
    )
    if team is not None:
        project.teams.add(team)
    return project


def make_asset(project, uploader, name, level=FileAsset.Level.PUBLIC):
    return FileAsset.objects.create(
        project=project,
        uploader=uploader,
        name=name,
        file=f'dummy/{name}',
        level=level,
        size=16,
        content_type='application/pdf',
    )


@pytest.mark.django_db
def test_public_files_are_broad_only_inside_the_same_root_organization(
    api_client,
    make_user,
):
    owner_a = make_user(email='file-root-a-owner@test.com')
    owner_b = make_user(email='file-root-b-owner@test.com')
    viewer_a = make_user(email='file-root-a-viewer@test.com')
    root_a = make_root('File root A', 'FILE-ROOT-A', owner_a)
    root_b = make_root('File root B', 'FILE-ROOT-B', owner_b)
    TeamMember.objects.create(team=root_a, user=viewer_a)
    project_a = make_project('File project A', 'FILE-PROJECT-A', owner_a, root_a)
    project_b = make_project('File project B', 'FILE-PROJECT-B', owner_b, root_b)
    visible = make_asset(
        project_a,
        owner_a,
        'same-root-public-document.pdf',
    )
    hidden = make_asset(
        project_b,
        owner_b,
        'other-root-public-document.pdf',
    )

    api_client.force_authenticate(user=viewer_a)
    listed = api_client.get(FILES_URL)
    assert listed.status_code == 200
    listed_ids = {row['id'] for row in extract_results(listed)}
    assert visible.id in listed_ids
    assert hidden.id not in listed_ids

    assert api_client.get(f'{FILES_URL}{visible.id}/').status_code == 200
    assert api_client.get(f'{FILES_URL}{hidden.id}/').status_code == 404
    assert api_client.get(f'{FILES_URL}{hidden.id}/download/').status_code == 404
    assert api_client.get(f'{FILES_URL}{hidden.id}/versions/').status_code == 404

    search = api_client.get(
        '/api/v1/dashboard/search/?q=other-root-public-document'
        '&search_type=files'
    )
    assert search.status_code == 200
    assert extract_data(search)['files'] == []


@pytest.mark.django_db
def test_internal_file_still_requires_an_explicit_project_relationship(
    api_client,
    make_user,
):
    owner = make_user(email='internal-file-owner@test.com')
    same_root_member = make_user(email='internal-file-viewer@test.com')
    root = make_root('Internal file root', 'FILE-INTERNAL-ROOT', owner)
    TeamMember.objects.create(team=root, user=same_root_member)
    project = make_project(
        'Internal file project',
        'FILE-INTERNAL-PROJECT',
        owner,
        root,
    )
    internal = make_asset(
        project,
        owner,
        'project-members-only.pdf',
        level=FileAsset.Level.INTERNAL,
    )

    api_client.force_authenticate(user=same_root_member)
    assert api_client.get(f'{FILES_URL}{internal.id}/').status_code == 404

    ProjectMember.objects.create(
        project=project,
        user=same_root_member,
        role_in_project=ProjectMember.RoleInProject.PARTICIPANT,
    )
    assert api_client.get(f'{FILES_URL}{internal.id}/').status_code == 200


@pytest.mark.django_db
def test_share_management_honors_file_scope_but_token_access_stays_explicit(
    api_client,
    make_user,
):
    owner_a = make_user(email='share-root-a-owner@test.com')
    owner_b = make_user(email='share-root-b-owner@test.com')
    root_a = make_root('Share root A', 'FILE-SHARE-ROOT-A', owner_a)
    root_b = make_root('Share root B', 'FILE-SHARE-ROOT-B', owner_b)
    project_a = make_project(
        'Share project A',
        'FILE-SHARE-PROJECT-A',
        owner_a,
        root_a,
    )
    project_b = make_project(
        'Share project B',
        'FILE-SHARE-PROJECT-B',
        owner_b,
        root_b,
    )
    file_a = make_asset(project_a, owner_a, 'share-root-a.pdf')
    file_b = make_asset(project_b, owner_b, 'share-root-b.pdf')

    api_client.force_authenticate(user=owner_a)
    created = api_client.post(SHARES_URL, {'file': file_a.id}, format='json')
    assert created.status_code == 201, created.json()
    link = FileShareLink.objects.get(pk=extract_data(created)['id'])

    blocked = api_client.post(SHARES_URL, {'file': file_b.id}, format='json')
    assert blocked.status_code == 403, blocked.json()

    api_client.force_authenticate(user=None)
    access = api_client.get(f'{SHARES_URL}access/?token={link.token}')
    assert access.status_code == 200, access.json()
    assert extract_data(access)['file']['id'] == file_a.id


@pytest.mark.django_db
def test_teacher_file_writes_are_root_scoped_but_sys_admin_stays_platform_level(
    api_client,
    make_user,
):
    teacher_a = make_user(
        email='file-root-a-teacher@test.com',
        global_role='teacher',
    )
    owner_a = make_user(email='file-write-root-a-owner@test.com')
    owner_b = make_user(email='file-write-root-b-owner@test.com')
    root_a = make_root('File write root A', 'FILE-WRITE-ROOT-A', owner_a)
    root_b = make_root('File write root B', 'FILE-WRITE-ROOT-B', owner_b)
    TeamMember.objects.create(
        team=root_a,
        user=teacher_a,
        role=TeamMember.Role.TEACHER,
    )
    project_a = make_project(
        'File write project A',
        'FILE-WRITE-PROJECT-A',
        owner_a,
        root_a,
    )
    project_b = make_project(
        'File write project B',
        'FILE-WRITE-PROJECT-B',
        owner_b,
        root_b,
    )
    existing_a = make_asset(
        project_a,
        owner_a,
        'teacher-rebind-source.pdf',
    )

    api_client.force_authenticate(user=teacher_a)
    cross_root_upload = api_client.post(
        FILES_URL,
        {
            'project': project_b.id,
            'name': 'blocked-cross-root-upload.txt',
            'file': SimpleUploadedFile(
                'blocked-cross-root-upload.txt',
                b'blocked',
                content_type='text/plain',
            ),
            'level': FileAsset.Level.PUBLIC,
        },
        format='multipart',
    )
    assert cross_root_upload.status_code == 403, cross_root_upload.json()

    cross_root_rebind = api_client.patch(
        f'{FILES_URL}{existing_a.id}/',
        {'project': project_b.id},
        format='json',
    )
    assert cross_root_rebind.status_code == 403, cross_root_rebind.json()
    existing_a.refresh_from_db()
    assert existing_a.project_id == project_a.id

    same_root_upload = api_client.post(
        FILES_URL,
        {
            'project': project_a.id,
            'name': 'allowed-same-root-upload.txt',
            'file': SimpleUploadedFile(
                'allowed-same-root-upload.txt',
                b'allowed',
                content_type='text/plain',
            ),
            'level': FileAsset.Level.PUBLIC,
        },
        format='multipart',
    )
    assert same_root_upload.status_code == 201, same_root_upload.json()

    sys_admin = make_user(
        email='file-platform-admin@test.com',
        global_role='sys_admin',
        is_staff=True,
        is_superuser=True,
    )
    api_client.force_authenticate(user=sys_admin)
    platform_upload = api_client.post(
        FILES_URL,
        {
            'project': project_b.id,
            'name': 'platform-admin-upload.txt',
            'file': SimpleUploadedFile(
                'platform-admin-upload.txt',
                b'platform',
                content_type='text/plain',
            ),
            'level': FileAsset.Level.PUBLIC,
        },
        format='multipart',
    )
    assert platform_upload.status_code == 201, platform_upload.json()


@pytest.mark.django_db
def test_unscoped_public_files_keep_legacy_and_single_root_compatibility(
    api_client,
    make_user,
):
    legacy_user = make_user(email='legacy-file-viewer@test.com')
    legacy_project = make_project(
        'Legacy file project',
        'FILE-LEGACY-PROJECT',
        legacy_user,
    )
    legacy_file = make_asset(
        legacy_project,
        legacy_user,
        'legacy-public-file.pdf',
    )

    api_client.force_authenticate(user=legacy_user)
    assert api_client.get(f'{FILES_URL}{legacy_file.id}/').status_code == 200

    root_owner = make_user(email='single-root-owner@test.com')
    root_member = make_user(email='single-root-member@test.com')
    root = make_root('Single file root', 'FILE-SINGLE-ROOT', root_owner)
    TeamMember.objects.create(team=root, user=root_member)
    single_root_file = FileAsset.objects.create(
        project=None,
        uploader=root_owner,
        name='single-root-global-file.pdf',
        file='dummy/single-root-global-file.pdf',
        level=FileAsset.Level.PUBLIC,
    )

    api_client.force_authenticate(user=root_member)
    assert api_client.get(
        f'{FILES_URL}{single_root_file.id}/'
    ).status_code == 200

    second_root_owner = make_user(email='second-file-root-owner@test.com')
    make_root('Second file root', 'FILE-SECOND-ROOT', second_root_owner)
    assert api_client.get(
        f'{FILES_URL}{single_root_file.id}/'
    ).status_code == 404
