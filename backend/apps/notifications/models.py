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
        CONTRIBUTION = 'contribution', '贡献通知'
        IP = 'ip', '知识产权通知'
        SENSITIVE = 'sensitive', '敏感资料通知'
        SCHEDULE = 'schedule', '工时通知'
        REPORT = 'report', '报表通知'
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

    class EmailDeliveryStatus(models.TextChoices):
        NOT_REQUESTED = 'not_requested', '未请求'
        QUEUED = 'queued', '等待摘要'
        SENT = 'sent', '已发送'
        FAILED = 'failed', '发送失败'
        SUPPRESSED = 'suppressed', '已按偏好关闭'

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
    email_delivery_status = models.CharField(
        '邮件投递状态',
        max_length=20,
        choices=EmailDeliveryStatus.choices,
        default=EmailDeliveryStatus.NOT_REQUESTED,
        db_index=True,
    )
    email_digest_frequency = models.CharField(
        '邮件摘要频率',
        max_length=10,
        blank=True,
        default='',
    )
    email_attempted_at = models.DateTimeField('邮件尝试时间', null=True, blank=True)
    email_sent_at = models.DateTimeField('邮件发送时间', null=True, blank=True)
    email_delivery_error = models.TextField('邮件投递错误', blank=True, default='')
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


class Announcement(models.Model):
    """公告"""
    class Category(models.TextChoices):
        SYSTEM = 'system', '系统公告'
        PROJECT = 'project', '项目公告'
        ACTIVITY = 'activity', '活动公告'
        FAQ = 'faq', '常见问题'
        TEMPLATE = 'template', '计划书与PPT模板'
        MEETING = 'meeting', '会议回放'
        NEWS = 'news', '新闻与资料'
        OTHER = 'other', '其他'

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PUBLISHED = 'published', '已发布'
        ARCHIVED = 'archived', '已归档'

    class Audience(models.TextChoices):
        ORGANIZATION = 'organization', '全实践团队'
        TEAMS = 'teams', '指定小团队'
        PROJECTS = 'projects', '指定项目'
        PUBLIC = 'public', '互联网公开'

    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    resource_links = models.JSONField(
        '资源链接',
        default=list,
        blank=True,
        help_text='格式：[{"title": "资料名称", "url": "https://..."}]',
    )
    category = models.CharField(
        '类别', max_length=20, choices=Category.choices, default=Category.OTHER
    )
    status = models.CharField(
        '状态', max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    audience = models.CharField(
        '发布范围',
        max_length=20,
        choices=Audience.choices,
        default=Audience.ORGANIZATION,
        db_index=True,
    )
    organization = models.ForeignKey(
        'common.Team',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='organization_announcements',
        verbose_name='所属实践团队',
        help_text='公告所属的根团队，用于不同实践团队之间的数据隔离',
    )
    target_teams = models.ManyToManyField(
        'common.Team',
        blank=True,
        related_name='targeted_announcements',
        verbose_name='目标小团队',
    )
    target_projects = models.ManyToManyField(
        'projects.Project',
        blank=True,
        related_name='targeted_announcements',
        verbose_name='目标项目',
    )
    is_pinned = models.BooleanField('置顶', default=False)
    # 兼容旧接口和既有公开门户；新代码以 audience=public 为准。
    is_public = models.BooleanField('是否公开', default=False)
    author = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True,
        related_name='announcements', verbose_name='发布人',
    )
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-is_pinned', '-published_at', '-created_at']
        verbose_name = '公告'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.title}({self.get_status_display()})'

    def save(self, *args, **kwargs):
        # 直接通过 ORM 创建的旧代码仍可能只传 is_public。序列化器在范围
        # 切换时会同时写入两个字段，这里的双向同步负责兼容旧调用。
        if self.audience == self.Audience.PUBLIC:
            self.is_public = True
        elif self.is_public:
            self.audience = self.Audience.PUBLIC
        super().save(*args, **kwargs)
