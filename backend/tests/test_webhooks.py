"""
P09: Webhook 配置管理测试
- WebhookConfig 模型（name/url/secret/is_active/events）
- CRUD 接口（仅系统管理员）
"""
import pytest

from apps.integrations.models import WebhookConfig


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


WEBHOOK_PAYLOAD = {
    'name': '测试 Webhook',
    'url': 'https://example.com/webhook',
    'secret': 'my-secret-token',
    'is_active': True,
    'events': ['task.overdue', 'project.closed'],
}


@pytest.mark.api
@pytest.mark.django_db
class TestWebhookModel:
    """WebhookConfig 模型测试"""

    def test_create_webhook_config(self):
        """模型可正常创建并保存字段"""
        config = WebhookConfig.objects.create(
            name='CI 通知',
            url='https://ci.example.com/hook',
            secret='abc123',
            is_active=True,
            events=['build.failed', 'build.success'],
        )
        assert config.pk is not None
        assert config.name == 'CI 通知'
        assert config.url == 'https://ci.example.com/hook'
        assert config.secret == 'abc123'
        assert config.is_active is True
        assert config.events == ['build.failed', 'build.success']

    def test_default_values(self):
        """默认值：is_active=True, events=[], secret=''"""
        config = WebhookConfig.objects.create(
            name='默认 Webhook',
            url='https://example.com/default',
        )
        assert config.is_active is True
        assert config.events == []
        assert config.secret == ''

    def test_str_representation(self):
        config = WebhookConfig.objects.create(
            name='展示名', url='https://example.com/str',
        )
        assert '展示名' in str(config)
        assert 'https://example.com/str' in str(config)

    def test_is_subscribed_all(self):
        """events 为空时视为订阅全部事件"""
        config = WebhookConfig.objects.create(
            name='全订阅', url='https://example.com/all',
        )
        assert config.is_subscribed_all is True
        config.events = ['task.overdue']
        assert config.is_subscribed_all is False


@pytest.mark.api
@pytest.mark.django_db
class TestWebhookCRUD:
    """Webhook 配置 CRUD 接口测试"""

    def test_admin_create_webhook(self, admin_client):
        """管理员可创建 Webhook 配置"""
        resp = admin_client.post('/api/v1/integrations/webhooks/', WEBHOOK_PAYLOAD, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['name'] == '测试 Webhook'
        assert data['url'] == 'https://example.com/webhook'
        assert data['secret'] == 'my-secret-token'
        assert data['is_active'] is True
        assert data['events'] == ['task.overdue', 'project.closed']
        assert 'id' in data

    def test_admin_list_webhooks(self, admin_client):
        """管理员可查看 Webhook 列表"""
        WebhookConfig.objects.create(name='W1', url='https://example.com/1')
        WebhookConfig.objects.create(name='W2', url='https://example.com/2', is_active=False)
        resp = admin_client.get('/api/v1/integrations/webhooks/')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) == 2

    def test_admin_retrieve_webhook(self, admin_client):
        """管理员可查看 Webhook 详情"""
        config = WebhookConfig.objects.create(
            name='详情', url='https://example.com/detail', events=['a.b'],
        )
        resp = admin_client.get(f'/api/v1/integrations/webhooks/{config.id}/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['name'] == '详情'
        assert data['events'] == ['a.b']

    def test_admin_update_webhook(self, admin_client):
        """管理员可更新 Webhook 配置"""
        config = WebhookConfig.objects.create(name='旧', url='https://example.com/old')
        resp = admin_client.patch(f'/api/v1/integrations/webhooks/{config.id}/', {
            'name': '新名称',
            'is_active': False,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        config.refresh_from_db()
        assert config.name == '新名称'
        assert config.is_active is False

    def test_admin_delete_webhook(self, admin_client):
        """管理员可删除 Webhook 配置"""
        config = WebhookConfig.objects.create(name='待删', url='https://example.com/del')
        resp = admin_client.delete(f'/api/v1/integrations/webhooks/{config.id}/')
        assert resp.status_code in (200, 204)
        assert not WebhookConfig.objects.filter(id=config.id).exists()

    def test_member_cannot_create_webhook(self, member_client):
        """普通成员无权创建 Webhook 配置"""
        resp = member_client.post('/api/v1/integrations/webhooks/', WEBHOOK_PAYLOAD, format='json')
        assert resp.status_code in (401, 403)

    def test_member_cannot_list_webhooks(self, member_client):
        """普通成员无权查看 Webhook 列表"""
        resp = member_client.get('/api/v1/integrations/webhooks/')
        assert resp.status_code in (401, 403)

    def test_filter_by_is_active(self, admin_client):
        """按 is_active 筛选"""
        WebhookConfig.objects.create(name='启用', url='https://example.com/on', is_active=True)
        WebhookConfig.objects.create(name='禁用', url='https://example.com/off', is_active=False)
        resp = admin_client.get('/api/v1/integrations/webhooks/?is_active=true')
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        assert all(r['is_active'] is True for r in results)
        assert len(results) == 1

    def test_create_with_empty_events(self, admin_client):
        """events 为空数组时视为订阅全部事件"""
        resp = admin_client.post('/api/v1/integrations/webhooks/', {
            'name': '全订阅',
            'url': 'https://example.com/all-events',
            'events': [],
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['events'] == []

    def test_invalid_url_rejected(self, admin_client):
        """非法 URL 被拒绝"""
        resp = admin_client.post('/api/v1/integrations/webhooks/', {
            'name': '非法',
            'url': 'not-a-url',
        }, format='json')
        assert resp.status_code in (400, 422)
