"""管理员演示数据备份包的创建、下载、校验与恢复测试。"""
import json
import zipfile
from io import StringIO
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command

from apps.common.backup_service import (
    DEMO_MARKER,
    DemoBackupError,
    create_demo_backup,
    restore_demo_backup,
    verify_demo_backup,
)
from apps.exports.custom_report_models import CustomReport
from apps.exports.scheduled_report_models import (
    ScheduledReport,
    ScheduledReportExecution,
)
from apps.files.models import FileAsset
from apps.intellectual_property.models import IntellectualPropertyApplication
from apps.notifications.models import Announcement
from apps.projects.models import Project


def extract_data(response):
    body = response.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.fixture(autouse=True)
def isolated_backup_root(settings, tmp_path):
    settings.DEMO_BACKUP_ROOT = str(tmp_path / 'demo-backups')


@pytest.mark.api
@pytest.mark.django_db
class TestBackup:
    def test_list_backups_for_admin(self, admin_client):
        response = admin_client.get('/api/v1/common/backup/')
        assert response.status_code == 200
        data = extract_data(response)
        assert data['backups'] == []
        assert data['total'] == 0
        assert data['mode'] == 'demo'

    def test_member_cannot_access_backup(self, member_client):
        assert member_client.get('/api/v1/common/backup/').status_code == 403
        assert member_client.post('/api/v1/common/backup/create/').status_code == 403

    def test_create_backup_writes_valid_zip(self, admin_client):
        response = admin_client.post('/api/v1/common/backup/create/', {}, format='json')
        assert response.status_code == 201, response.json()
        data = extract_data(response)
        assert data['status'] == 'ready'
        assert data['backup_id'].startswith('demo-')
        manifest = verify_demo_backup(data['backup_id'])
        assert manifest['schema'] == 'team-management-demo-backup-v2'
        assert manifest['restore_strategy'] == 'snapshot_overlay_v2'

    def test_package_contains_manifest_snapshot_and_readme(self, admin_client):
        backup = create_demo_backup(created_by=admin_client.user)
        root = admin_client.get('/api/v1/common/backup/').json()['data']
        assert root['total'] == 1
        # 通过下载接口读取内容，避免依赖服务的内部路径。
        response = admin_client.get(
            f'/api/v1/common/backup/{backup["backup_id"]}/download/'
        )
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/zip'
        assert (
            response['Content-Disposition']
            == f'attachment; filename="{backup["backup_id"]}.zip"'
        )
        content = b''.join(response.streaming_content)
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            assert 'manifest.json' in names
            assert 'data/demo_snapshot.json' in names
            assert 'README.txt' in names
            snapshot = archive.read('data/demo_snapshot.json').decode('utf-8')
            manifest = archive.read('manifest.json').decode('utf-8')
            assert '"scheduled_reports"' in snapshot
            assert '"scheduled_report_executions"' in snapshot
            assert '"finance_incomes"' in snapshot
            assert '"finance_receipts"' in snapshot
            assert '"project_membership_events"' in snapshot
            assert '"project_stage_logs"' in snapshot
            assert '"task_collaborators"' in snapshot
            assert '"user_lifecycle_events"' in snapshot
            assert '"teams"' in snapshot
            assert '"team_members"' in snapshot
            assert '"member_skills"' in snapshot
            assert '"flexible_work_schedules"' in snapshot
            assert '"member_rankings"' in snapshot
            assert '"ranking_objections"' in snapshot
            assert '"sensitive_data"' in snapshot
            assert '"sensitive_access_requests"' in snapshot
            assert '"notifications"' in snapshot
            assert '"announcements"' in snapshot
            assert '"operation_logs"' in snapshot
            assert '"encrypted_content"' not in snapshot
            assert '"encrypted_file_path"' not in snapshot
            assert '"ip_applications"' in snapshot
            assert '"ip_return_records"' in snapshot
            assert '"ip_objections"' in snapshot
            assert '"portal_publications"' in snapshot
            assert '"imports"' in snapshot
            assert 'seed_demo_data --clean --force + snapshot overlay' in manifest

    def test_current_team_demo_projects_are_included(self, admin_client):
        Project.objects.create(
            name='完整团队演示项目',
            code='TEAM-DEMO-TEST',
            leader=admin_client.user,
        )
        backup = create_demo_backup(created_by=admin_client.user)
        response = admin_client.get(
            f'/api/v1/common/backup/{backup["backup_id"]}/download/'
        )
        content = b''.join(response.streaming_content)
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(content)) as archive:
            snapshot = json.loads(archive.read('data/demo_snapshot.json'))
        assert any(
            project['code'] == 'TEAM-DEMO-TEST'
            for project in snapshot['projects']
        )

    def test_ip_certificate_reference_and_physical_pdf_enter_backup(
        self,
        admin_client,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path / 'media'
        project = Project.objects.create(
            name='证书备份演示项目',
            code='TEAM-DEMO-IP-BACKUP',
            leader=admin_client.user,
        )
        certificate_content = b'%PDF-1.4\n% demo certificate\n%%EOF'
        certificate = FileAsset(
            project=project,
            name='IP-TEAM-DEMO-BACKUP 最终授权登记证书.pdf',
            level=FileAsset.Level.INTERNAL,
            size=len(certificate_content),
            content_type='application/pdf',
            uploader=admin_client.user,
        )
        certificate.file.save(
            'seed_demo_data/ip-backup-certificate.pdf',
            ContentFile(certificate_content),
            save=True,
        )
        IntellectualPropertyApplication.objects.create(
            title='证书备份演示成果',
            application_code='IP-TEAM-DEMO-BACKUP',
            related_project=project,
            status=IntellectualPropertyApplication.Status.AUTHORIZED,
            main_writer=admin_client.user,
            project_reviewer=admin_client.user,
            final_certificate_file=certificate,
            created_by=admin_client.user,
        )

        backup = create_demo_backup(created_by=admin_client.user)
        response = admin_client.get(
            f'/api/v1/common/backup/{backup["backup_id"]}/download/'
        )
        content = b''.join(response.streaming_content)
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            snapshot = json.loads(archive.read('data/demo_snapshot.json'))
            certificate_entry = (
                f'media/assets/{certificate.pk}_'
                f'{Path(certificate.file.name).name}'
            )
            assert certificate_entry in names
            assert archive.read(certificate_entry) == certificate_content

        application = next(
            item for item in snapshot['ip_applications']
            if item['application_code'] == 'IP-TEAM-DEMO-BACKUP'
        )
        assert application['final_certificate_file__name'] == certificate.name

    def test_only_marker_reports_and_files_enter_demo_backup(
        self,
        admin_client,
        make_user,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path / 'media'
        demo_user = make_user(
            email='admin@demo.com',
            global_role='sys_admin',
            is_staff=True,
            is_superuser=True,
        )
        marker_report = CustomReport.objects.create(
            name=f'{DEMO_MARKER}演示项目日报',
            report_type=CustomReport.ReportType.SUMMARY,
            created_by=demo_user,
        )
        marker_schedule = ScheduledReport.objects.create(
            report=marker_report,
            created_by=demo_user,
            file_format=ScheduledReport.FileFormat.XLSX,
        )
        marker_execution = ScheduledReportExecution(
            schedule=marker_schedule,
            status=ScheduledReport.RunStatus.SUCCESS,
            file_name='demo-marker.xlsx',
            file_format=ScheduledReport.FileFormat.XLSX,
            file_size=19,
            generated_by=demo_user,
        )
        marker_execution.file.save(
            'demo-marker.xlsx',
            ContentFile(b'demo report content'),
            save=True,
        )

        real_report = CustomReport.objects.create(
            name='同一演示账号创建的真实报表',
            report_type=CustomReport.ReportType.SUMMARY,
            created_by=demo_user,
        )
        real_schedule = ScheduledReport.objects.create(
            report=real_report,
            created_by=demo_user,
            file_format=ScheduledReport.FileFormat.XLSX,
        )
        real_execution = ScheduledReportExecution(
            schedule=real_schedule,
            status=ScheduledReport.RunStatus.SUCCESS,
            file_name='real-report.xlsx',
            file_format=ScheduledReport.FileFormat.XLSX,
            file_size=19,
            generated_by=demo_user,
        )
        real_execution.file.save(
            'real-report.xlsx',
            ContentFile(b'real report content'),
            save=True,
        )
        Announcement.objects.create(
            title=f'{DEMO_MARKER}演示公告',
            content='演示内容',
            status=Announcement.Status.PUBLISHED,
            author=demo_user,
        )
        Announcement.objects.create(
            title='同一演示账号创建的真实公告',
            content='真实内容',
            status=Announcement.Status.PUBLISHED,
            author=demo_user,
        )

        backup = create_demo_backup(created_by=admin_client.user)
        response = admin_client.get(
            f'/api/v1/common/backup/{backup["backup_id"]}/download/'
        )
        content = b''.join(response.streaming_content)
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            snapshot = json.loads(archive.read('data/demo_snapshot.json'))

        assert [report['name'] for report in snapshot['custom_reports']] == [
            marker_report.name
        ]
        assert len(snapshot['scheduled_reports']) == 1
        assert len(snapshot['scheduled_report_executions']) == 1
        assert [item['title'] for item in snapshot['announcements']] == [
            f'{DEMO_MARKER}演示公告'
        ]
        assert (
            f'media/scheduled_reports/{marker_execution.pk}_demo-marker.xlsx'
            in names
        )
        assert not any(
            name.startswith(
                f'media/scheduled_reports/{real_execution.pk}_'
            )
            for name in names
        )

    def test_restore_requires_explicit_confirmation(self, admin_client):
        backup = create_demo_backup(created_by=admin_client.user)
        response = admin_client.post(
            f'/api/v1/common/backup/{backup["backup_id"]}/restore/',
            {},
            format='json',
        )
        assert response.status_code == 400

    def test_restore_verifies_creates_rollback_and_runs_seed(
        self,
        admin_client,
        monkeypatch,
    ):
        backup = create_demo_backup(created_by=admin_client.user)
        calls = []
        monkeypatch.setattr(
            'apps.common.backup_service.call_command',
            lambda *args, **kwargs: calls.append((args, kwargs)),
        )
        response = admin_client.post(
            f'/api/v1/common/backup/{backup["backup_id"]}/restore/',
            {'confirmation': 'RESTORE_DEMO'},
            format='json',
        )
        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert data['status'] == 'restored'
        assert data['rollback_backup_id'] != backup['backup_id']
        assert data['requires_relogin'] is True
        assert calls[0][0] == ('seed_demo_data',)

    def test_restore_uses_selected_snapshot_and_restores_attachment(
        self,
        admin_client,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path / 'media'
        project = Project.objects.create(
            name='包特定恢复项目',
            code='TEAM-DEMO-BACKUP-STATE',
            leader=admin_client.user,
            intro='备份 A 中的项目说明',
        )
        asset = FileAsset(
            project=project,
            name='包特定附件.txt',
            level=FileAsset.Level.INTERNAL,
            size=len(b'backup-a-content'),
            content_type='text/plain',
            uploader=admin_client.user,
        )
        asset.file.save(
            'seed_demo_data/package-specific.txt',
            ContentFile(b'backup-a-content'),
            save=True,
        )
        backup_a = create_demo_backup(created_by=admin_client.user)

        project.intro = '备份 B 中的项目说明'
        project.save(update_fields=['intro'])
        Path(asset.file.path).write_bytes(b'backup-b-content')
        asset.size = len(b'backup-b-content')
        asset.save(update_fields=['size'])
        create_demo_backup(created_by=admin_client.user)

        result = restore_demo_backup(
            backup_a['backup_id'],
            requested_by=admin_client.user,
        )

        restored_project = Project.objects.get(code='TEAM-DEMO-BACKUP-STATE')
        restored_asset = FileAsset.objects.get(
            project=restored_project,
            name='包特定附件.txt',
        )
        assert restored_project.intro == '备份 A 中的项目说明'
        assert Path(restored_asset.file.path).read_bytes() == b'backup-a-content'
        assert result['strategy'] == 'snapshot_overlay_v2'
        assert result['restored_media_files'] >= 1

    def test_restore_failure_uses_pre_restore_rollback_package(
        self,
        admin_client,
        monkeypatch,
    ):
        project = Project.objects.create(
            name='自动回滚项目',
            code='TEAM-DEMO-ROLLBACK-STATE',
            leader=admin_client.user,
            intro='恢复前状态',
        )
        target = create_demo_backup(created_by=admin_client.user)
        restored_packages = []

        def fake_restore(path, manifest):
            restored_packages.append(path.stem)
            if path.stem == target['backup_id']:
                Project.objects.filter(pk=project.pk).update(intro='中途损坏状态')
                raise RuntimeError('模拟恢复失败')
            Project.objects.filter(pk=project.pk).update(intro='恢复前状态')
            return {'records': {}, 'media_files': 0}

        monkeypatch.setattr(
            'apps.common.backup_service._restore_verified_package',
            fake_restore,
        )

        with pytest.raises(DemoBackupError, match='已自动回滚'):
            restore_demo_backup(target['backup_id'], requested_by=admin_client.user)

        project.refresh_from_db()
        assert project.intro == '恢复前状态'
        assert len(restored_packages) == 2
        assert restored_packages[0] == target['backup_id']
        assert restored_packages[1] != target['backup_id']

    def test_full_demo_seed_backup_round_trip(
        self,
        admin_client,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path / 'media'
        call_command(
            'seed_demo_data',
            clean=True,
            force=True,
            stdout=StringIO(),
        )
        project = Project.objects.filter(code__startswith='TEAM-DEMO-').order_by('code').first()
        asset = FileAsset.objects.filter(project=project).exclude(file='').first()
        original_content = Path(asset.file.path).read_bytes()
        backup_content = original_content + b'\nselected-backup-state'
        project.intro = '完整备份包 A 的项目状态'
        project.save(update_fields=['intro'])
        Path(asset.file.path).write_bytes(backup_content)
        asset.size = len(backup_content)
        asset.save(update_fields=['size'])
        selected = create_demo_backup(created_by=admin_client.user)

        project.intro = '恢复前的后续状态 B'
        project.save(update_fields=['intro'])
        Path(asset.file.path).write_bytes(b'later-state-b')

        result = restore_demo_backup(selected['backup_id'], requested_by=admin_client.user)

        restored_project = Project.objects.get(code=project.code)
        restored_asset = FileAsset.objects.get(project=restored_project, name=asset.name)
        assert restored_project.intro == '完整备份包 A 的项目状态'
        assert Path(restored_asset.file.path).read_bytes() == backup_content
        assert Project.objects.filter(code__startswith='TEAM-DEMO-').count() == 24
        assert result['restored_records']['updated'] > 0
        assert result['restored_media_files'] > 100

    def test_missing_backup_cannot_restore(self, admin_client):
        response = admin_client.post(
            '/api/v1/common/backup/demo-20000101-000000/restore/',
            {'confirmation': 'RESTORE_DEMO'},
            format='json',
        )
        assert response.status_code == 400

    def test_unauthenticated_access_blocked(self, api_client):
        assert api_client.get('/api/v1/common/backup/').status_code in (401, 403)
        assert api_client.post('/api/v1/common/backup/create/').status_code in (401, 403)
