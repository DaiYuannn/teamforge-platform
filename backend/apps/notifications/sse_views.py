"""基于 Redis Pub/Sub 的 SSE 实时通知推送。"""
import json
import logging
import time

import redis
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationListSerializer
from .streaming import notification_channel

logger = logging.getLogger('apps.notifications')


class EventStreamRenderer(BaseRenderer):
    """让 DRF 接受浏览器发送的 text/event-stream Accept 头。"""

    media_type = 'text/event-stream'
    format = 'event-stream'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode(self.charset)
        return json.dumps(data, ensure_ascii=False, default=str).encode(self.charset)


def _format_event(event, data, event_id=None):
    lines = [f'event: {event}']
    if event_id is not None:
        lines.append(f'id: {event_id}')
    lines.append(f'data: {json.dumps(data, ensure_ascii=False, default=str)}')
    return '\n'.join(lines) + '\n\n'


def _token_expiration(auth):
    """从 SimpleJWT token 或兼容映射中提取 Unix 过期时间。"""
    try:
        value = auth.get('exp')
        return int(value) if value is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def _stream_access_error(user_id, token_expires_at, now=None):
    """长连接期间重新确认令牌和账户仍然有效。"""
    current_timestamp = time.time() if now is None else float(now)
    if token_expires_at is not None and current_timestamp >= token_expires_at:
        return 'token_expired'

    from apps.users.models import User

    active = User.objects.filter(pk=user_id, is_active=True).exclude(
        membership_status=User.MembershipStatus.EXITED,
    ).exists()
    return None if active else 'account_inactive'


def _decode_stream_message(message):
    """兼容旧版纯通知 ID 和新版 JSON 事件。"""
    raw = message.get('data') if isinstance(message, dict) else None
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        return payload
    try:
        return {'type': 'notification', 'notification_id': int(raw)}
    except (TypeError, ValueError):
        return {'type': 'notification'}


class NotificationSSEView(APIView):
    """
    Redis 事件唤醒 + 数据库游标补发。

    每条连接不再按固定间隔查询数据库；新通知由 Redis Pub/Sub 唤醒。
    断线重连时使用 last_id 做一次数据库补发，兼顾实时性与可靠性。
    """

    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer, EventStreamRenderer]

    def get(self, request):
        requested_last_id = (
            request.query_params.get('last_id')
            or request.headers.get('Last-Event-ID')
        )
        try:
            requested_last_id = int(requested_last_id) if requested_last_id else 0
        except (TypeError, ValueError):
            requested_last_id = 0
        user_id = request.user.id
        token_expires_at = _token_expiration(request.auth)

        def pending_notifications(last_id):
            return list(
                Notification.objects.filter(
                    recipient_id=user_id,
                    channel=Notification.Channel.INAPP,
                    id__gt=last_id,
                )
                .select_related('recipient', 'sender')
                .order_by('id')[:100]
            )

        def event_stream():
            last_id = requested_last_id
            yield _format_event(
                'connected',
                {
                    'type': 'connected',
                    'message': 'SSE连接成功',
                    'last_id': last_id,
                    'transport': 'redis-pubsub',
                },
                event_id=last_id,
            )

            redis_url = getattr(
                settings,
                'NOTIFICATION_STREAM_REDIS_URL',
                settings.CELERY_BROKER_URL,
            )
            client = None
            pubsub = None

            def close_event(reason):
                messages = {
                    'token_expired': '登录凭证已过期，请重新登录',
                    'account_inactive': '账户已停用或退出团队',
                }
                return _format_event(
                    'stream_closed',
                    {
                        'type': 'stream_closed',
                        'reason': reason,
                        'message': messages[reason],
                        'last_id': last_id,
                    },
                    event_id=last_id,
                )

            def access_error():
                return _stream_access_error(
                    user_id,
                    token_expires_at,
                )

            def unread_count():
                return Notification.objects.filter(
                    recipient_id=user_id,
                    channel=Notification.Channel.INAPP,
                    is_read=False,
                ).count()

            def catch_up():
                """分批补发游标后的站内通知；访问失效时立即终止。"""
                nonlocal last_id
                while True:
                    reason = access_error()
                    if reason:
                        yield close_event(reason)
                        return False
                    batch = pending_notifications(last_id)
                    for notification in batch:
                        reason = access_error()
                        if reason:
                            yield close_event(reason)
                            return False
                        last_id = notification.id
                        yield _format_event(
                            'notification',
                            {
                                'type': 'notification',
                                'data': NotificationListSerializer(notification).data,
                            },
                            event_id=notification.id,
                        )
                    if len(batch) < 100:
                        return True

            if not getattr(settings, 'NOTIFICATION_STREAM_ENABLED', True):
                yield from catch_up()
                return

            heartbeat_seconds = max(
                1,
                int(getattr(settings, 'NOTIFICATION_STREAM_HEARTBEAT_SECONDS', 15)),
            )
            fallback_seconds = max(
                1,
                int(getattr(settings, 'NOTIFICATION_STREAM_FALLBACK_POLL_SECONDS', 5)),
            )

            while True:
                reason = access_error()
                if reason:
                    yield close_event(reason)
                    return
                try:
                    client = redis.Redis.from_url(
                        redis_url,
                        socket_connect_timeout=3,
                        socket_timeout=heartbeat_seconds + 5,
                        health_check_interval=30,
                    )
                    pubsub = client.pubsub(ignore_subscribe_messages=True)
                    # 先订阅再补发，封住数据库补发与订阅之间的竞态。
                    pubsub.subscribe(notification_channel(user_id))
                    caught_up = yield from catch_up()
                    if not caught_up:
                        return

                    while True:
                        message = pubsub.get_message(timeout=heartbeat_seconds)
                        reason = access_error()
                        if reason:
                            yield close_event(reason)
                            return
                        if message is None:
                            yield _format_event(
                                'heartbeat',
                                {
                                    'type': 'heartbeat',
                                    'time': int(time.time()),
                                    'unread_count': unread_count(),
                                },
                                event_id=last_id,
                            )
                            continue

                        payload = _decode_stream_message(message)
                        if payload.get('type') == 'notification_state':
                            yield _format_event(
                                'notification_state',
                                payload,
                                event_id=last_id,
                            )
                        else:
                            # Pub/Sub 只负责唤醒；按游标读取避免丢失和重复。
                            caught_up = yield from catch_up()
                            if not caught_up:
                                return
                except GeneratorExit:
                    raise
                except Exception as exc:
                    logger.warning('SSE Redis 连接中断，切换数据库补偿: %s', exc)
                    # 故障期间保持 SSE 连接，数据库游标补发后再尝试恢复 Redis。
                    caught_up = yield from catch_up()
                    if not caught_up:
                        return
                    reason = access_error()
                    if reason:
                        yield close_event(reason)
                        return
                    yield _format_event(
                        'fallback',
                        {
                            'type': 'fallback',
                            'message': '实时通道暂不可用，已切换数据库补偿',
                            'last_id': last_id,
                            'unread_count': unread_count(),
                        },
                        event_id=last_id,
                    )
                    time.sleep(fallback_seconds)
                finally:
                    if pubsub is not None:
                        try:
                            pubsub.close()
                        except Exception:
                            pass
                        pubsub = None
                    if client is not None:
                        try:
                            client.close()
                        except Exception:
                            pass
                        client = None

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache, no-transform'
        response['X-Accel-Buffering'] = 'no'
        return response
