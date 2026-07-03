"""
邮件发送服务
封装通知邮件发送逻辑
"""
import logging

from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('apps.notifications')


def send_notification_email(to_email, title, content):
    """
    发送通知邮件
    :param to_email: 收件人邮箱
    :param title: 邮件标题
    :param content: 邮件内容
    :return: bool 是否发送成功
    """
    # 未配置发件邮箱时直接返回 False，不抛异常
    if not getattr(settings, 'DEFAULT_FROM_EMAIL', None):
        logger.warning('未配置 DEFAULT_FROM_EMAIL，跳过邮件发送')
        return False
    if not to_email:
        logger.warning('收件人邮箱为空，跳过邮件发送')
        return False

    try:
        send_mail(
            subject=title,
            message=content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
        return True
    except Exception as e:
        logger.exception('发送邮件失败: %s', e)
        return False
