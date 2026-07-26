"""
SSE (Server-Sent Events) 实时通知推送测试
- 认证要求（未登录返回 401）
- 响应头（Content-Type / Cache-Control / X-Accel-Buffering）
- 初始连接事件（connected 事件）
- 广播通知服务（为所有活跃用户创建通知）

测试环境关闭 Redis 长连接，只验证游标补发、响应头和首批数据块；
生产环境由 Redis Pub/Sub 唤醒连接，不做固定间隔数据库轮询。
"""
import json
from types import SimpleNamespace

import pytest

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.notifications.sse_views import (
    _decode_stream_message,
    _stream_access_error,
)
from apps.notifications import streaming
from apps.users.models import User


# ========== SSE 认证测试 ==========

@pytest.mark.api
@pytest.mark.django_db
class TestSSEAuthentication:
    """SSE 接口认证测试"""

    def test_sse_requires_auth(self, api_client):
        """未认证访问 SSE 返回 401"""
        resp = api_client.get('/api/v1/notifications/sse/')
        assert resp.status_code == 401

    def test_sse_invalid_token_rejected(self, api_client):
        """无效 token 访问 SSE 返回 401"""
        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_xyz')
        resp = api_client.get('/api/v1/notifications/sse/')
        assert resp.status_code == 401


# ========== SSE 响应头测试 ==========

@pytest.mark.api
@pytest.mark.django_db
class TestSSEResponseHeaders:
    """SSE 响应头测试"""

    def test_sse_accept_header_is_supported(self, member_client):
        """浏览器的 text/event-stream Accept 头不会触发 406。"""
        resp = member_client.get(
            '/api/v1/notifications/sse/',
            HTTP_ACCEPT='text/event-stream',
        )
        try:
            assert resp.status_code == 200
            assert 'text/event-stream' in resp['Content-Type']
        finally:
            resp.close()

    def test_sse_content_type(self, member_client):
        """SSE 返回 text/event-stream 内容类型"""
        resp = member_client.get('/api/v1/notifications/sse/')
        try:
            assert resp.status_code == 200
            assert 'text/event-stream' in resp['Content-Type']
        finally:
            resp.close()

    def test_sse_cache_control(self, member_client):
        """SSE 响应头 Cache-Control: no-cache"""
        resp = member_client.get('/api/v1/notifications/sse/')
        try:
            assert resp.status_code == 200
            assert 'no-cache' in resp['Cache-Control']
            assert 'no-transform' in resp['Cache-Control']
        finally:
            resp.close()

    def test_sse_x_accel_buffering(self, member_client):
        """SSE 响应头 X-Accel-Buffering: no（Nginx 关闭缓冲）"""
        resp = member_client.get('/api/v1/notifications/sse/')
        try:
            assert resp.status_code == 200
            assert resp['X-Accel-Buffering'] == 'no'
        finally:
            resp.close()

    def test_sse_is_streaming_response(self, member_client):
        """SSE 响应为流式响应"""
        resp = member_client.get('/api/v1/notifications/sse/')
        try:
            assert resp.status_code == 200
            assert resp.streaming is True
        finally:
            resp.close()


# ========== SSE 初始连接事件测试 ==========

@pytest.mark.api
@pytest.mark.django_db
class TestSSEInitialEvent:
    """SSE 初始连接事件测试（仅消费第一个数据块，避免触发 time.sleep）"""

    def test_sse_initial_connected_event(self, member_client):
        """SSE 初始连接发送 connected 事件"""
        resp = member_client.get('/api/v1/notifications/sse/')
        try:
            assert resp.status_code == 200
            # 只消费第一个数据块（connected 事件），不进入 while 循环
            first_chunk = next(resp.streaming_content)
            # StreamingHttpResponse.streaming_content 返回 bytes
            assert b'event: connected' in first_chunk
        finally:
            resp.close()

    def test_sse_connected_event_data_format(self, member_client):
        """SSE connected 事件数据格式正确"""
        resp = member_client.get('/api/v1/notifications/sse/')
        try:
            assert resp.status_code == 200
            first_chunk = next(resp.streaming_content).decode('utf-8')
            # 验证 SSE 格式: event: xxx\ndata: xxx\n\n
            assert first_chunk.startswith('event: connected\n')
            assert first_chunk.endswith('\n\n')
            # 提取 data 行并解析 JSON
            data_line = [line for line in first_chunk.strip().split('\n')
                         if line.startswith('data: ')][0]
            data = json.loads(data_line[len('data: '):])
            assert data['type'] == 'connected'
            assert 'message' in data
            assert 'SSE' in data['message']
        finally:
            resp.close()

    def test_sse_pushes_existing_notification(self, member_client):
        """SSE 连接后推送已有通知（第二个数据块为 notification 事件）"""
        # 先为当前用户创建一条通知
        Notification.objects.create(
            recipient=member_client.user,
            title='测试推送通知',
            content='这是通过 SSE 推送的通知内容',
            notification_type='system',
        )
        resp = member_client.get('/api/v1/notifications/sse/')
        try:
            assert resp.status_code == 200
            # 第一个数据块: connected 事件
            chunk1 = next(resp.streaming_content)
            assert b'event: connected' in chunk1
            # 第二个数据块: notification 事件（已有通知会被推送）
            chunk2 = next(resp.streaming_content)
            assert b'event: notification' in chunk2
            # 验证通知数据
            chunk2_str = chunk2.decode('utf-8')
            data_line = [line for line in chunk2_str.strip().split('\n')
                         if line.startswith('data: ')][0]
            data = json.loads(data_line[len('data: '):])
            assert data['type'] == 'notification'
            assert data['data']['title'] == '测试推送通知'
        finally:
            resp.close()

    def test_sse_honors_last_event_id_header(self, member_client):
        """断线重连只补发 Last-Event-ID 之后的站内通知。"""
        first = Notification.objects.create(
            recipient=member_client.user,
            title='已接收通知',
            content='不应重复补发',
            notification_type='system',
        )
        second = Notification.objects.create(
            recipient=member_client.user,
            title='待补发通知',
            content='应当补发',
            notification_type='system',
        )

        resp = member_client.get(
            '/api/v1/notifications/sse/',
            HTTP_LAST_EVENT_ID=str(first.id),
        )
        try:
            connected = next(resp.streaming_content).decode('utf-8')
            pushed = next(resp.streaming_content).decode('utf-8')

            assert f'id: {first.id}' in connected
            assert f'id: {second.id}' in pushed
            assert '待补发通知' in pushed
            assert '已接收通知' not in pushed
        finally:
            resp.close()


@pytest.mark.django_db
class TestSSEStreamReliability:
    def test_stream_access_rechecks_token_and_account_state(self, make_user):
        user = make_user(email='sse-access@test.com')

        assert _stream_access_error(user.pk, 100, now=100) == 'token_expired'
        assert _stream_access_error(user.pk, 200, now=100) is None

        user.is_active = False
        user.save(update_fields=['is_active'])
        assert _stream_access_error(user.pk, 200, now=100) == 'account_inactive'

        user.is_active = True
        user.membership_status = User.MembershipStatus.EXITED
        user.save(update_fields=['is_active', 'membership_status'])
        assert _stream_access_error(user.pk, 200, now=100) == 'account_inactive'

    def test_live_stream_closes_after_account_is_deactivated(
        self, member_client
    ):
        response = member_client.get('/api/v1/notifications/sse/')
        try:
            connected = next(response.streaming_content).decode('utf-8')
            member_client.user.is_active = False
            member_client.user.save(update_fields=['is_active'])
            closed = next(response.streaming_content).decode('utf-8')

            assert 'event: connected' in connected
            assert 'event: stream_closed' in closed
            assert 'account_inactive' in closed
        finally:
            response.close()

    def test_live_stream_closes_after_token_expires(
        self, member_client, monkeypatch
    ):
        response = member_client.get('/api/v1/notifications/sse/')
        try:
            connected = next(response.streaming_content).decode('utf-8')
            monkeypatch.setattr(
                'apps.notifications.sse_views.time.time',
                lambda: 10**12,
            )
            closed = next(response.streaming_content).decode('utf-8')

            assert 'event: connected' in connected
            assert 'event: stream_closed' in closed
            assert 'token_expired' in closed
        finally:
            response.close()

    def test_stream_message_decoder_supports_json_and_legacy_ids(self):
        state = _decode_stream_message({
            'data': json.dumps({
                'type': 'notification_state',
                'all_read': True,
                'unread_count': 0,
            }).encode('utf-8'),
        })
        legacy = _decode_stream_message({'data': b'42'})

        assert state['type'] == 'notification_state'
        assert state['all_read'] is True
        assert legacy == {'type': 'notification', 'notification_id': 42}

    def test_redis_failure_keeps_stream_and_uses_database_fallback(
        self, member_client, settings, monkeypatch
    ):
        settings.NOTIFICATION_STREAM_ENABLED = True
        settings.NOTIFICATION_STREAM_FALLBACK_POLL_SECONDS = 1
        Notification.objects.create(
            recipient=member_client.user,
            title='Redis 故障补偿通知',
            content='仍应从数据库发送',
        )

        def unavailable(*args, **kwargs):
            raise ConnectionError('redis unavailable')

        monkeypatch.setattr(
            'apps.notifications.sse_views.redis.Redis.from_url',
            unavailable,
        )
        response = member_client.get('/api/v1/notifications/sse/')
        try:
            connected = next(response.streaming_content).decode('utf-8')
            notification = next(response.streaming_content).decode('utf-8')
            fallback = next(response.streaming_content).decode('utf-8')

            assert 'event: connected' in connected
            assert 'event: notification' in notification
            assert 'Redis 故障补偿通知' in notification
            assert 'event: fallback' in fallback
            assert 'unread_count' in fallback
        finally:
            response.close()

    def test_redis_failure_catches_notification_created_during_outage(
        self, member_client, settings, monkeypatch
    ):
        settings.NOTIFICATION_STREAM_ENABLED = True
        settings.NOTIFICATION_STREAM_FALLBACK_POLL_SECONDS = 1

        def unavailable(*args, **kwargs):
            raise ConnectionError('redis unavailable')

        created = False

        def create_while_waiting(seconds):
            nonlocal created
            assert seconds == 1
            if created:
                return
            created = True
            Notification.objects.create(
                recipient=member_client.user,
                title='故障期间到达的通知',
                content='下一轮数据库补偿应发送',
            )

        monkeypatch.setattr(
            'apps.notifications.sse_views.redis.Redis.from_url',
            unavailable,
        )
        monkeypatch.setattr(
            'apps.notifications.sse_views.time.sleep',
            create_while_waiting,
        )
        response = member_client.get('/api/v1/notifications/sse/')
        try:
            connected = next(response.streaming_content).decode('utf-8')
            fallback = next(response.streaming_content).decode('utf-8')
            notification = next(response.streaming_content).decode('utf-8')

            assert 'event: connected' in connected
            assert 'event: fallback' in fallback
            assert 'event: notification' in notification
            assert '故障期间到达的通知' in notification
        finally:
            response.close()

    def test_batch_publish_reuses_one_pipeline(self, settings, monkeypatch):
        settings.NOTIFICATION_STREAM_ENABLED = True

        class FakePipeline:
            def __init__(self):
                self.published = []
                self.execute_count = 0

            def publish(self, channel, payload):
                self.published.append((channel, json.loads(payload)))
                return self

            def execute(self):
                self.execute_count += 1

        class FakeClient:
            def __init__(self):
                self.pipeline_count = 0
                self.pipeline_instance = FakePipeline()

            def pipeline(self, transaction=False):
                assert transaction is False
                self.pipeline_count += 1
                return self.pipeline_instance

        client = FakeClient()
        monkeypatch.setattr(streaming, '_redis_client', lambda url: client)
        notifications = [
            SimpleNamespace(id=1, recipient_id=10, channel='inapp'),
            SimpleNamespace(id=2, recipient_id=11, channel='inapp'),
        ]

        assert streaming.publish_notifications(notifications) is True
        assert client.pipeline_count == 1
        assert client.pipeline_instance.execute_count == 1
        assert len(client.pipeline_instance.published) == 2


# ========== 广播通知服务测试 ==========

@pytest.mark.django_db
class TestBroadcast:
    """NotificationService.broadcast 广播通知测试"""

    def test_broadcast_creates_for_all_active_users(self, make_user):
        """广播通知为所有活跃用户创建通知"""
        user1 = make_user(email='b1@test.com', name='用户1')
        user2 = make_user(email='b2@test.com', name='用户2')
        user3 = make_user(email='b3@test.com', name='用户3')

        count = NotificationService.broadcast(
            title='系统广播通知',
            content='这是一条广播消息',
            category='system',
            priority='normal',
        )

        assert count == 3
        # 每个活跃用户都收到 1 条通知
        assert Notification.objects.filter(recipient=user1).count() == 1
        assert Notification.objects.filter(recipient=user2).count() == 1
        assert Notification.objects.filter(recipient=user3).count() == 1

    def test_broadcast_excludes_inactive_users(self, make_user):
        """广播通知不为非活跃用户创建通知"""
        active_user = make_user(email='active@test.com', name='活跃用户')
        inactive_user = make_user(email='inactive@test.com', name='非活跃用户')
        inactive_user.is_active = False
        inactive_user.save()

        count = NotificationService.broadcast(
            title='广播测试',
            content='内容',
        )

        assert count == 1
        assert Notification.objects.filter(recipient=active_user).count() == 1
        assert Notification.objects.filter(recipient=inactive_user).count() == 0

    def test_broadcast_returns_correct_count(self, make_user):
        """广播返回创建的通知数量等于活跃用户数"""
        for i in range(5):
            make_user(email=f'count_{i}@test.com', name=f'用户{i}')

        count = NotificationService.broadcast(
            title='计数测试',
            content='内容',
        )
        assert count == 5

    def test_broadcast_notification_content(self, make_user):
        """广播通知内容正确"""
        user = make_user(email='content@test.com', name='内容用户')

        NotificationService.broadcast(
            title='标题测试',
            content='内容测试',
            category='project',
            priority='high',
        )

        notif = Notification.objects.filter(recipient=user).first()
        assert notif is not None
        assert notif.title == '标题测试'
        assert notif.content == '内容测试'
        assert notif.notification_type == 'project'
        assert notif.priority == 'high'

    def test_broadcast_with_sender(self, make_user):
        """广播通知可指定发送人"""
        sender = make_user(email='sender@test.com', name='发送人', global_role='teacher')
        recipient = make_user(email='recipient@test.com', name='接收人')

        NotificationService.broadcast(
            title='带发送人的广播',
            content='内容',
            sender=sender,
        )

        notif = Notification.objects.filter(recipient=recipient).first()
        assert notif is not None
        assert notif.sender == sender

    def test_broadcast_no_active_users(self):
        """无活跃用户时广播返回 0"""
        count = NotificationService.broadcast(
            title='空广播',
            content='内容',
        )
        assert count == 0

    def test_broadcast_default_category_and_priority(self, make_user):
        """广播通知默认类型为 system，优先级为 normal"""
        user = make_user(email='default@test.com', name='默认用户')

        NotificationService.broadcast(
            title='默认值测试',
            content='内容',
        )

        notif = Notification.objects.filter(recipient=user).first()
        assert notif is not None
        assert notif.notification_type == 'system'
        assert notif.priority == 'normal'
