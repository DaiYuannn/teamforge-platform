"""
N38: 备份与恢复测试（桩实现）
- GET  /api/v1/common/backup/
- POST /api/v1/common/backup/create/
- POST /api/v1/common/backup/<id>/restore/
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestBackup:
    """备份与恢复测试"""

    def test_list_backups(self, member_client):
        """列出备份（桩，返回空列表）"""
        resp = member_client.get('/api/v1/common/backup/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert 'backups' in data
        assert data['total'] == 0

    def test_create_backup(self, member_client):
        """触发备份（桩）"""
        resp = member_client.post('/api/v1/common/backup/create/', {}, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == 'stub'

    def test_restore_backup(self, member_client):
        """从备份恢复（桩）"""
        resp = member_client.post('/api/v1/common/backup/bkp-001/restore/', {}, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['backup_id'] == 'bkp-001'
        assert data['status'] == 'stub'

    def test_unauthenticated_list_blocked(self, api_client):
        """未认证不可列出备份"""
        resp = api_client.get('/api/v1/common/backup/')
        assert resp.status_code in (401, 403)

    def test_unauthenticated_create_blocked(self, api_client):
        """未认证不可触发备份"""
        resp = api_client.post('/api/v1/common/backup/create/', {}, format='json')
        assert resp.status_code in (401, 403)

    def test_restore_returns_success_message(self, member_client):
        """恢复返回成功消息"""
        resp = member_client.post('/api/v1/common/backup/bkp-002/restore/', {}, format='json')
        assert resp.status_code == 200
        body = resp.json()
        assert body.get('message')
