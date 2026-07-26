import pytest


def extract_data(response):
    payload = response.json()
    return payload.get('data', payload) if isinstance(payload, dict) else payload


@pytest.mark.api
@pytest.mark.django_db
class TestTaskAttachments:
    def test_create_task_with_file_asset(self, teacher_client, make_project, make_file):
        project = make_project(leader=teacher_client.user)
        file_asset = make_file(
            project=project,
            uploader=teacher_client.user,
            level='internal',
        )
        response = teacher_client.post(
            '/api/v1/tasks/',
            {
                'project': project.id,
                'title': '含附件任务',
                'assignee': teacher_client.user.id,
                'status': 'todo',
                'priority': 'medium',
                'attachment_ids': [file_asset.id],
            },
            format='json',
        )
        assert response.status_code == 201, response.json()
        data = extract_data(response)
        assert [item['id'] for item in data['attachment_files']] == [file_asset.id]

    def test_attachment_must_belong_to_same_project(
        self, teacher_client, make_project, make_file
    ):
        project = make_project(leader=teacher_client.user)
        other_project = make_project()
        file_asset = make_file(project=other_project)
        response = teacher_client.post(
            '/api/v1/tasks/',
            {
                'project': project.id,
                'title': '错误附件',
                'assignee': teacher_client.user.id,
                'attachment_ids': [file_asset.id],
            },
            format='json',
        )
        assert response.status_code == 400

    def test_sensitive_file_cannot_be_attached_directly(
        self, teacher_client, make_project, make_file
    ):
        project = make_project(leader=teacher_client.user)
        file_asset = make_file(
            project=project,
            uploader=teacher_client.user,
            level='sensitive',
        )
        response = teacher_client.post(
            '/api/v1/tasks/',
            {
                'project': project.id,
                'title': '敏感附件任务',
                'assignee': teacher_client.user.id,
                'attachment_ids': [file_asset.id],
            },
            format='json',
        )
        assert response.status_code == 400
