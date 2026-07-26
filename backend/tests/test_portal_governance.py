import pytest
from rest_framework.test import APIClient

from apps.dashboard.portal_models import PortalPublication


def extract_data(response):
    payload = response.json()
    return payload.get('data', payload) if isinstance(payload, dict) else payload


@pytest.mark.api
@pytest.mark.django_db
class TestPortalGovernance:
    def test_new_content_is_not_public_by_default(self, api_client, make_project):
        project = make_project(current_stage=13)
        response = api_client.get('/api/v1/dashboard/public-portal/')
        assert response.status_code == 200
        ids = [item['project_id'] for item in extract_data(response)['awarded_projects']]
        assert project.id not in ids

    def test_teacher_can_publish_project_and_mark_featured(
        self, teacher_client, make_project
    ):
        project = make_project(current_stage=13)
        response = teacher_client.patch(
            f'/api/v1/dashboard/public-portal/publications/project/{project.id}/',
            {'is_public': True, 'is_featured': True, 'custom_title': '公开项目标题'},
            format='json',
        )
        assert response.status_code == 200, response.json()

        public_client = APIClient()
        public = extract_data(
            public_client.get('/api/v1/dashboard/public-portal/')
        )
        result = next(
            item for item in public['awarded_projects']
            if item['project_id'] == project.id
        )
        assert result['project_name'] == '公开项目标题'
        assert result['is_featured'] is True

    def test_member_consent_is_required_and_can_be_withdrawn(
        self, make_user, teacher_user
    ):
        member = make_user(email='consent@test.com', name='授权成员')
        teacher = APIClient()
        teacher.force_authenticate(teacher_user)
        member_api = APIClient()
        member_api.force_authenticate(member)

        denied = teacher.patch(
            f'/api/v1/dashboard/public-portal/publications/member/{member.id}/',
            {'is_public': True},
            format='json',
        )
        assert denied.status_code == 400

        consent = member_api.patch(
            '/api/v1/dashboard/public-portal/member-consent/',
            {'consent': True},
            format='json',
        )
        assert consent.status_code == 200
        published = teacher.patch(
            f'/api/v1/dashboard/public-portal/publications/member/{member.id}/',
            {'is_public': True},
            format='json',
        )
        assert published.status_code == 200, published.json()

        public = extract_data(APIClient().get('/api/v1/dashboard/public-portal/'))
        assert member.id in [item['user_id'] for item in public['core_members']]

        withdrawn = member_api.patch(
            '/api/v1/dashboard/public-portal/member-consent/',
            {'consent': False},
            format='json',
        )
        assert withdrawn.status_code == 200
        publication = PortalPublication.objects.get(
            content_type=PortalPublication.ContentType.MEMBER,
            object_id=member.id,
        )
        assert publication.member_consent is False
        assert publication.is_public is False

    def test_team_profile_can_be_updated(self, teacher_client):
        response = teacher_client.patch(
            '/api/v1/dashboard/public-portal/manage/',
            {
                'team_name': '真实团队名称',
                'join_message': '欢迎联系团队',
                'contact_email': 'join@example.com',
            },
            format='json',
        )
        assert response.status_code == 200, response.json()
        public = extract_data(APIClient().get('/api/v1/dashboard/public-portal/'))
        assert public['settings']['team_name'] == '真实团队名称'
        assert public['settings']['join_message'] == '欢迎联系团队'

    def test_member_cannot_manage_publications(self, member_client, make_project):
        project = make_project()
        response = member_client.patch(
            f'/api/v1/dashboard/public-portal/publications/project/{project.id}/',
            {'is_public': True},
            format='json',
        )
        assert response.status_code == 403
