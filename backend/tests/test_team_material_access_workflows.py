"""Regression coverage for team search, exact scopes and material workflows."""

from datetime import timedelta
from io import BytesIO
import json
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import (
    Competition,
    CompetitionEvent,
    CompetitionParticipant,
)
from apps.files.models import FileAsset
from apps.imports.models import ImportTask
from apps.sensitive.models import (
    SensitiveData,
    SensitiveDataGrant,
    SensitiveGrantAccessLog,
)


def response_data(response):
    payload = response.json()
    return payload.get('data', payload) if isinstance(payload, dict) else payload


def response_results(response):
    payload = response_data(response)
    return payload.get('results', payload) if isinstance(payload, dict) else payload


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_root(owner, *, name='总团队', code='TEAM-MATERIAL-ROOT'):
    root = Team.objects.create(name=name, code=code, owner=owner)
    TeamMember.objects.create(
        team=root,
        user=owner,
        role=TeamMember.Role.OWNER,
    )
    return root


def make_zip(manifest, files):
    payload = BytesIO()
    with zipfile.ZipFile(payload, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            'manifest.json',
            json.dumps(manifest, ensure_ascii=False).encode('utf-8'),
        )
        for path, content in files.items():
            archive.writestr(path, content)
    return payload.getvalue()


@pytest.mark.api
@pytest.mark.django_db
def test_total_team_candidate_picker_combines_pinyin_and_structured_filters(make_user):
    owner = make_user(email='candidate-owner@test.com', name='负责人')
    candidate = make_user(
        email='candidate-liu@test.com',
        name='刘宇成',
        school='示例大学',
        grade='大三',
        major='软件工程',
    )
    existing = make_user(email='candidate-existing@test.com', name='现有成员')
    outsider = make_user(email='candidate-outsider@test.com', name='外部组织成员')
    view_only_teacher = make_user(email='candidate-view-teacher@test.com', name='查看老师')
    root = make_root(owner)
    squad = Team.objects.create(
        name='项目参赛小组',
        code='TEAM-MATERIAL-SQUAD',
        owner=owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(
        team=root,
        user=candidate,
        role=TeamMember.Role.MEMBER,
    )
    TeamMember.objects.create(
        team=root,
        user=view_only_teacher,
        role=TeamMember.Role.TEACHER,
    )
    TeamMember.objects.create(team=squad, user=existing)
    other_root = make_root(
        outsider,
        name='其他总团队',
        code='TEAM-MATERIAL-OTHER-ROOT',
    )
    assert other_root.id != root.id

    response = client_for(owner).get(
        f'/api/v1/teams/{squad.id}/candidates/',
        {
            'search': 'LYC',
            'school': '示例',
            'team_role': TeamMember.Role.MEMBER,
            'membership_status': 'active',
        },
    )

    assert response.status_code == 200, response.json()
    rows = response_data(response)
    assert [row['id'] for row in rows] == [candidate.id]
    assert rows[0]['school'] == '示例大学'
    assert existing.id not in {row['id'] for row in rows}
    assert outsider.id not in {row['id'] for row in rows}

    denied = client_for(view_only_teacher).get(
        f'/api/v1/teams/{root.id}/candidates/'
    )
    assert denied.status_code == 403, denied.json()


@pytest.mark.api
@pytest.mark.django_db
def test_member_detail_lists_exact_competition_entry_role_status_and_work(make_user, make_project):
    owner = make_user(email='detail-owner@test.com', name='负责人')
    member = make_user(email='detail-member@test.com', name='参赛成员')
    root = make_root(owner, code='MEMBER-DETAIL-ROOT')
    TeamMember.objects.create(team=root, user=member)
    project = make_project(
        leader=owner,
        name='安全项目',
        code='MEMBER-DETAIL-PROJECT',
    )
    project.teams.add(root)
    event = CompetitionEvent.objects.create(
        name='安全创新赛',
        edition='2026',
        organizer='示例主办方',
    )
    entry = Competition.objects.create(
        event=event,
        project=project,
        name=event.name,
        organizer=event.organizer,
        entry_name='安全项目 A 队',
    )
    participation = CompetitionParticipant.objects.create(
        competition=entry,
        user=member,
        role=CompetitionParticipant.Role.MEMBER,
        participation_status=CompetitionParticipant.ParticipationStatus.CONFIRMED,
        responsibility='现场答辩与材料整理',
    )

    response = client_for(owner).get(f'/api/v1/members/{member.id}/')

    assert response.status_code == 200, response.json()
    records = response_data(response)['competition_participations']
    assert records == [{
        'participant_id': participation.id,
        'competition_id': entry.id,
        'competition_name': event.name,
        'event_id': event.id,
        'event_name': event.name,
        'event_edition': '2026',
        'event_organizer': '示例主办方',
        'project_id': project.id,
        'project_name': '安全项目',
        'project_code': 'MEMBER-DETAIL-PROJECT',
        'entry_name': '安全项目 A 队',
        'role': CompetitionParticipant.Role.MEMBER,
        'role_display': participation.get_role_display(),
        'participation_status': CompetitionParticipant.ParticipationStatus.CONFIRMED,
        'participation_status_display': participation.get_participation_status_display(),
        'responsibility': '现场答辩与材料整理',
        'joined_at': records[0]['joined_at'],
    }]


@pytest.mark.api
@pytest.mark.django_db
def test_internal_files_enforce_exact_team_and_competition_rosters(
    settings,
    tmp_path,
    make_user,
    make_project,
):
    settings.MEDIA_ROOT = tmp_path
    owner = make_user(email='scope-owner@test.com')
    participant = make_user(email='scope-participant@test.com')
    same_root_bystander = make_user(email='scope-bystander@test.com')
    squad_member = make_user(email='scope-squad-member@test.com')
    view_only_teacher = make_user(email='scope-view-teacher@test.com')
    root = make_root(owner, code='EXACT-FILE-ROOT')
    squad = Team.objects.create(
        name='资料小团队',
        code='EXACT-FILE-SQUAD',
        owner=owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    for user in (participant, same_root_bystander):
        TeamMember.objects.create(team=root, user=user)
    TeamMember.objects.create(team=squad, user=squad_member)
    TeamMember.objects.create(
        team=squad,
        user=view_only_teacher,
        role=TeamMember.Role.TEACHER,
    )
    project = make_project(
        leader=owner,
        code='EXACT-FILE-PROJECT',
    )
    project.teams.add(root)
    event = CompetitionEvent.objects.create(name='资料边界赛', edition='2026')
    entry = Competition.objects.create(
        event=event,
        project=project,
        name=event.name,
        entry_name='项目一队',
    )
    CompetitionParticipant.objects.create(
        competition=entry,
        user=participant,
        participation_status=CompetitionParticipant.ParticipationStatus.CONFIRMED,
    )
    competition_file = FileAsset.objects.create(
        project=project,
        competition_entry=entry,
        name='仅本参赛队.pdf',
        file=SimpleUploadedFile('competition.pdf', b'competition'),
        level=FileAsset.Level.INTERNAL,
        uploader=owner,
    )
    team_file = FileAsset.objects.create(
        project=project,
        team=squad,
        name='仅资料小团队.pdf',
        file=SimpleUploadedFile('team.pdf', b'team'),
        level=FileAsset.Level.INTERNAL,
        uploader=owner,
    )

    assert client_for(participant).get(
        f'/api/v1/files/{competition_file.id}/'
    ).status_code == 200
    assert client_for(same_root_bystander).get(
        f'/api/v1/files/{competition_file.id}/'
    ).status_code == 404
    assert client_for(squad_member).get(
        f'/api/v1/files/{team_file.id}/'
    ).status_code == 200
    assert client_for(same_root_bystander).get(
        f'/api/v1/files/{team_file.id}/'
    ).status_code == 404
    read_only_detail = client_for(view_only_teacher).get(
        f'/api/v1/files/{team_file.id}/'
    )
    assert read_only_detail.status_code == 200
    assert response_data(read_only_detail)['can_manage'] is False

    denied_upload = client_for(view_only_teacher).post(
        '/api/v1/files/',
        {
            'project': project.id,
            'team': squad.id,
            'name': '只读老师不可上传.txt',
            'file': SimpleUploadedFile('readonly.txt', b'readonly'),
            'level': FileAsset.Level.INTERNAL,
        },
        format='multipart',
    )
    assert denied_upload.status_code == 403, denied_upload.json()


@pytest.mark.api
@pytest.mark.django_db
def test_exact_sensitive_grant_supports_view_download_expiry_and_audit(
    settings,
    tmp_path,
    make_user,
):
    settings.MEDIA_ROOT = tmp_path
    owner = make_user(email='grant-owner@test.com', name='资料负责人')
    grantee = make_user(email='grant-user@test.com', name='材料整理同学')
    unrelated = make_user(email='grant-unrelated@test.com', name='无关成员')
    root = make_root(owner, code='SENSITIVE-GRANT-ROOT')
    TeamMember.objects.create(team=root, user=grantee)
    TeamMember.objects.create(team=root, user=unrelated)
    attachment = FileAsset.objects.create(
        team=root,
        name='授权材料.pdf',
        file=SimpleUploadedFile('grant.pdf', b'grant-document'),
        level=FileAsset.Level.SENSITIVE,
        uploader=owner,
    )
    sensitive = SensitiveData.objects.create(
        data_type=SensitiveData.DataType.OTHER,
        title='专利提交授权材料',
        team=root,
        subject_user=owner,
        uploader=owner,
        file_attachment=attachment,
    )
    sensitive.encrypt_content('仅授权人可见的明文')
    expires_at = timezone.now() + timedelta(hours=2)

    granted = client_for(owner).post(
        f'/api/v1/sensitive/data/{sensitive.id}/grants/',
        {
            'granted_to': grantee.id,
            'can_view': True,
            'can_download': True,
            'purpose': '整理专利申请材料并提交',
            'expires_at': expires_at.isoformat(),
        },
        format='json',
    )
    assert granted.status_code == 201, granted.json()
    grant_id = response_data(granted)['id']

    catalogue = client_for(grantee).get('/api/v1/sensitive/data/')
    assert sensitive.id in {row['id'] for row in response_results(catalogue)}
    # 同小团队成员可看到“存在这份资料”的脱敏目录，但没有单份授权时
    # 不能查看明文或下载附件。
    assert client_for(unrelated).get(
        f'/api/v1/sensitive/data/{sensitive.id}/'
    ).status_code == 200
    denied_view = client_for(unrelated).post(
        f'/api/v1/sensitive/data/{sensitive.id}/view/',
        {'grant_id': grant_id},
        format='json',
    )
    assert denied_view.status_code == 403, denied_view.json()

    viewed = client_for(grantee).post(
        f'/api/v1/sensitive/data/{sensitive.id}/view/',
        {'grant_id': grant_id},
        format='json',
    )
    assert viewed.status_code == 200, viewed.json()
    assert response_data(viewed)['plaintext'] == '仅授权人可见的明文'

    downloaded = client_for(grantee).get(
        f'/api/v1/sensitive/data/{sensitive.id}/download-by-grant/',
        {'grant_id': grant_id},
    )
    assert downloaded.status_code == 200
    assert b'grant-document' in b''.join(downloaded.streaming_content)
    assert SensitiveGrantAccessLog.objects.filter(
        grant_id=grant_id,
        accessor=grantee,
        action=SensitiveGrantAccessLog.Action.VIEW,
        is_success=True,
    ).exists()
    assert SensitiveGrantAccessLog.objects.filter(
        grant_id=grant_id,
        accessor=grantee,
        action=SensitiveGrantAccessLog.Action.DOWNLOAD,
        is_success=True,
    ).exists()

    grant = SensitiveDataGrant.objects.get(pk=grant_id)
    grant.expires_at = timezone.now() - timedelta(seconds=1)
    grant.save(update_fields=['expires_at'])
    expired = client_for(grantee).post(
        f'/api/v1/sensitive/data/{sensitive.id}/view/',
        {'grant_id': grant_id},
        format='json',
    )
    assert expired.status_code in {403, 404}


@pytest.mark.api
@pytest.mark.django_db
def test_direct_sensitive_attachment_upload_is_closed_and_rejects_scripts(
    settings,
    tmp_path,
    make_user,
):
    settings.MEDIA_ROOT = tmp_path
    member = make_user(email='direct-sensitive@test.com')
    root = make_root(member, code='DIRECT-SENSITIVE-ROOT')
    client = client_for(member)

    created = client.post(
        '/api/v1/sensitive/data/',
        {
            'data_type': SensitiveData.DataType.OTHER,
            'title': '直接上传的内部计划书',
            'team': root.id,
            'attachment_upload': SimpleUploadedFile(
                'plan.pdf', b'%PDF-1.4 direct', content_type='application/pdf'
            ),
        },
        format='multipart',
    )
    assert created.status_code == 201, created.json()
    sensitive = SensitiveData.objects.get(pk=response_data(created)['id'])
    assert sensitive.file_attachment.level == FileAsset.Level.SENSITIVE
    assert sensitive.file_attachment.team_id == root.id

    rejected = client.post(
        '/api/v1/sensitive/data/',
        {
            'data_type': SensitiveData.DataType.OTHER,
            'title': '危险脚本',
            'team': root.id,
            'attachment_upload': SimpleUploadedFile('payload.ps1', b'Write-Host bad'),
        },
        format='multipart',
    )
    assert rejected.status_code == 400, rejected.json()


@pytest.mark.api
@pytest.mark.django_db
def test_zip_manifest_import_separates_materials_and_rolls_back(
    settings,
    tmp_path,
    make_user,
    make_project,
):
    settings.MEDIA_ROOT = tmp_path
    owner = make_user(email='archive-owner@test.com')
    subject = make_user(email='archive-subject@test.com')
    root = make_root(owner, code='ARCHIVE-ROOT')
    squad = Team.objects.create(
        name='资料导入小团队',
        code='ARCHIVE-SQUAD',
        owner=owner,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    TeamMember.objects.create(team=squad, user=subject)
    project = make_project(leader=owner, code='ARCHIVE-PROJECT')
    project.teams.add(root)
    manifest = {
        'version': 1,
        'items': [
            {
                'path': 'ordinary/plan.pdf',
                'name': '项目计划书.pdf',
                'project_code': project.code,
                'team_code': squad.code,
                'level': 'internal',
                'visibility': 'team',
            },
            {
                'path': 'sensitive/id-card.pdf',
                'title': '成员身份证附件',
                'project_code': project.code,
                'team_code': squad.code,
                'level': 'sensitive',
                'visibility': 'team',
                'data_type': 'id_card',
                'subject_email': subject.email,
            },
        ],
    }
    archive_bytes = make_zip(
        manifest,
        {
            'ordinary/plan.pdf': b'ordinary-plan',
            'sensitive/id-card.pdf': b'sensitive-id-card',
        },
    )
    client = client_for(owner)
    preview = client.post(
        '/api/v1/imports/tasks/preview-materials/',
        {
            'team': squad.id,
            'file': SimpleUploadedFile(
                'materials.zip', archive_bytes, content_type='application/zip'
            ),
        },
        format='multipart',
    )
    assert preview.status_code == 200, preview.json()
    preview_data = response_data(preview)
    assert preview_data['valid_rows'] == 2
    assert preview_data['error_rows'] == 0

    task_id = preview_data['task_id']
    confirmed = client.post(
        f'/api/v1/imports/tasks/{task_id}/confirm/',
        {},
        format='json',
    )
    assert confirmed.status_code == 200, confirmed.json()
    assert response_data(confirmed)['ordinary_count'] == 1
    assert response_data(confirmed)['sensitive_count'] == 1
    task = ImportTask.objects.get(pk=task_id)
    created_file_ids = task.snapshot['file_ids']
    assert FileAsset.objects.filter(pk__in=created_file_ids).count() == 2
    assert SensitiveData.objects.filter(
        pk__in=task.snapshot['sensitive_data_ids'],
        subject_user=subject,
        team=squad,
    ).count() == 1

    rolled_back = client.post(f'/api/v1/imports/tasks/{task_id}/rollback/')
    assert rolled_back.status_code == 200, rolled_back.json()
    assert not FileAsset.all_objects.filter(pk__in=created_file_ids).exists()
    task.refresh_from_db()
    assert task.status == ImportTask.Status.ROLLED_BACK


@pytest.mark.api
@pytest.mark.django_db
def test_zip_material_preview_rejects_traversal_and_leaves_no_task(
    settings,
    tmp_path,
    make_user,
):
    settings.MEDIA_ROOT = tmp_path
    owner = make_user(email='archive-security-owner@test.com')
    root = make_root(owner, code='ARCHIVE-SECURITY-ROOT')
    archive_bytes = make_zip(
        {
            'version': 1,
            'items': [{'path': '../escape.pdf', 'project_code': 'MISSING'}],
        },
        {'../escape.pdf': b'escape'},
    )

    response = client_for(owner).post(
        '/api/v1/imports/tasks/preview-materials/',
        {
            'team': root.id,
            'file': SimpleUploadedFile('unsafe.zip', archive_bytes),
        },
        format='multipart',
    )

    assert response.status_code == 400, response.json()
    assert not ImportTask.objects.filter(module=ImportTask.Module.MATERIALS).exists()
    staged_dir = tmp_path / 'imports' / 'materials'
    assert not staged_dir.exists() or not list(staged_dir.iterdir())
