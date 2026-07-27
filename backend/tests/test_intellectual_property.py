"""Focused API contracts and permission boundaries for intellectual property."""
from itertools import count

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.contributions.models import Contribution
from apps.files.models import FileAsset
from apps.intellectual_property.models import (
    IntellectualPropertyApplication,
    IPApplicationContributor,
    IPMaterialVersion,
    IPObjection,
    IPReturnRecord,
)
from apps.projects.models import ProjectMember


APPLICATION_URL = '/api/v1/intellectual-property/applications/'
CONTRIBUTOR_URL = '/api/v1/intellectual-property/contributors/'
RETURN_URL = '/api/v1/intellectual-property/returns/'
MATERIAL_URL = '/api/v1/intellectual-property/materials/'
OBJECTION_URL = '/api/v1/intellectual-property/objections/'
_application_codes = count(1)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


def response_data(response):
    body = response.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data')
    return body


def response_results(response):
    data = response_data(response)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


def make_application(project, main_writer=None, **extra):
    number = next(_application_codes)
    main_writer = main_writer or project.leader
    return IntellectualPropertyApplication.objects.create(
        title=extra.pop('title', f'知识产权申请 {number}'),
        application_code=extra.pop('application_code', f'IP-TEST-{number:04d}'),
        related_project=project,
        main_writer=main_writer,
        created_by=extra.pop('created_by', project.leader),
        **extra,
    )


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
class TestIPApplicationPermissions:
    def test_teacher_can_delete_application(
        self, teacher_client, make_project
    ):
        application = make_application(make_project())

        response = teacher_client.delete(f'{APPLICATION_URL}{application.id}/')

        assert response.status_code == 200, response.json()
        assert not IntellectualPropertyApplication.objects.filter(
            pk=application.id
        ).exists()

    def test_project_leader_can_create_but_other_member_cannot(
        self, leader_client, make_project, make_user
    ):
        project = make_project(leader=leader_client.user)
        response = leader_client.post(APPLICATION_URL, {
            'title': '负责人创建的申请',
            'application_code': 'IP-LEADER-CREATE',
            'ip_type': 'software_copyright',
            'related_project': project.id,
            'main_writer': leader_client.user.id,
        }, format='json')
        assert response.status_code == 201, response.json()
        created = IntellectualPropertyApplication.objects.get(
            application_code='IP-LEADER-CREATE'
        )
        assert created.project_reviewer_id == leader_client.user.id

        outsider = make_user(email='ip-outsider-create@test.com')
        response = client_for(outsider).post(APPLICATION_URL, {
            'title': '越权申请',
            'application_code': 'IP-OUTSIDER-CREATE',
            'ip_type': 'software_copyright',
            'related_project': project.id,
            'main_writer': leader_client.user.id,
        }, format='json')
        assert response.status_code == 403
        assert not IntellectualPropertyApplication.objects.filter(
            application_code='IP-OUTSIDER-CREATE'
        ).exists()

    def test_create_persists_complete_responsibility_chain(
        self, leader_client, make_project, make_user
    ):
        project = make_project(leader=leader_client.user)
        writer = make_user(email='ip-chain-writer@test.com')
        executor = make_user(email='ip-chain-executor@test.com')
        material_manager = make_user(email='ip-chain-material@test.com')
        teacher = make_user(
            email='ip-chain-teacher@test.com', global_role='teacher'
        )
        for member in (writer, executor, material_manager):
            ProjectMember.objects.create(project=project, user=member)

        response = leader_client.post(APPLICATION_URL, {
            'title': '完整责任链申请',
            'application_code': 'IP-CHAIN-CREATE',
            'ip_type': 'invention_patent',
            'related_project': project.id,
            'main_writer': writer.id,
            'applicant_executor': executor.id,
            'material_manager': material_manager.id,
            'project_reviewer': project.leader_id,
            'teacher_confirmer': teacher.id,
            'start_date': '2026-07-01',
            'current_problem': '等待技术交底书确认',
            'intro': '验证责任链字段在创建接口中完整落库。',
        }, format='json')

        assert response.status_code == 201, response.json()
        assert response_data(response)['current_problem'] == '等待技术交底书确认'
        application = IntellectualPropertyApplication.objects.get(
            application_code='IP-CHAIN-CREATE'
        )
        assert application.main_writer_id == writer.id
        assert application.applicant_executor_id == executor.id
        assert application.material_manager_id == material_manager.id
        assert application.project_reviewer_id == project.leader_id
        assert application.teacher_confirmer_id == teacher.id
        assert str(application.start_date) == '2026-07-01'
        assert application.current_problem == '等待技术交底书确认'

    def test_create_rejects_invalid_reviewer_and_teacher_roles(
        self, leader_client, make_project, make_user
    ):
        project = make_project(leader=leader_client.user)
        member = make_user(email='ip-chain-member@test.com')
        ProjectMember.objects.create(project=project, user=member)
        base_payload = {
            'title': '无效责任链申请',
            'application_code': 'IP-CHAIN-INVALID-REVIEWER',
            'ip_type': 'software_copyright',
            'related_project': project.id,
            'main_writer': member.id,
            'project_reviewer': member.id,
        }

        invalid_reviewer = leader_client.post(
            APPLICATION_URL, base_payload, format='json'
        )
        assert invalid_reviewer.status_code == 400, invalid_reviewer.json()

        base_payload.update({
            'application_code': 'IP-CHAIN-INVALID-TEACHER',
            'project_reviewer': project.leader_id,
            'teacher_confirmer': member.id,
        })
        invalid_teacher = leader_client.post(
            APPLICATION_URL, base_payload, format='json'
        )
        assert invalid_teacher.status_code == 400, invalid_teacher.json()

    def test_project_leader_todo_uses_related_project_fallback(
        self, leader_client, make_project
    ):
        project = make_project(leader=leader_client.user)
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.LEADER_REVIEW,
            project_reviewer=None,
        )

        response = leader_client.get(f'{APPLICATION_URL}my_todo/')

        assert response.status_code == 200, response.json()
        assert application.id in {
            item['id'] for item in response_results(response)
        }

    def test_teacher_todo_includes_unassigned_teacher_confirmation(
        self, teacher_client, make_project
    ):
        application = make_application(
            make_project(),
            status=IntellectualPropertyApplication.Status.TEACHER_CONFIRM,
            teacher_confirmer=None,
        )

        response = teacher_client.get(f'{APPLICATION_URL}my_todo/')

        assert response.status_code == 200, response.json()
        assert application.id in {
            item['id'] for item in response_results(response)
        }

    def test_update_accepts_application_code(self, leader_client, make_project):
        project = make_project(leader=leader_client.user)
        application = make_application(project)

        response = leader_client.patch(
            f'{APPLICATION_URL}{application.id}/',
            {'application_code': 'IP-CODE-UPDATED'},
            format='json',
        )

        assert response.status_code == 200, response.json()
        application.refresh_from_db()
        assert application.application_code == 'IP-CODE-UPDATED'

    def test_main_writer_cannot_move_application_to_unmanaged_project(
        self, make_project, make_user
    ):
        writer = make_user(email='ip-writer@test.com')
        source = make_project()
        target = make_project()
        ProjectMember.objects.create(project=source, user=writer)
        application = make_application(source, main_writer=writer)

        response = client_for(writer).patch(
            f'{APPLICATION_URL}{application.id}/',
            {'related_project': target.id},
            format='json',
        )

        assert response.status_code == 400, response.json()
        application.refresh_from_db()
        assert application.related_project_id == source.id

    def test_transition_uses_current_stage_business_role(
        self, make_project, make_user
    ):
        reviewer = make_user(email='ip-reviewer@test.com')
        project = make_project()
        ProjectMember.objects.create(project=project, user=reviewer)
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.LEADER_REVIEW,
            project_reviewer=reviewer,
        )

        response = client_for(reviewer).post(
            f'{APPLICATION_URL}{application.id}/transition/',
            {'target_status': 'teacher_confirm'},
            format='json',
        )

        assert response.status_code == 200, response.json()
        application.refresh_from_db()
        assert application.status == 'teacher_confirm'

    def test_writer_cannot_complete_research_office_review(
        self, make_project, make_user
    ):
        writer = make_user(email='ip-office-writer@test.com')
        project = make_project()
        ProjectMember.objects.create(project=project, user=writer)
        application = make_application(
            project,
            main_writer=writer,
            status=IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
        )

        response = client_for(writer).post(
            f'{APPLICATION_URL}{application.id}/transition/',
            {'target_status': 'accepted'},
            format='json',
        )

        assert response.status_code == 403
        application.refresh_from_db()
        assert application.status == 'research_office_review'

    def test_writer_cannot_skip_review_after_resubmission(
        self, make_project, make_user
    ):
        writer = make_user(email='ip-resubmitted-writer@test.com')
        project = make_project()
        ProjectMember.objects.create(project=project, user=writer)
        application = make_application(
            project,
            main_writer=writer,
            status=IntellectualPropertyApplication.Status.RESUBMITTED,
        )

        response = client_for(writer).post(
            f'{APPLICATION_URL}{application.id}/transition/',
            {'target_status': 'accepted'},
            format='json',
        )

        assert response.status_code == 403
        application.refresh_from_db()
        assert application.status == 'resubmitted'

    def test_generic_transition_cannot_bypass_return_or_archive_workflows(
        self, teacher_client, make_project
    ):
        project = make_project()
        under_review = make_application(
            project,
            status=IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
        )
        authorized = make_application(
            project,
            status=IntellectualPropertyApplication.Status.AUTHORIZED,
        )

        returned = teacher_client.post(
            f'{APPLICATION_URL}{under_review.id}/transition/',
            {'target_status': 'returned'},
            format='json',
        )
        archived = teacher_client.post(
            f'{APPLICATION_URL}{authorized.id}/transition/',
            {'target_status': 'archived'},
            format='json',
        )

        assert returned.status_code == 400, returned.json()
        assert archived.status_code == 400, archived.json()
        under_review.refresh_from_db()
        authorized.refresh_from_db()
        assert under_review.status == 'research_office_review'
        assert authorized.status == 'authorized'
        assert not IPReturnRecord.objects.filter(application=under_review).exists()

    def test_generic_transition_cannot_bypass_return_resolution(
        self, leader_client, make_project
    ):
        project = make_project(leader=leader_client.user)
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.MODIFYING,
        )

        response = leader_client.post(
            f'{APPLICATION_URL}{application.id}/transition/',
            {'target_status': 'resubmitted'},
            format='json',
        )

        assert response.status_code == 400, response.json()
        application.refresh_from_db()
        assert application.status == 'modifying'

    def test_deferred_state_is_reachable_and_can_be_restarted(
        self, leader_client, make_project
    ):
        project = make_project(leader=leader_client.user)
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.WRITING,
        )

        deferred = leader_client.post(
            f'{APPLICATION_URL}{application.id}/transition/',
            {'target_status': 'deferred'},
            format='json',
        )
        restarted = leader_client.post(
            f'{APPLICATION_URL}{application.id}/transition/',
            {'target_status': 'draft'},
            format='json',
        )

        assert deferred.status_code == 200, deferred.json()
        assert restarted.status_code == 200, restarted.json()
        application.refresh_from_db()
        assert application.status == 'draft'

    def test_authorization_automatically_syncs_responsibility_contributions_idempotently(
        self, teacher_client, make_project, make_user
    ):
        project = make_project()
        executor = make_user(email='ip-auto-sync-executor@test.com')
        ProjectMember.objects.create(project=project, user=executor)
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.ACCEPTED,
            applicant_executor=executor,
            project_reviewer=project.leader,
        )

        authorized = teacher_client.post(
            f'{APPLICATION_URL}{application.id}/transition/',
            {'target_status': 'authorized'},
            format='json',
        )
        assert authorized.status_code == 200, authorized.json()
        assert Contribution.objects.filter(
            user=project.leader,
            project=project,
            contribution_type=Contribution.ContributionType.IP_WRITING,
            related_object_id=application.id,
        ).count() == 1
        assert Contribution.objects.filter(
            user=executor,
            project=project,
            contribution_type=Contribution.ContributionType.IP_EXECUTION,
            related_object_id=application.id,
        ).count() == 1

        resync = teacher_client.post(
            f'{APPLICATION_URL}{application.id}/sync_contribution/'
        )
        assert resync.status_code == 200, resync.json()
        assert response_data(resync)['synced_count'] == 0
        assert Contribution.objects.filter(
            project=project,
            related_object_id=application.id,
        ).count() == 2


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
class TestIPRelatedRecordIsolation:
    def test_related_lists_only_include_accessible_projects(
        self, make_project, make_user, make_file
    ):
        member = make_user(email='ip-visible-member@test.com')
        visible_project = make_project()
        hidden_project = make_project()
        ProjectMember.objects.create(project=visible_project, user=member)
        visible = make_application(visible_project)
        hidden = make_application(hidden_project)

        visible_contributor = IPApplicationContributor.objects.create(
            application=visible, user=member, role='co_writer'
        )
        hidden_contributor = IPApplicationContributor.objects.create(
            application=hidden, user=hidden_project.leader, role='co_writer'
        )
        now = timezone.now()
        visible_return = IPReturnRecord.objects.create(
            application=visible, return_time=now, return_reason='可见退回'
        )
        hidden_return = IPReturnRecord.objects.create(
            application=hidden, return_time=now, return_reason='隐藏退回'
        )
        visible_material = IPMaterialVersion.objects.create(
            application=visible,
            file_asset=make_file(project=visible_project),
            uploaded_by=visible_project.leader,
        )
        hidden_material = IPMaterialVersion.objects.create(
            application=hidden,
            file_asset=make_file(project=hidden_project),
            uploaded_by=hidden_project.leader,
        )
        visible_objection = IPObjection.objects.create(
            application=visible, objector=member, content='可见异议'
        )
        hidden_objection = IPObjection.objects.create(
            application=hidden, objector=hidden_project.leader, content='隐藏异议'
        )

        client = client_for(member)
        cases = (
            (CONTRIBUTOR_URL, visible_contributor.id, hidden_contributor.id),
            (RETURN_URL, visible_return.id, hidden_return.id),
            (MATERIAL_URL, visible_material.id, hidden_material.id),
            (OBJECTION_URL, visible_objection.id, hidden_objection.id),
        )
        for url, visible_id, hidden_id in cases:
            response = client.get(url)
            assert response.status_code == 200, response.json()
            ids = {item['id'] for item in response_results(response)}
            assert visible_id in ids
            assert hidden_id not in ids
            assert client.get(f'{url}{hidden_id}/').status_code == 404

    def test_member_cannot_patch_return_record(self, make_project, make_user):
        member = make_user(email='ip-return-member@test.com')
        project = make_project()
        ProjectMember.objects.create(project=project, user=member)
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
        )
        record = IPReturnRecord.objects.create(
            application=application,
            return_time=timezone.now(),
            return_reason='原原因',
        )

        response = client_for(member).patch(
            f'{RETURN_URL}{record.id}/', {'return_reason': '越权修改'}, format='json'
        )

        assert response.status_code == 403
        record.refresh_from_db()
        assert record.return_reason == '原原因'


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
class TestIPContributionConfirmation:
    def test_leader_creates_and_contributor_confirms_idempotently(
        self, leader_client, make_project, make_user
    ):
        project = make_project(leader=leader_client.user)
        contributor_user = make_user(email='ip-contributor@test.com')
        ProjectMember.objects.create(project=project, user=contributor_user)
        application = make_application(project)

        response = leader_client.post(CONTRIBUTOR_URL, {
            'application': application.id,
            'user': contributor_user.id,
            'role': 'co_writer',
            'contribution_description': '共同撰写',
        }, format='json')
        assert response.status_code == 201, response.json()
        contributor_id = response_data(response)['id']

        contributor_client = client_for(contributor_user)
        first = contributor_client.post(f'{CONTRIBUTOR_URL}{contributor_id}/confirm/')
        second = contributor_client.post(f'{CONTRIBUTOR_URL}{contributor_id}/confirm/')
        assert first.status_code == second.status_code == 200

        contributor = IPApplicationContributor.objects.get(pk=contributor_id)
        assert contributor.is_confirmed is True
        assert contributor.confirmed_by_id == contributor_user.id
        assert contributor.confirmed_at is not None

        denied = leader_client.post(f'{CONTRIBUTOR_URL}{contributor_id}/confirm/')
        assert denied.status_code == 403

    def test_editing_confirmed_assignment_requires_reconfirmation(
        self, leader_client, make_project, make_user
    ):
        project = make_project(leader=leader_client.user)
        contributor_user = make_user(email='ip-confirmed-edit@test.com')
        ProjectMember.objects.create(project=project, user=contributor_user)
        application = make_application(project)
        contributor = IPApplicationContributor.objects.create(
            application=application,
            user=contributor_user,
            role='co_writer',
            is_confirmed=True,
            confirmed_by=contributor_user,
            confirmed_at=timezone.now(),
        )

        response = leader_client.patch(
            f'{CONTRIBUTOR_URL}{contributor.id}/',
            {'contribution_description': '调整后的分工'},
            format='json',
        )

        assert response.status_code == 200, response.json()
        contributor.refresh_from_db()
        assert contributor.is_confirmed is False
        assert contributor.confirmed_by is None
        assert contributor.confirmed_at is None

    def test_leader_cannot_assign_non_project_user(
        self, leader_client, make_project, make_user
    ):
        project = make_project(leader=leader_client.user)
        application = make_application(project)
        outsider = make_user(email='ip-contribution-outsider@test.com')

        response = leader_client.post(CONTRIBUTOR_URL, {
            'application': application.id,
            'user': outsider.id,
            'role': 'co_writer',
        }, format='json')

        assert response.status_code == 400, response.json()


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
class TestIPUploadsAndReturnContract:
    def test_material_upload_creates_internal_project_file(
        self, tmp_path, make_project, make_user
    ):
        member = make_user(email='ip-material-member@test.com')
        project = make_project()
        ProjectMember.objects.create(project=project, user=member)
        application = make_application(project)
        upload = SimpleUploadedFile(
            'manual.txt', b'IP material', content_type='text/plain'
        )

        with override_settings(MEDIA_ROOT=tmp_path):
            response = client_for(member).post(MATERIAL_URL, {
                'application': application.id,
                'material_type': 'manual',
                'version': 'v1',
                'material_upload': upload,
            }, format='multipart')

        assert response.status_code == 201, response.json()
        material = IPMaterialVersion.objects.get(pk=response_data(response)['id'])
        assert material.file_asset.project_id == project.id
        assert material.file_asset.level == FileAsset.Level.INTERNAL
        assert material.file_asset.uploader_id == member.id
        assert material.file_asset.name == 'manual.txt'

        update_response = client_for(member).patch(
            f'{MATERIAL_URL}{material.id}/',
            {'change_note': '补充材料说明'},
            format='json',
        )
        assert update_response.status_code == 200, update_response.json()
        material.refresh_from_db()
        assert material.change_note == '补充材料说明'

    def test_certificate_and_final_material_are_required_for_archive(
        self, tmp_path, teacher_client, make_project
    ):
        project = make_project()
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.AUTHORIZED,
        )
        archive_url = f'{APPLICATION_URL}{application.id}/archive/'

        missing_certificate = teacher_client.post(archive_url)
        assert missing_certificate.status_code == 400
        assert '最终授权/登记证书' in missing_certificate.json()['message']

        with override_settings(MEDIA_ROOT=tmp_path):
            certificate_response = teacher_client.patch(
                f'{APPLICATION_URL}{application.id}/',
                {
                    'final_certificate_upload': SimpleUploadedFile(
                        'certificate.pdf',
                        b'%PDF-1.4\nfinal certificate\n%%EOF',
                        content_type='application/pdf',
                    )
                },
                format='multipart',
            )
            assert certificate_response.status_code == 200, certificate_response.json()
            assert (
                response_data(certificate_response)['final_certificate_file_name']
                == 'certificate.pdf'
            )
            application.refresh_from_db()
            assert application.final_certificate_file.project_id == project.id
            assert application.final_certificate_file.level == FileAsset.Level.INTERNAL
            assert application.final_certificate_file.file.storage.exists(
                application.final_certificate_file.file.name
            )

            missing_final_material = teacher_client.post(archive_url)
            assert missing_final_material.status_code == 400
            assert '最终版' in missing_final_material.json()['message']

            material_response = teacher_client.post(MATERIAL_URL, {
                'application': application.id,
                'material_type': 'archive',
                'version': 'v-final',
                'is_final': True,
                'material_upload': SimpleUploadedFile(
                    'archive.pdf',
                    b'%PDF-1.4\nfinal material\n%%EOF',
                    content_type='application/pdf',
                ),
            }, format='multipart')
            assert material_response.status_code == 201, material_response.json()
            assert response_data(material_response)['is_final'] is True

            archived = teacher_client.post(archive_url)
            assert archived.status_code == 200, archived.json()

        application.refresh_from_db()
        assert application.status == IntellectualPropertyApplication.Status.ARCHIVED

    def test_archive_rejects_missing_physical_certificate(
        self, tmp_path, teacher_client, make_project, make_file
    ):
        project = make_project()
        missing_certificate = make_file(
            project=project,
            level=FileAsset.Level.INTERNAL,
            name='missing-certificate.pdf',
        )
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.AUTHORIZED,
            final_certificate_file=missing_certificate,
        )
        IPMaterialVersion.objects.create(
            application=application,
            file_asset=make_file(
                project=project,
                level=FileAsset.Level.INTERNAL,
                name='missing-final.pdf',
            ),
            material_type=IPMaterialVersion.MaterialType.ARCHIVE,
            uploaded_by=project.leader,
            is_final=True,
        )

        with override_settings(MEDIA_ROOT=tmp_path):
            response = teacher_client.post(
                f'{APPLICATION_URL}{application.id}/archive/'
            )

        assert response.status_code == 400
        assert '最终证书文件不存在' in response.json()['message']
        application.refresh_from_db()
        assert application.status == IntellectualPropertyApplication.Status.AUTHORIZED

    def test_certificate_upload_rejects_unsafe_file_type(
        self, leader_client, make_project
    ):
        application = make_application(make_project(leader=leader_client.user))

        response = leader_client.patch(
            f'{APPLICATION_URL}{application.id}/',
            {
                'final_certificate_upload': SimpleUploadedFile(
                    'certificate.exe',
                    b'not a certificate',
                    content_type='application/octet-stream',
                )
            },
            format='multipart',
        )

        assert response.status_code == 400, response.json()
        application.refresh_from_db()
        assert application.final_certificate_file is None

    def test_objection_proof_upload_creates_internal_project_file(
        self, tmp_path, make_project, make_user
    ):
        member = make_user(email='ip-objection-member@test.com')
        project = make_project()
        ProjectMember.objects.create(project=project, user=member)
        application = make_application(project)
        upload = SimpleUploadedFile(
            'proof.txt', b'proof content', content_type='text/plain'
        )

        with override_settings(MEDIA_ROOT=tmp_path):
            response = client_for(member).post(OBJECTION_URL, {
                'application': application.id,
                'objection_type': 'writing_credit',
                'content': '贡献归属需要复核',
                'proof_upload': upload,
            }, format='multipart')

        assert response.status_code == 201, response.json()
        objection = IPObjection.objects.get(pk=response_data(response)['id'])
        assert objection.proof_file.project_id == project.id
        assert objection.proof_file.level == FileAsset.Level.INTERNAL
        assert objection.proof_file.uploader_id == member.id
        assert objection.proof_file.name == 'proof.txt'

    def test_unrelated_user_cannot_upload_material_or_objection(
        self, make_project, make_user
    ):
        outsider = make_user(email='ip-upload-outsider@test.com')
        application = make_application(make_project())
        client = client_for(outsider)

        material_response = client.post(MATERIAL_URL, {
            'application': application.id,
            'material_type': 'manual',
            'material_upload': SimpleUploadedFile('material.txt', b'material'),
        }, format='multipart')
        objection_response = client.post(OBJECTION_URL, {
            'application': application.id,
            'content': '越权异议',
            'proof_upload': SimpleUploadedFile('proof.txt', b'proof'),
        }, format='multipart')

        assert material_response.status_code == 403
        assert objection_response.status_code == 403

    def test_return_time_required_and_null_deadline_accepted(
        self, leader_client, make_project
    ):
        project = make_project(leader=leader_client.user)
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
        )
        payload = {
            'application': application.id,
            'return_reason': '材料需要修改',
            'modify_deadline': None,
        }

        missing_time = leader_client.post(RETURN_URL, payload, format='json')
        assert missing_time.status_code == 400

        payload['return_time'] = timezone.now().isoformat()
        response = leader_client.post(RETURN_URL, payload, format='json')
        assert response.status_code == 201, response.json()
        record = IPReturnRecord.objects.get(pk=response_data(response)['id'])
        assert record.modify_deadline is None

    def test_return_resolve_validates_payload_and_is_not_repeatable(
        self, make_project, make_user
    ):
        modifier = make_user(email='ip-return-modifier@test.com')
        project = make_project()
        ProjectMember.objects.create(project=project, user=modifier)
        application = make_application(
            project,
            status=IntellectualPropertyApplication.Status.RETURNED,
        )
        record = IPReturnRecord.objects.create(
            application=application,
            return_time=timezone.now(),
            return_reason='需要修改',
            responsible_user=modifier,
        )
        client = client_for(modifier)

        invalid = client.post(
            f'{RETURN_URL}{record.id}/resolve/',
            {'modify_description': '', 'result': 'invalid'},
            format='json',
        )
        assert invalid.status_code == 400

        resolved = client.post(
            f'{RETURN_URL}{record.id}/resolve/',
            {'modify_description': '已完成修改', 'result': 'modified'},
            format='json',
        )
        assert resolved.status_code == 200, resolved.json()

        repeated = client.post(
            f'{RETURN_URL}{record.id}/resolve/',
            {'modify_description': '重复提交', 'result': 'modified'},
            format='json',
        )
        assert repeated.status_code == 400

    def test_rejects_file_asset_from_another_project(
        self, make_project, make_user, make_file
    ):
        member = make_user(email='ip-cross-file-member@test.com')
        project = make_project()
        other_project = make_project()
        ProjectMember.objects.create(project=project, user=member)
        application = make_application(project)
        other_file = make_file(project=other_project)

        response = client_for(member).post(OBJECTION_URL, {
            'application': application.id,
            'content': '跨项目文件',
            'proof_file': other_file.id,
        }, format='json')

        assert response.status_code == 400, response.json()


@pytest.mark.api
@pytest.mark.django_db
class TestIPObjectionReviewContract:
    def test_leader_review_then_teacher_confirmation(
        self, make_project, make_user
    ):
        project = make_project()
        leader_client = client_for(project.leader)
        teacher = make_user(
            email='ip-review-teacher@test.com', global_role='teacher'
        )
        teacher_client = client_for(teacher)
        objector = make_user(email='ip-review-objector@test.com')
        ProjectMember.objects.create(project=project, user=objector)
        application = make_application(project)
        objection = IPObjection.objects.create(
            application=application,
            objector=objector,
            content='申请复核贡献归属',
        )

        leader_response = leader_client.patch(
            f'{OBJECTION_URL}{objection.id}/review/',
            {'action': 'leader_review', 'leader_opinion': '同意提交老师确认'},
            format='json',
        )
        assert leader_response.status_code == 200, leader_response.json()

        teacher_response = teacher_client.patch(
            f'{OBJECTION_URL}{objection.id}/review/',
            {
                'action': 'teacher_confirm',
                'teacher_opinion': '已核实',
                'final_result': '补充贡献说明',
                'final_status': 'resolved',
            },
            format='json',
        )
        assert teacher_response.status_code == 200, teacher_response.json()
        objection.refresh_from_db()
        assert objection.status == IPObjection.ObjectionStatus.RESOLVED
        assert objection.teacher_confirmer_id == teacher.id
