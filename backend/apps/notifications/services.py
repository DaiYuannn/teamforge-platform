"""
通知服务
封装通知创建、发送、批量操作等业务逻辑
"""
import logging
from datetime import time

from django.db import transaction
from django.utils import timezone

from apps.users.models import User
from .models import Notification
from .email_service import send_notification_email

logger = logging.getLogger('apps.notifications')


def _preference_enabled(config, key, default=True):
    """兼容对象开关与数组白名单两种偏好结构。"""
    if isinstance(config, dict):
        value = config.get(key, default)
        return value if isinstance(value, bool) else default
    if isinstance(config, (list, tuple, set)):
        return key in config
    return default


def _parse_clock(value):
    try:
        hours, minutes = str(value).split(':', 1)
        return time(hour=int(hours), minute=int(minutes))
    except (TypeError, ValueError):
        return None


def _inside_quiet_hours(quiet_hours, now=None):
    if not isinstance(quiet_hours, dict) or quiet_hours.get('enabled', True) is False:
        return False
    start = _parse_clock(quiet_hours.get('start'))
    end = _parse_clock(quiet_hours.get('end'))
    if start is None or end is None or start == end:
        return False
    local_now = timezone.localtime(now or timezone.now()).time().replace(second=0, microsecond=0)
    if start < end:
        return start <= local_now < end
    return local_now >= start or local_now < end


def should_notify_user(
    user,
    category=Notification.NotificationType.SYSTEM,
    channel=Notification.Channel.INAPP,
    priority=Notification.Priority.NORMAL,
    now=None,
):
    """
    统一判断账户是否接收某类别/渠道的通知。

    站内通知是可追溯记录，免打扰时段仍会写入通知中心；邮件和 Webhook
    在免打扰时段暂停。高/紧急通知可穿透免打扰，但仍尊重类别和渠道关闭。
    """
    if user is None or not getattr(user, 'is_active', False):
        return False
    try:
        preference = user.preference
        settings = preference.notification_preferences or {}
    except Exception:
        settings = {}

    categories = settings.get('categories', {})
    channels = settings.get('channels', {})
    category_key = {
        Notification.NotificationType.IP: 'approval',
        Notification.NotificationType.SENSITIVE: 'approval',
        Notification.NotificationType.ANNOUNCEMENT: 'system',
    }.get(str(category), str(category))
    if not _preference_enabled(categories, category_key, default=True):
        return False
    channel_key = str(channel)
    if (
        channel_key == Notification.Channel.INAPP
        and isinstance(channels, dict)
        and 'inapp' not in channels
        and 'in_app' in channels
    ):
        channel_key = 'in_app'
    if not _preference_enabled(channels, channel_key, default=True):
        return False
    if (
        channel != Notification.Channel.INAPP
        and priority not in [Notification.Priority.HIGH, Notification.Priority.URGENT]
        and _inside_quiet_hours(settings.get('quiet_hours', {}), now=now)
    ):
        return False
    return True


def notification_digest_frequency(user):
    """返回账户选择的邮件频率；非法或缺失值按即时发送处理。"""
    try:
        value = (user.preference.notification_preferences or {}).get(
            'digest', 'instant'
        )
    except Exception:
        value = 'instant'
    return value if value in {'instant', 'daily', 'weekly'} else 'instant'


class NotificationService:
    """
    通知服务类
    提供站内通知创建、邮件发送、批量通知等静态方法
    """

    @staticmethod
    def create_notification(
        recipient,
        title,
        content,
        category=Notification.NotificationType.SYSTEM,
        ref_type='',
        ref_id=None,
        sender=None,
        priority=Notification.Priority.NORMAL,
        channel=Notification.Channel.INAPP,
    ):
        """
        创建站内通知
        :param recipient: 接收人（User 实例或 ID）
        :param title: 通知标题
        :param content: 通知内容
        :param category: 通知类型（system/project/task/finance/competition/announcement）
        :param ref_type: 关联对象类型
        :param ref_id: 关联对象 ID
        :param sender: 发送人（User 实例或 ID，可为空）
        :param priority: 优先级（low/normal/high/urgent）
        :param channel: 通知渠道（inapp/email/webhook）
        :return: Notification 实例
        """
        try:
            # 支持传入 User 实例或 ID
            if isinstance(recipient, int):
                recipient = User.objects.get(id=recipient)
            if isinstance(sender, int):
                sender = User.objects.get(id=sender)
            if not should_notify_user(
                recipient,
                category=category,
                channel=channel,
                priority=priority,
            ):
                return None

            notification = Notification.objects.create(
                recipient=recipient,
                sender=sender,
                title=title,
                content=content,
                notification_type=category,
                priority=priority,
                channel=channel,
                related_object_type=ref_type,
                related_object_id=ref_id,
            )
            return notification
        except Exception as e:
            logger.exception('创建站内通知失败: %s', e)
            return None

    @staticmethod
    def create_and_send_email(
        recipient,
        title,
        content,
        category=Notification.NotificationType.SYSTEM,
        ref_type='',
        ref_id=None,
        sender=None,
        priority=Notification.Priority.NORMAL,
    ):
        """
        创建站内通知并发送邮件
        :param recipient: 接收人（User 实例或 ID）
        :param title: 通知标题
        :param content: 通知内容
        :param category: 通知类型
        :param ref_type: 关联对象类型
        :param ref_id: 关联对象 ID
        :param sender: 发送人
        :param priority: 优先级
        :return: (Notification 实例, 邮件是否发送成功)
        """
        try:
            if isinstance(recipient, int):
                recipient = User.objects.get(id=recipient)
        except Exception:
            return None, False

        email_allowed = should_notify_user(
            recipient,
            category=category,
            channel=Notification.Channel.EMAIL,
            priority=priority,
        )
        inapp_allowed = should_notify_user(
            recipient,
            category=category,
            channel=Notification.Channel.INAPP,
            priority=priority,
        )
        if not email_allowed and not inapp_allowed:
            return None, False

        digest = notification_digest_frequency(recipient)
        queue_for_digest = (
            email_allowed
            and bool(recipient.email)
            and digest in {'daily', 'weekly'}
            and priority not in [
                Notification.Priority.HIGH,
                Notification.Priority.URGENT,
            ]
        )
        if queue_for_digest:
            email_status = Notification.EmailDeliveryStatus.QUEUED
        elif email_allowed and recipient.email:
            email_status = Notification.EmailDeliveryStatus.NOT_REQUESTED
        else:
            email_status = Notification.EmailDeliveryStatus.SUPPRESSED

        notification = Notification.objects.create(
            recipient=recipient,
            sender=sender,
            title=title,
            content=content,
            notification_type=category,
            priority=priority,
            channel=(
                Notification.Channel.INAPP
                if inapp_allowed
                else Notification.Channel.EMAIL
            ),
            related_object_type=ref_type,
            related_object_id=ref_id,
            email_delivery_status=email_status,
            email_digest_frequency=digest if queue_for_digest else '',
        )

        if queue_for_digest or not email_allowed or not recipient.email:
            return notification, False

        attempted_at = timezone.now()
        email_sent = send_notification_email(recipient.email, title, content)
        notification.email_attempted_at = attempted_at
        notification.email_delivery_status = (
            Notification.EmailDeliveryStatus.SENT
            if email_sent
            else Notification.EmailDeliveryStatus.FAILED
        )
        notification.email_sent_at = attempted_at if email_sent else None
        notification.email_delivery_error = (
            '' if email_sent else '邮件服务未配置或发送失败，请检查服务端邮件日志'
        )
        notification.save(update_fields=[
            'email_attempted_at',
            'email_delivery_status',
            'email_sent_at',
            'email_delivery_error',
        ])
        return notification, email_sent

    @staticmethod
    def bulk_create_and_send_email(
        recipients,
        title,
        content,
        category=Notification.NotificationType.SYSTEM,
        ref_type='',
        ref_id=None,
        sender=None,
        priority=Notification.Priority.NORMAL,
    ):
        """批量创建站内记录并按每个账户的邮件/摘要偏好投递。"""
        created_count = 0
        for recipient in recipients or []:
            notification, _ = NotificationService.create_and_send_email(
                recipient=recipient,
                title=title,
                content=content,
                category=category,
                ref_type=ref_type,
                ref_id=ref_id,
                sender=sender,
                priority=priority,
            )
            if notification is not None:
                created_count += 1
        return created_count

    @staticmethod
    def send_queued_digest(frequency, now=None):
        """把等待中的每日/每周通知合并成账户级摘要邮件并记录结果。"""
        if frequency not in {'daily', 'weekly'}:
            raise ValueError('摘要频率必须为 daily 或 weekly')
        now = now or timezone.now()
        queued = list(
            Notification.objects.filter(
                email_delivery_status=Notification.EmailDeliveryStatus.QUEUED,
                email_digest_frequency=frequency,
            )
            .select_related('recipient')
            .order_by('recipient_id', 'created_at', 'id')
        )
        grouped = {}
        for notification in queued:
            if notification.recipient_id:
                grouped.setdefault(notification.recipient_id, []).append(notification)

        stats = {'recipients': 0, 'sent': 0, 'failed': 0, 'suppressed': 0}
        for notifications in grouped.values():
            recipient = notifications[0].recipient
            deliverable = [
                item
                for item in notifications
                if should_notify_user(
                    recipient,
                    category=item.notification_type,
                    channel=Notification.Channel.EMAIL,
                    priority=item.priority,
                    now=now,
                )
            ]
            suppressed = [item for item in notifications if item not in deliverable]
            if suppressed:
                Notification.objects.filter(
                    id__in=[item.id for item in suppressed]
                ).update(
                    email_delivery_status=Notification.EmailDeliveryStatus.SUPPRESSED,
                    email_attempted_at=now,
                    email_delivery_error='账户已关闭对应邮件类别/渠道或处于免打扰时段',
                )
                stats['suppressed'] += len(suppressed)
            if not deliverable:
                continue
            stats['recipients'] += 1
            lines = [
                f'{index}. [{item.get_notification_type_display()}] {item.title}'
                for index, item in enumerate(deliverable[:50], start=1)
            ]
            if len(deliverable) > 50:
                lines.append(f'另有 {len(deliverable) - 50} 条，请登录系统查看。')
            label = '每日' if frequency == 'daily' else '每周'
            sent = bool(recipient.email) and send_notification_email(
                recipient.email,
                f'团队管理平台{label}通知摘要（{len(deliverable)} 条）',
                '\n'.join([
                    f'{recipient.name}，您好：',
                    '',
                    *lines,
                    '',
                    '详情请登录团队管理平台通知中心查看。',
                ]),
            )
            status = (
                Notification.EmailDeliveryStatus.SENT
                if sent
                else Notification.EmailDeliveryStatus.FAILED
            )
            Notification.objects.filter(
                id__in=[item.id for item in deliverable]
            ).update(
                email_delivery_status=status,
                email_attempted_at=now,
                email_sent_at=now if sent else None,
                email_delivery_error=(
                    '' if sent else '摘要邮件发送失败，请检查服务端邮件日志'
                ),
            )
            stats['sent' if sent else 'failed'] += len(deliverable)
        return stats

    @staticmethod
    def bulk_create_notifications(
        recipients,
        title,
        content,
        category=Notification.NotificationType.SYSTEM,
        ref_type='',
        ref_id=None,
        sender=None,
        priority=Notification.Priority.NORMAL,
        channel=Notification.Channel.INAPP,
    ):
        """
        批量创建通知（为多个接收人创建相同通知）
        :param recipients: 接收人列表（User 实例列表或 ID 列表）
        :param title: 通知标题
        :param content: 通知内容
        :param category: 通知类型
        :param ref_type: 关联对象类型
        :param ref_id: 关联对象 ID
        :param sender: 发送人
        :param priority: 优先级
        :param channel: 通知渠道
        :return: 创建的通知数量
        """
        if not recipients:
            return 0

        notifications = []
        for recipient in recipients:
            try:
                # 支持 User 实例或 ID
                recipient_user = recipient
                if isinstance(recipient, int):
                    recipient_user = User.objects.get(id=recipient)
                if not should_notify_user(
                    recipient_user,
                    category=category,
                    channel=channel,
                    priority=priority,
                ):
                    continue

                notifications.append(Notification(
                    recipient=recipient_user,
                    sender=sender,
                    title=title,
                    content=content,
                    notification_type=category,
                    priority=priority,
                    channel=channel,
                    related_object_type=ref_type,
                    related_object_id=ref_id,
                ))
            except Exception as e:
                logger.exception('批量创建通知时跳过接收人: %s', e)
                continue

        if notifications:
            with transaction.atomic():
                Notification.objects.bulk_create(notifications)
                from .streaming import publish_notifications
                notifications_to_publish = tuple(notifications)
                transaction.on_commit(
                    lambda: publish_notifications(notifications_to_publish)
                )

        return len(notifications)

    @classmethod
    def broadcast(
        cls,
        title,
        content,
        category=Notification.NotificationType.SYSTEM,
        priority=Notification.Priority.NORMAL,
        sender=None,
    ):
        """
        向所有活跃用户广播通知
        :param title: 通知标题
        :param content: 通知内容
        :param category: 通知类型（system/project/task/finance/competition/announcement）
        :param priority: 优先级（low/normal/high/urgent）
        :param sender: 发送人（User 实例或 ID，可为空）
        :return: 创建的通知数量
        """
        active_users = list(User.objects.filter(is_active=True))
        return cls.bulk_create_notifications(
            recipients=active_users,
            title=title,
            content=content,
            category=category,
            priority=priority,
            sender=sender,
        )

    @staticmethod
    def mark_as_read(notification_id, user):
        """
        标记单条通知为已读
        :param notification_id: 通知 ID
        :param user: 当前用户
        :return: (是否成功, 消息)
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user,
                channel=Notification.Channel.INAPP,
            )
        except Notification.DoesNotExist:
            return False, '通知不存在'

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
            unread_count = Notification.objects.filter(
                recipient=user,
                channel=Notification.Channel.INAPP,
                is_read=False,
            ).count()
            from .streaming import publish_notification_state
            transaction.on_commit(lambda: publish_notification_state(
                user.pk,
                notification_id=notification.pk,
                unread_count=unread_count,
            ))
        return True, '已标记为已读'

    @staticmethod
    def mark_all_as_read(user):
        """
        标记当前用户所有未读通知为已读
        :param user: 当前用户
        :return: 标记的通知数量
        """
        now = timezone.now()
        count = Notification.objects.filter(
            recipient=user,
            channel=Notification.Channel.INAPP,
            is_read=False,
        ).update(is_read=True, read_at=now)
        if count:
            from .streaming import publish_notification_state
            transaction.on_commit(lambda: publish_notification_state(
                user.pk,
                all_read=True,
                unread_count=0,
            ))
        return count

    @staticmethod
    def get_unread_count(user):
        """
        获取当前用户未读通知数量
        :param user: 当前用户
        :return: 未读数量
        """
        return Notification.objects.filter(
            recipient=user,
            channel=Notification.Channel.INAPP,
            is_read=False,
        ).count()
