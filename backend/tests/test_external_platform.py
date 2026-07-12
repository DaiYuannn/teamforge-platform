"""
N44: 外部平台集成测试
- /api/v1/integrations/external-platforms/   外部平台 CRUD
"""
import pytest

from apps.integrations.external_models import ExternalPlatform


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestExternalPlatform:
    """外部平台集成测试"""

    def test_create_platform(self, admin_client):
        """管理员创建外部平台"""
        resp = admin_client.post('/api/v1/integrations/external-platforms/', {
            'name': '钉钉', 'platform_type': 'dingtalk',
            'api_url': 'https://oapi.dingtalk.com', 'api_key': 'secret',
            'config': {'app_key': 'xxx'},
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        p = ExternalPlatform.objects.get(name='钉钉')
        assert p.platform_type == 'dingtalk'
        assert p.is_active is True

    def test_list_platforms(self, admin_client):
        """列出外部平台"""
        ExternalPlatform.objects.create(name='Jira', platform_type='jira')
        resp = admin_client.get('/api/v1/integrations/external-platforms/')
        assert resp.status_code == 200
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        assert any(p['name'] == 'Jira' for p in items)

    def test_member_cannot_create(self, member_client):
        """普通成员不能创建"""
        resp = member_client.post('/api/v1/integrations/external-platforms/', {
            'name': '越权', 'platform_type': 'x',
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_member_can_list(self, member_client):
        """普通成员可查看"""
        ExternalPlatform.objects.create(name='可读', platform_type='x')
        resp = member_client.get('/api/v1/integrations/external-platforms/')
        assert resp.status_code == 200

    def test_update_platform(self, admin_client):
        """更新外部平台"""
        p = ExternalPlatform.objects.create(name='待更新', platform_type='x')
        resp = admin_client.patch(f'/api/v1/integrations/external-platforms/{p.id}/', {
            'is_active': False,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        p.refresh_from_db()
        assert p.is_active is False

    def test_delete_platform(self, admin_client):
        """删除外部平台"""
        p = ExternalPlatform.objects.create(name='待删除', platform_type='x')
        resp = admin_client.delete(f'/api/v1/integrations/external-platforms/{p.id}/')
        assert resp.status_code in (200, 204)
        assert not ExternalPlatform.objects.filter(id=p.id).exists()

    def test_api_key_write_only(self, admin_client):
        """api_key 仅写不读"""
        admin_client.post('/api/v1/integrations/external-platforms/', {
            'name': '密钥测试', 'platform_type': 'x', 'api_key': 'topsecret',
        }, format='json')
        resp = admin_client.get('/api/v1/integrations/external-platforms/')
        data = extract_data(resp)
        items = data.get('results', data) if isinstance(data, dict) else data
        # 返回数据不应包含明文 api_key
        assert all('topsecret' not in str(item) for item in items)
