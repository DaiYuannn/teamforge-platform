"""
通知服务
封装通知创建、发送、批量操作等业务逻辑
"""
import logging

from django.db import transaction

from apps.users.models import User
from .models import Notification
from .email_service import send_notification_email

logger = logging.getLogger('apps.notifications')


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
        # 先创建邮件渠道的站内通知记录
        notification = NotificationService.create_notification(
            recipient=recipient,
            title=title,
            content=content,
            category=category,
            ref_type=ref_type,
            ref_id=ref_id,
            sender=sender,
            priority=priority,
            channel=Notification.Channel.EMAIL,
        )

        # 获取接收人邮箱
        email = None
        try:
            if isinstance(recipient, int):
                recipient = User.objects.get(id=recipient)
            email = recipient.email
        except Exception:
            pass

        # 发送邮件
        email_sent = False
        if email:
            email_sent = send_notification_email(email, title, content)

        return notification, email_sent

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
            notification = Notification.objects.get(id=notification_id, recipient=user)
        except Notification.DoesNotExist:
            return False, '通知不存在'

        if not notification.is_read:
            from django.utils import timezone
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
        return True, '已标记为已读'

    @staticmethod
    def mark_all_as_read(user):
        """
        标记当前用户所有未读通知为已读
        :param user: 当前用户
        :return: 标记的通知数量
        """
        from django.utils import timezone
        now = timezone.now()
        count = Notification.objects.filter(
            recipient=user, is_read=False
        ).update(is_read=True, read_at=now)
        return count

    @staticmethod
    def get_unread_count(user):
        """
        获取当前用户未读通知数量
        :param user: 当前用户
        :return: 未读数量
        """
        return Notification.objects.filter(recipient=user, is_read=False).count()
