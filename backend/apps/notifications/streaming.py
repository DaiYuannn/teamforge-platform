"""通知实时流的 Redis 发布工具。"""
import json
import logging
from functools import lru_cache

import redis
from django.conf import settings

logger = logging.getLogger('apps.notifications')


def notification_channel(user_id):
    return f'team-management:notifications:user:{int(user_id)}'


def _stream_redis_url():
    return getattr(
        settings,
        'NOTIFICATION_STREAM_REDIS_URL',
        settings.CELERY_BROKER_URL,
    )


@lru_cache(maxsize=4)
def _redis_client(redis_url):
    """复用线程安全的 Redis 连接池，避免每条通知重新握手。"""
    return redis.Redis.from_url(
        redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
        health_check_interval=30,
    )


def _publish_events(events):
    """批量发布用户事件；失败不影响已经提交的业务事务。"""
    if not getattr(settings, 'NOTIFICATION_STREAM_ENABLED', True):
        return False
    prepared = [
        (notification_channel(user_id), json.dumps(payload, ensure_ascii=False))
        for user_id, payload in events
        if user_id
    ]
    if not prepared:
        return False
    try:
        client = _redis_client(_stream_redis_url())
        if len(prepared) == 1:
            channel, payload = prepared[0]
            client.publish(channel, payload)
        else:
            pipeline = client.pipeline(transaction=False)
            for channel, payload in prepared:
                pipeline.publish(channel, payload)
            pipeline.execute()
        return True
    except Exception as exc:
        logger.warning('发布实时通知失败，将由 SSE 重连补发: %s', exc)
        _redis_client.cache_clear()
        return False


def publish_notification(notification):
    """发布新通知唤醒事件；正文仍以数据库游标为准。"""
    if (
        not notification.recipient_id
        or notification.channel != 'inapp'
    ):
        return False
    return _publish_events([(
        notification.recipient_id,
        {
            'type': 'notification',
            'notification_id': notification.id,
        },
    )])


def publish_notifications(notifications):
    """用一个 Redis pipeline 发布一批新通知。"""
    return _publish_events([
        (
            notification.recipient_id,
            {
                'type': 'notification',
                'notification_id': notification.id,
            },
        )
        for notification in notifications
        if notification.recipient_id and notification.channel == 'inapp'
    ])


def publish_notification_state(
    user_id,
    *,
    notification_id=None,
    all_read=False,
    unread_count=None,
):
    """向同一账户的其他连接广播已读状态变化。"""
    payload = {
        'type': 'notification_state',
        'is_read': True,
        'all_read': bool(all_read),
    }
    if notification_id is not None:
        payload['notification_id'] = int(notification_id)
    if unread_count is not None:
        payload['unread_count'] = max(0, int(unread_count))
    return _publish_events([(user_id, payload)])
