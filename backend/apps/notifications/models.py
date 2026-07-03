"""
通知模型（架构预留）
包含 Notification（通知公告）
"""
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    通知公告模型（架构预留）
    系统通知、项目通知、任务提醒等
    """

    class NotificationType(models.TextChoices):
        """通知类型"""
        SYSTEM = 'system', '系统通知'
        PROJECT = 'project', '项目通知'
        TASK = 'task', '任务通知'
        FINANCE = 'finance', '经费通知'
        COMPETITION = 'competition', '比赛通知'
        ANNOUNCEMENT = 'announcement', '公告'

    class Priority(models.TextChoices):
        """优先级"""
        LOW = 'low', '低'
        NORMAL = 'normal', '普通'
        HIGH = 'high', '高'
        URGENT = 'urgent', '紧急'

    class Channel(models.TextChoices):
        """通知渠道"""
        INAPP = 'inapp', '站内'
        EMAIL = 'email', '邮件'
        WEBHOOK = 'webhook', 'Webhook'

    # 通知类型
    notification_type = models.CharField(
        '通知类型',
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    # 通知渠道
    channel = models.CharField(
        '通知渠道',
        max_length=20,
        choices=Channel.choices,
        default=Channel.INAPP,
    )
    # 标题
    title = models.CharField('标题', max_length=200)
    # 内容
    content = models.TextField('内容')
    # 优先级
    priority = models.CharField(
        '优先级',
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    # 接收人（为空表示全体）
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='接收人',
        null=True, blank=True,
    )
    # 发送人
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='sent_notifications',
        verbose_name='发送人',
        null=True, blank=True,
    )
    # 是否已读
    is_read = models.BooleanField('已读', default=False)
    # 已读时间
    read_at = models.DateTimeField('已读时间', null=True, blank=True)
    # 关联对象类型
    related_object_type = models.CharField('关联对象类型', max_length=50, blank=True, default='')
    # 关联对象ID
    related_object_id = models.IntegerField('关联对象ID', null=True, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = '通知公告'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title}({self.get_notification_type_display()})'
