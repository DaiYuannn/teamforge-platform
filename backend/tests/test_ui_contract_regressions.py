"""Regression tests for UI-to-API contracts used by the redesigned frontend."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.api
@pytest.mark.contract
@pytest.mark.django_db
class TestCompetitionFormContract:
    def test_optional_dates_accept_null_and_list_keeps_organizer(
        self, api_client, make_project,
    ):
        project = make_project()
        api_client.force_authenticate(user=project.leader)

        create_response = api_client.post('/api/v1/competitions/', {
            'project': project.id,
            'name': '创新创业大赛',
            'level': 'province',
            'status': 'preparing',
            'organizer': '省教育厅',
            'register_date': None,
            'defense_date': None,
            'result_date': None,
        }, format='json')

        assert create_response.status_code == 201, create_response.json()
        created = create_response.json()['data']
        assert created['register_date'] is None
        assert created['defense_date'] is None
        assert created['result_date'] is None

        list_response = api_client.get('/api/v1/competitions/')
        assert list_response.status_code == 200, list_response.json()
        payload = list_response.json().get('data', list_response.json())
        rows = payload.get('results', payload) if isinstance(payload, dict) else payload
        row = next(item for item in rows if item['id'] == created['id'])
        assert row['organizer'] == '省教育厅'

    def test_full_workflow_fields_round_trip_and_partial_update_preserves_them(
        self, api_client, make_project,
    ):
        project = make_project()
        api_client.force_authenticate(user=project.leader)
        workflow = {
            'project': project.id,
            'name': '挑战杯全流程记录',
            'comp_type': '创新创业',
            'level': 'national',
            'status': 'completed',
            'organizer': '全国竞赛组委会',
            'current_stage': '获奖归档',
            'register_date': '2026-01-02',
            'material_deadline': '2026-01-20',
            'review_date': '2026-02-02',
            'defense_date': '2026-02-15',
            'school_date': '2026-02-20',
            'city_date': '2026-03-01',
            'province_date': '2026-03-20',
            'national_date': '2026-04-10',
            'result_date': '2026-04-15',
            'is_promoted': True,
            'is_awarded': True,
            'award_level': '国赛一等奖',
            'not_promoted_reason': '',
            'review_summary': '评委重点询问真实用户数据和成本结构。',
            'improvement_suggestion': '补齐落地单位证明与三年财务测算。',
        }

        create_response = api_client.post(
            '/api/v1/competitions/',
            workflow,
            format='json',
        )
        assert create_response.status_code == 201, create_response.json()
        created = create_response.json()['data']

        for field, expected in workflow.items():
            assert created[field] == expected

        competition_id = created['id']
        patch_response = api_client.patch(
            f'/api/v1/competitions/{competition_id}/',
            {'current_stage': '国赛已完成'},
            format='json',
        )
        assert patch_response.status_code == 200, patch_response.json()

        detail_response = api_client.get(f'/api/v1/competitions/{competition_id}/')
        assert detail_response.status_code == 200, detail_response.json()
        detail = detail_response.json().get('data', detail_response.json())
        assert detail['current_stage'] == '国赛已完成'
        for field in (
            'material_deadline', 'review_date', 'defense_date',
            'school_date', 'city_date', 'province_date', 'national_date',
            'result_date', 'award_level', 'review_summary',
            'improvement_suggestion',
        ):
            assert detail[field] == workflow[field]

        list_response = api_client.get('/api/v1/competitions/')
        payload = list_response.json().get('data', list_response.json())
        rows = payload.get('results', payload) if isinstance(payload, dict) else payload
        row = next(item for item in rows if item['id'] == competition_id)
        assert row['current_stage'] == '国赛已完成'


@pytest.mark.api
@pytest.mark.contract
@pytest.mark.django_db
class TestContributionProofUploadContract:
    def test_proof_upload_creates_internal_file_in_same_project(
        self, api_client, make_project, make_user,
    ):
        from apps.contributions.models import ProjectContributionReviewer

        project = make_project()
        reviewer = make_user(email='proof-reviewer@example.com')
        ProjectContributionReviewer.objects.create(
            project=project,
            user=reviewer,
            is_independent=True,
        )
        upload = SimpleUploadedFile(
            'contribution-proof.txt',
            b'proof content',
            content_type='text/plain',
        )
        api_client.force_authenticate(user=project.leader)

        response = api_client.post('/api/v1/contributions/contributions/', {
            'project': project.id,
            'user': project.leader.id,
            'contribution_type': 'project_leader',
            'content': '负责项目统筹与交付',
            'proof_upload': upload,
        }, format='multipart')

        assert response.status_code == 201, response.json()
        contribution_id = response.json()['data']['id']

        from apps.contributions.models import Contribution

        contribution = Contribution.objects.select_related('proof_file').get(pk=contribution_id)
        assert contribution.proof_file is not None
        assert contribution.proof_file.project_id == project.id
        assert contribution.proof_file.level == 'internal'
        assert contribution.proof_file.uploader_id == project.leader.id
        assert contribution.proof_file.name == 'contribution-proof.txt'
