"""
P15 通知中心增强测试
- notification_type 筛选
- delete 删除单条通知
- clear_all 清空已读通知
- delete_read 删除已读通知
"""
import pytest

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService


def extract_data(response):
    """从统一响应格式中提取 data"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


def get_results(data):
    """从分页或非分页数据中提取结果列表"""
    if isinstance(data, dict):
        return data.get('results', data)
    return data


@pytest.fixture
def make_notification(db, make_user):
    """创建通知的工厂函数（直接操作模型）"""
    counter = [0]

    def _make(
        recipient=None,
        title=None,
        content='通知内容',
        notification_type=Notification.NotificationType.SYSTEM,
        is_read=False,
        sender=None,
        **extra,
    ):
        counter[0] += 1
        recipient = recipient or make_user(
            email=f'notif_user{counter[0]}@test.com',
            name=f'通知用户{counter[0]}',
        )
        return Notification.objects.create(
            recipient=recipient,
            sender=sender,
            title=title or f'通知标题{counter[0]}',
            content=content,
            notification_type=notification_type,
            is_read=is_read,
            **extra,
        )

    return _make


@pytest.mark.api
@pytest.mark.django_db
class TestNotificationTypeFilter:
    """通知类型筛选测试"""

    def test_filter_by_notification_type(self, auth_client, make_notification):
        """通过 notification_type 参数筛选"""
        user = auth_client.user
        make_notification(recipient=user, title='系统通知', notification_type=Notification.NotificationType.SYSTEM)
        make_notification(recipient=user, title='项目通知', notification_type=Notification.NotificationType.PROJECT)

        resp = auth_client.get('/api/v1/notifications/', {'notification_type': 'project'})
        assert resp.status_code == 200
        titles = [n['title'] for n in get_results(extract_data(resp))]
        assert '项目通知' in titles
        assert '系统通知' not in titles

    def test_filter_by_category_alias(self, auth_client, make_notification):
        """category 参数（兼容旧名）同样按 notification_type 筛选"""
        user = auth_client.user
        make_notification(recipient=user, title='任务通知', notification_type=Notification.NotificationType.TASK)
        make_notification(recipient=user, title='系统通知2', notification_type=Notification.NotificationType.SYSTEM)

        resp = auth_client.get('/api/v1/notifications/', {'category': 'task'})
        assert resp.status_code == 200
        titles = [n['title'] for n in get_results(extract_data(resp))]
        assert '任务通知' in titles
        assert '系统通知2' not in titles

    def test_filter_by_is_read(self, auth_client, make_notification):
        """按 is_read 筛选"""
        user = auth_client.user
        make_notification(recipient=user, title='未读', is_read=False)
        make_notification(recipient=user, title='已读', is_read=True)

        resp = auth_client.get('/api/v1/notifications/', {'is_read': 'false'})
        assert resp.status_code == 200
        titles = [n['title'] for n in get_results(extract_data(resp))]
        assert '未读' in titles
        assert '已读' not in titles

    def test_only_own_notifications(self, auth_client, make_notification, make_user):
        """仅返回当前用户自己的通知"""
        user = auth_client.user
        other = make_user(email='other_notif@test.com', name='其他人')
        make_notification(recipient=user, title='我的通知')
        make_notification(recipient=other, title='别人的通知')

        resp = auth_client.get('/api/v1/notifications/')
        assert resp.status_code == 200
        titles = [n['title'] for n in get_results(extract_data(resp))]
        assert '我的通知' in titles
        assert '别人的通知' not in titles


@pytest.mark.api
@pytest.mark.django_db
class TestNotificationDelete:
    """删除单条通知测试"""

    def test_delete_notification_via_post(self, auth_client, make_notification):
        """POST 删除单条通知"""
        user = auth_client.user
        n = make_notification(recipient=user, title='待删除')
        resp = auth_client.post(f'/api/v1/notifications/{n.id}/delete/')
        assert resp.status_code == 200
        assert not Notification.objects.filter(id=n.id).exists()

    def test_delete_notification_via_delete_method(self, auth_client, make_notification):
        """DELETE 方法删除单条通知"""
        user = auth_client.user
        n = make_notification(recipient=user, title='DELETE方法')
        resp = auth_client.delete(f'/api/v1/notifications/{n.id}/delete/')
        assert resp.status_code == 200
        assert not Notification.objects.filter(id=n.id).exists()

    def test_delete_other_user_notification_not_found(self, auth_client, make_notification, make_user):
        """不能删除别人的通知（404）"""
        other = make_user(email='other_del@test.com', name='他人')
        n = make_notification(recipient=other, title='他人的通知')
        resp = auth_client.post(f'/api/v1/notifications/{n.id}/delete/')
        assert resp.status_code == 404
        assert Notification.objects.filter(id=n.id).exists()

    def test_delete_requires_auth(self, api_client, make_notification):
        """未登录不可删除"""
        n = make_notification(title='通知')
        resp = api_client.post(f'/api/v1/notifications/{n.id}/delete/')
        assert resp.status_code == 401


@pytest.mark.api
@pytest.mark.django_db
class TestNotificationClearAll:
    """清空已读通知测试"""

    def test_clear_all_deletes_read_only(self, auth_client, make_notification):
        """clear_all 仅删除已读通知，保留未读"""
        user = auth_client.user
        make_notification(recipient=user, title='已读1', is_read=True)
        make_notification(recipient=user, title='已读2', is_read=True)
        make_notification(recipient=user, title='未读1', is_read=False)

        resp = auth_client.post('/api/v1/notifications/clear_all/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['count'] == 2

        remaining = Notification.objects.filter(recipient=user)
        assert remaining.count() == 1
        assert remaining.first().is_read is False

    def test_clear_all_no_read_returns_zero(self, auth_client, make_notification):
        """没有已读通知时返回 0"""
        user = auth_client.user
        make_notification(recipient=user, title='未读', is_read=False)
        resp = auth_client.post('/api/v1/notifications/clear_all/')
        assert resp.status_code == 200
        assert extract_data(resp)['count'] == 0

    def test_clear_all_requires_auth(self, api_client):
        """未登录不可清空"""
        resp = api_client.post('/api/v1/notifications/clear_all/')
        assert resp.status_code == 401


@pytest.mark.api
@pytest.mark.django_db
class TestNotificationDeleteRead:
    """删除已读通知测试"""

    def test_delete_read_deletes_read_only(self, auth_client, make_notification):
        """delete_read 仅删除已读通知"""
        user = auth_client.user
        make_notification(recipient=user, title='已读A', is_read=True)
        make_notification(recipient=user, title='已读B', is_read=True)
        make_notification(recipient=user, title='未读A', is_read=False)

        resp = auth_client.post('/api/v1/notifications/delete_read/')
        assert resp.status_code == 200
        assert extract_data(resp)['count'] == 2

        remaining = Notification.objects.filter(recipient=user)
        assert remaining.count() == 1
        assert remaining.first().is_read is False

    def test_delete_read_does_not_affect_others(self, auth_client, make_notification, make_user):
        """delete_read 不影响其他用户的已读通知"""
        user = auth_client.user
        other = make_user(email='other_dr@test.com', name='他人')
        make_notification(recipient=user, title='我的已读', is_read=True)
        make_notification(recipient=other, title='他人已读', is_read=True)

        resp = auth_client.post('/api/v1/notifications/delete_read/')
        assert resp.status_code == 200
        assert extract_data(resp)['count'] == 1
        # 他人已读通知仍在
        assert Notification.objects.filter(recipient=other, is_read=True).exists()


@pytest.mark.api
@pytest.mark.django_db
class TestNotificationCenterIntegration:
    """通知中心集成流程"""

    def test_mark_read_then_delete_read(self, auth_client, make_notification):
        """标记已读后清空已读"""
        user = auth_client.user
        n1 = make_notification(recipient=user, title='N1', is_read=False)
        n2 = make_notification(recipient=user, title='N2', is_read=False)

        # 标记全部已读
        NotificationService.mark_all_as_read(user)
        assert Notification.objects.filter(recipient=user, is_read=False).count() == 0

        # 未读数量应为 0
        resp = auth_client.get('/api/v1/notifications/unread_count/')
        assert resp.status_code == 200
        assert extract_data(resp)['count'] == 0

        # 清空已读
        resp = auth_client.post('/api/v1/notifications/clear_all/')
        assert resp.status_code == 200
        assert extract_data(resp)['count'] == 2
        assert Notification.objects.filter(recipient=user).count() == 0
        # 引用避免未使用告警
        assert n1.id and n2.id


@pytest.mark.django_db(transaction=True)
class TestNotificationReadStateBroadcast:
    def test_mark_as_read_publishes_account_state(
        self, make_user, make_notification, monkeypatch
    ):
        user = make_user(email='read-state@test.com')
        notification = make_notification(recipient=user, is_read=False)
        calls = []
        monkeypatch.setattr(
            'apps.notifications.streaming.publish_notification_state',
            lambda user_id, **payload: calls.append((user_id, payload)),
        )

        success, _ = NotificationService.mark_as_read(notification.pk, user)

        assert success is True
        assert calls == [(user.pk, {
            'notification_id': notification.pk,
            'unread_count': 0,
        })]

    def test_mark_all_as_read_publishes_zero_unread_count(
        self, make_user, make_notification, monkeypatch
    ):
        user = make_user(email='all-read-state@test.com')
        make_notification(recipient=user, is_read=False)
        make_notification(recipient=user, is_read=False)
        calls = []
        monkeypatch.setattr(
            'apps.notifications.streaming.publish_notification_state',
            lambda user_id, **payload: calls.append((user_id, payload)),
        )

        count = NotificationService.mark_all_as_read(user)

        assert count == 2
        assert calls == [(user.pk, {'all_read': True, 'unread_count': 0})]
