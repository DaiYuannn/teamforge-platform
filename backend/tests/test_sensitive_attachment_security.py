"""敏感附件、下载审计与公开分享边界测试。"""

from datetime import timedelta
import json

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import OperationLog
from apps.files.models import FileAsset, FileVersion
from apps.files.share_models import FileShareLink
from apps.projects.models import ProjectMember
from apps.sensitive.models import SensitiveAccessRequest, SensitiveData


def extract_data(response):
    payload = response.json()
    if isinstance(payload, dict) and 'code' in payload:
        return payload.get('data', payload)
    return payload


def extract_results(response):
    payload = extract_data(response)
    if isinstance(payload, dict) and 'results' in payload:
        return payload['results']
    return payload


def client_for(user):
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    client.user = user
    return client


@pytest.fixture
def stored_attachment(settings, tmp_path, make_project, make_user):
    settings.MEDIA_ROOT = tmp_path
    return FileAsset.objects.create(
        project=make_project(),
        name='identity-proof.pdf',
        file=SimpleUploadedFile(
            'identity-proof.pdf',
            b'%PDF-1.4\none-line-sensitive-demo\n',
            content_type='application/pdf',
        ),
        level=FileAsset.Level.PUBLIC,
        uploader=make_user(email='attachment-owner@test.com'),
        size=36,
        content_type='application/pdf',
    )


@pytest.mark.api
@pytest.mark.django_db
class TestSensitiveCatalogue:
    def test_internal_member_sees_other_users_masked_metadata(
        self,
        member_client,
        make_sensitive_data,
    ):
        sensitive = make_sensitive_data(title='他人证件资料')

        response = member_client.get('/api/v1/sensitive/data/')

        assert response.status_code == 200, response.json()
        row = next(item for item in extract_results(response) if item['id'] == sensitive.id)
        assert row['title'] == '他人证件资料'
        assert row['owner_name']
        assert row['masked_value'] != '测试敏感明文内容'
        assert 'encrypted_content' not in row
        assert 'plaintext' not in row

        detail = member_client.get(f'/api/v1/sensitive/data/{sensitive.id}/')
        assert detail.status_code == 200
        assert extract_data(detail)['masked_value'] != '测试敏感明文内容'

    def test_external_collaborator_cannot_browse_team_sensitive_catalogue(
        self,
        make_user,
    ):
        external = make_user(
            email='external-sensitive@test.com',
            membership_status='external',
        )
        response = client_for(external).get('/api/v1/sensitive/data/')
        assert response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
class TestSensitiveAttachmentProtection:
    def test_linking_attachment_marks_sensitive_and_revokes_shares(
        self,
        stored_attachment,
        make_user,
    ):
        link = FileShareLink.objects.create(
            file=stored_attachment,
            created_by=make_user(email='share-owner@test.com'),
            token=FileShareLink.generate_token(),
        )

        SensitiveData.objects.create(
            title='附件保护测试',
            data_type=SensitiveData.DataType.ID_CARD,
            file_attachment=stored_attachment,
        )

        stored_attachment.refresh_from_db()
        link.refresh_from_db()
        assert stored_attachment.level == FileAsset.Level.SENSITIVE
        assert link.is_active is False

        stored_attachment.level = FileAsset.Level.PUBLIC
        stored_attachment.save(update_fields=['level'])
        stored_attachment.refresh_from_db()
        assert stored_attachment.level == FileAsset.Level.SENSITIVE

    def test_model_rejects_new_sensitive_share(
        self,
        stored_attachment,
        make_user,
    ):
        stored_attachment.level = FileAsset.Level.SENSITIVE
        stored_attachment.save(update_fields=['level'])

        with pytest.raises(ValidationError):
            FileShareLink.objects.create(
                file=stored_attachment,
                created_by=make_user(email='blocked-share@test.com'),
                token=FileShareLink.generate_token(),
            )

    def test_sensitive_file_serializer_omits_every_signed_file_url(
        self,
        admin_client,
        stored_attachment,
    ):
        stored_attachment.level = FileAsset.Level.SENSITIVE
        stored_attachment.save(update_fields=['level'])
        FileVersion.objects.create(
            file_asset=stored_attachment,
            file=stored_attachment.file,
            version=1,
            uploader=admin_client.user,
        )

        detail = admin_client.get(f'/api/v1/files/{stored_attachment.id}/')
        assert detail.status_code == 200
        data = extract_data(detail)
        assert 'file' not in data
        assert 'file_url' not in data

        versions = admin_client.get(
            f'/api/v1/files/{stored_attachment.id}/versions/'
        )
        assert versions.status_code == 200
        assert all('file' not in row for row in extract_data(versions))


@pytest.mark.api
@pytest.mark.django_db
class TestSensitiveAttachmentDownloads:
    def test_regular_and_version_get_downloads_are_explicitly_audited(
        self,
        member_client,
        stored_attachment,
    ):
        version = FileVersion.objects.create(
            file_asset=stored_attachment,
            file=stored_attachment.file,
            version=1,
            uploader=stored_attachment.uploader,
        )

        direct_response = member_client.get(
            f'/api/v1/files/{stored_attachment.id}/download/'
        )
        assert direct_response.status_code == 200
        b''.join(direct_response.streaming_content)

        version_response = member_client.get(
            f'/api/v1/files/{stored_attachment.id}/versions/{version.id}/download/'
        )
        assert version_response.status_code == 200
        b''.join(version_response.streaming_content)

        assert OperationLog.objects.filter(
            module='files',
            operation_type=OperationLog.OperationType.DOWNLOAD,
            object_type='FileAsset',
            object_id=str(stored_attachment.id),
            description='通过受保护文件接口下载',
            is_success=True,
        ).exists()
        assert OperationLog.objects.filter(
            module='files',
            operation_type=OperationLog.OperationType.DOWNLOAD,
            object_type='FileVersion',
            object_id=str(version.id),
            description='通过受保护文件接口下载历史版本',
            is_success=True,
        ).exists()

    def test_approved_applicant_can_download_and_audit_contains_no_secret(
        self,
        member_client,
        stored_attachment,
    ):
        sensitive = SensitiveData.objects.create(
            title='不可写入审计的证件标题',
            data_type=SensitiveData.DataType.ID_CARD,
            file_attachment=stored_attachment,
        )
        request_obj = SensitiveAccessRequest.objects.create(
            sensitive_data=sensitive,
            applicant=member_client.user,
            reason='业务核验',
            usage_scenario='业务核验',
            is_download=True,
            status=SensitiveAccessRequest.Status.APPROVED,
            access_expires_at=timezone.now() + timedelta(hours=1),
        )

        response = member_client.get(
            f'/api/v1/sensitive/requests/{request_obj.id}/download-attachment/'
        )

        assert response.status_code == 200
        assert b'one-line-sensitive-demo' in b''.join(response.streaming_content)

        log = OperationLog.objects.filter(
            module='sensitive',
            operation_type=OperationLog.OperationType.DOWNLOAD,
            object_type='SensitiveAccessRequest',
            object_id=str(request_obj.id),
        ).latest('id')
        serialized_log = ' '.join([
            log.description,
            log.request_path,
            str(log.request_data or ''),
            log.error_message,
        ])
        assert log.is_success is True
        assert log.request_method == 'GET'
        assert '?' not in log.request_path
        assert 'identity-proof.pdf' not in serialized_log
        assert sensitive.title not in serialized_log
        assert 'one-line-sensitive-demo' not in serialized_log
        assert 'token' not in serialized_log.lower()

        request_data = extract_data(
            member_client.get('/api/v1/sensitive/requests/my_requests/')
        )
        request_row = next(
            item for item in request_data['results']
            if item['id'] == request_obj.id
        )
        assert request_row['has_attachment'] is True
        assert request_row['can_download_attachment'] is True

    @pytest.mark.parametrize(
        ('status_value', 'is_download', 'expires_delta'),
        [
            (SensitiveAccessRequest.Status.PENDING, True, 1),
            (SensitiveAccessRequest.Status.APPROVED, False, 1),
            (SensitiveAccessRequest.Status.APPROVED, True, -1),
            (SensitiveAccessRequest.Status.APPROVED, True, None),
        ],
    )
    def test_download_requires_every_approval_condition(
        self,
        member_client,
        stored_attachment,
        status_value,
        is_download,
        expires_delta,
    ):
        sensitive = SensitiveData.objects.create(
            title='条件校验',
            file_attachment=stored_attachment,
        )
        expires_at = (
            timezone.now() + timedelta(hours=expires_delta)
            if expires_delta is not None
            else None
        )
        request_obj = SensitiveAccessRequest.objects.create(
            sensitive_data=sensitive,
            applicant=member_client.user,
            reason='test',
            is_download=is_download,
            status=status_value,
            access_expires_at=expires_at,
        )

        response = member_client.get(
            f'/api/v1/sensitive/requests/{request_obj.id}/download-attachment/'
        )

        assert response.status_code == 403
        failed_log = OperationLog.objects.filter(
            module='sensitive',
            object_type='SensitiveAccessRequest',
            object_id=str(request_obj.id),
            operation_type=OperationLog.OperationType.DOWNLOAD,
        ).latest('id')
        assert failed_log.is_success is False
        assert failed_log.response_status == 403
        if expires_delta is not None and expires_delta < 0:
            request_obj.refresh_from_db()
            assert request_obj.status == SensitiveAccessRequest.Status.EXPIRED

    def test_other_user_cannot_use_an_applicants_download_request(
        self,
        member_client,
        stored_attachment,
        make_user,
    ):
        sensitive = SensitiveData.objects.create(
            title='仅限本人',
            file_attachment=stored_attachment,
        )
        other = make_user(email='approved-applicant@test.com')
        request_obj = SensitiveAccessRequest.objects.create(
            sensitive_data=sensitive,
            applicant=other,
            reason='test',
            is_download=True,
            status=SensitiveAccessRequest.Status.APPROVED,
            access_expires_at=timezone.now() + timedelta(hours=1),
        )

        response = member_client.get(
            f'/api/v1/sensitive/requests/{request_obj.id}/download-attachment/'
        )
        assert response.status_code == 404

    @pytest.mark.parametrize('role', ['teacher', 'sys_admin', 'sens_approver'])
    def test_privileged_roles_have_no_direct_download_bypass(
        self,
        role,
        stored_attachment,
        make_user,
    ):
        sensitive = SensitiveData.objects.create(
            title='审计下载',
            file_attachment=stored_attachment,
        )
        reviewer = make_user(
            email=f'{role}-attachment-audit@test.com',
            global_role=role,
        )

        response = client_for(reviewer).get(
            f'/api/v1/sensitive/data/{sensitive.id}/audit-download-attachment/'
        )

        assert response.status_code == 404

    def test_member_has_no_direct_download_route(
        self,
        member_client,
        stored_attachment,
    ):
        sensitive = SensitiveData.objects.create(
            title='审计角色限定',
            file_attachment=stored_attachment,
        )
        response = member_client.get(
            f'/api/v1/sensitive/data/{sensitive.id}/audit-download-attachment/'
        )
        assert response.status_code == 404

    def test_generic_download_is_closed_even_for_admin(
        self,
        admin_client,
        stored_attachment,
    ):
        SensitiveData.objects.create(
            title='必须走审计入口',
            file_attachment=stored_attachment,
        )
        response = admin_client.get(
            f'/api/v1/files/{stored_attachment.id}/download/'
        )
        assert response.status_code == 403
        log = OperationLog.objects.filter(
            module='files',
            object_type='FileAsset',
            object_id=str(stored_attachment.id),
        ).latest('id')
        assert log.operation_type == OperationLog.OperationType.DOWNLOAD
        assert log.is_success is False


@pytest.mark.api
@pytest.mark.django_db
class TestSensitiveShareBoundary:
    def test_api_rejects_sensitive_share_and_checks_internal_access(
        self,
        member_client,
        stored_attachment,
        make_project,
    ):
        SensitiveData.objects.create(
            title='禁止分享',
            file_attachment=stored_attachment,
        )
        denied_sensitive = member_client.post(
            '/api/v1/files/shares/',
            {'file': stored_attachment.id},
            format='json',
        )
        assert denied_sensitive.status_code == 403

        internal_file = FileAsset.objects.create(
            project=make_project(),
            name='internal.pdf',
            file='dummy/internal.pdf',
            level=FileAsset.Level.INTERNAL,
            uploader=member_client.user,
        )
        denied_internal = member_client.post(
            '/api/v1/files/shares/',
            {'file': internal_file.id},
            format='json',
        )
        assert denied_internal.status_code == 403

        ProjectMember.objects.create(
            project=internal_file.project,
            user=member_client.user,
            status=ProjectMember.Status.ACTIVE,
        )
        allowed_internal = member_client.post(
            '/api/v1/files/shares/',
            {'file': internal_file.id},
            format='json',
        )
        assert allowed_internal.status_code == 201

    def test_historical_active_sensitive_link_cannot_be_accessed_or_downloaded(
        self,
        api_client,
        stored_attachment,
        make_user,
    ):
        token = 'sensitive-history-token'
        link = FileShareLink.objects.create(
            file=stored_attachment,
            created_by=make_user(email='historical-share@test.com'),
            token=token,
        )
        FileAsset.objects.filter(pk=stored_attachment.id).update(
            level=FileAsset.Level.SENSITIVE
        )

        access = api_client.get(f'/api/v1/files/shares/access/?token={token}')
        download = api_client.get(
            f'/api/v1/files/shares/download/?token={token}'
        )

        assert access.status_code == 403
        assert download.status_code == 403
        link.refresh_from_db()
        assert link.view_count == 0
        log = OperationLog.objects.filter(
            module='files',
            object_type='FileShareLink',
            object_id=str(link.id),
        ).latest('id')
        assert token not in log.request_path
        assert token not in log.description
        assert log.request_data is None
        for recorded_log in OperationLog.objects.filter(
            request_path='/api/v1/files/shares/download/'
        ):
            recorded = ' '.join([
                recorded_log.request_path,
                recorded_log.description,
                json.dumps(recorded_log.request_data, ensure_ascii=False),
            ])
            assert token not in recorded

    def test_successful_share_download_is_explicitly_audited_without_token(
        self,
        api_client,
        stored_attachment,
        make_user,
    ):
        token = 'public-download-token'
        link = FileShareLink.objects.create(
            file=stored_attachment,
            created_by=make_user(email='public-share@test.com'),
            token=token,
        )

        response = api_client.get(
            f'/api/v1/files/shares/download/?token={token}'
        )

        assert response.status_code == 200
        b''.join(response.streaming_content)
        log = OperationLog.objects.filter(
            module='files',
            object_type='FileShareLink',
            object_id=str(link.id),
        ).latest('id')
        assert log.is_success is True
        assert log.request_method == 'GET'
        assert token not in log.request_path
        assert token not in log.description
        assert log.request_data is None
