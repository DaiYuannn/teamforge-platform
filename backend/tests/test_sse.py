"""
SSE (Server-Sent Events) 实时通知推送测试
- 认证要求（未登录返回 401）
- 响应头（Content-Type / Cache-Control / X-Accel-Buffering）
- 初始连接事件（connected 事件）
- 广播通知服务（为所有活跃用户创建通知）

注意：SSE 流式推送使用 time.sleep 轮询，测试仅验证响应头和首个数据块，
不验证长时间流式行为（需要异步测试框架）。
"""
import json

import pytest

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService


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
            assert resp['Cache-Control'] == 'no-cache'
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
