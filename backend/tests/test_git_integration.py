"""
N45: Git 集成测试
- /api/v1/integrations/git-repositories/   Git 仓库 CRUD
"""
import pytest
from subprocess import CompletedProcess
from unittest.mock import patch

from apps.integrations.git_models import GitRepository


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestGitIntegration:
    """Git 集成测试"""

    def test_create_repo(self, admin_client, make_project):
        """管理员创建 Git 仓库"""
        project = make_project()
        resp = admin_client.post('/api/v1/integrations/git-repositories/', {
            'url': 'https://github.com/org/repo.git',
            'branch': 'main',
            'token': 'ghp_token',
            'project': project.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        repo = GitRepository.objects.get(url='https://github.com/org/repo.git')
        assert repo.created_by == admin_client.user
        assert repo.branch == 'main'
        assert repo.token != 'ghp_token'
        assert repo.token.startswith('enc:v1:')
        assert repo.get_token() == 'ghp_token'

    def test_list_repos(self, admin_client, make_project):
        """列出 Git 仓库"""
        project = make_project()
        GitRepository.objects.create(url='https://github.com/a/b.git', project=project)
        resp = admin_client.get('/api/v1/integrations/git-repositories/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert any(r['url'] == 'https://github.com/a/b.git' for r in items)

    def test_member_cannot_create(self, member_client, make_project):
        """普通成员不能创建"""
        project = make_project()
        resp = member_client.post('/api/v1/integrations/git-repositories/', {
            'url': 'https://github.com/x/y.git', 'project': project.id,
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_update_repo(self, admin_client, make_project):
        """更新 Git 仓库"""
        project = make_project()
        repo = GitRepository.objects.create(url='https://github.com/u/v.git', project=project)
        resp = admin_client.patch(f'/api/v1/integrations/git-repositories/{repo.id}/', {
            'branch': 'develop',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        repo.refresh_from_db()
        assert repo.branch == 'develop'

    def test_delete_repo(self, admin_client, make_project):
        """删除 Git 仓库"""
        project = make_project()
        repo = GitRepository.objects.create(url='https://github.com/d/e.git', project=project)
        resp = admin_client.delete(f'/api/v1/integrations/git-repositories/{repo.id}/')
        assert resp.status_code in (200, 204)
        assert not GitRepository.objects.filter(id=repo.id).exists()

    def test_token_write_only(self, admin_client, make_project):
        """token 仅写不读"""
        project = make_project()
        admin_client.post('/api/v1/integrations/git-repositories/', {
            'url': 'https://github.com/t/t.git', 'project': project.id, 'token': 'secret-token',
        }, format='json')
        resp = admin_client.get('/api/v1/integrations/git-repositories/')
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert all('secret-token' not in str(item) for item in items)

    def test_default_branch(self, admin_client, make_project):
        """默认分支为 main"""
        project = make_project()
        resp = admin_client.post('/api/v1/integrations/git-repositories/', {
            'url': 'https://github.com/d/b.git', 'project': project.id,
        }, format='json')
        assert resp.status_code in (200, 201)
        repo = GitRepository.objects.get(url='https://github.com/d/b.git')
        assert repo.branch == 'main'

    @patch('apps.integrations.connection_services.socket.getaddrinfo')
    @patch('apps.integrations.connection_services.subprocess.run')
    def test_connection_and_sync_remote_branch(
        self, run_mock, address_mock, admin_client, make_project
    ):
        address_mock.return_value = [(None, None, None, None, ('140.82.112.4', 443))]
        commit = 'a' * 40
        run_mock.return_value = CompletedProcess(
            args=[], returncode=0,
            stdout=f'{commit}\trefs/heads/main\n', stderr='',
        )
        repository = GitRepository.objects.create(
            url='https://github.com/example/repository.git',
            branch='main', token='git-secret', project=make_project(),
        )

        checked = admin_client.post(
            f'/api/v1/integrations/git-repositories/{repository.id}/test-connection/'
        )
        synced = admin_client.post(
            f'/api/v1/integrations/git-repositories/{repository.id}/sync/'
        )

        assert checked.status_code == 200, checked.json()
        assert synced.status_code == 200, synced.json()
        repository.refresh_from_db()
        assert repository.connection_status == 'connected'
        assert repository.remote_commit == commit
        assert repository.last_synced_at is not None
        assert run_mock.call_args.kwargs['env']['GIT_CONFIG_VALUE_0'] == 'Authorization: Bearer git-secret'
