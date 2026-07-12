"""
第三方集成模型
包含 IntegrationConfig（集成配置）、IntegrationLog（集成调用日志）
用于对接企业微信/通用Webhook/邮件等第三方通知渠道
（飞书/QQ机器人已移除，不再集成；群机器人推送功能后期实现）
"""
from django.db import models
from django.conf import settings

# 导入分散在独立文件中的模型，使 Django 迁移系统能检测到它们
from .external_models import ExternalPlatform  # noqa: F401
from .git_models import GitRepository  # noqa: F401


class IntegrationConfig(models.Model):
    """
    第三方集成配置模型
    记录各类第三方通知渠道的连接配置
    保留渠道：企业微信、通用Webhook、邮件
    """

    class Provider(models.TextChoices):
        """第三方服务提供商"""
        WECOM = 'wecom', '企业微信'
        WEBHOOK = 'webhook', '通用Webhook'
        EMAIL = 'email', '邮件'

    # 集成名称
    name = models.CharField('集成名称', max_length=100)
    # 服务提供商
    provider = models.CharField(
        '服务提供商',
        max_length=20,
        choices=Provider.choices,
        default=Provider.WEBHOOK,
    )
    # Webhook 地址
    webhook_url = models.URLField('Webhook地址', blank=True, default='')
    # 应用ID
    app_id = models.CharField('应用ID', max_length=200, blank=True, default='')
    # 加密密钥（加密存储，预留）
    encrypted_secret = models.TextField('加密密钥', blank=True, default='')
    # 是否启用
    enabled = models.BooleanField('是否启用', default=False)
    # 创建人
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='integration_configs_created',
        verbose_name='创建人',
        null=True, blank=True,
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'integration_configs'
        verbose_name = '集成配置'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}({self.get_provider_display()})'


class IntegrationLog(models.Model):
    """
    第三方集成调用日志模型
    记录每次第三方通知发送的结果，用于追踪和排查问题
    """

    class Provider(models.TextChoices):
        """第三方服务提供商（与 IntegrationConfig 保持一致）"""
        WECOM = 'wecom', '企业微信'
        WEBHOOK = 'webhook', '通用Webhook'
        EMAIL = 'email', '邮件'

    class Status(models.TextChoices):
        """发送状态"""
        PENDING = 'pending', '待发送'
        SUCCESS = 'success', '成功'
        FAILED = 'failed', '失败'

    # 服务提供商
    provider = models.CharField(
        '服务提供商',
        max_length=20,
        choices=Provider.choices,
        default=Provider.WEBHOOK,
    )
    # 事件类型
    event_type = models.CharField('事件类型', max_length=100)
    # 发送对象
    target = models.CharField('发送对象', max_length=200, blank=True, default='')
    # 发送内容
    payload = models.JSONField('发送内容', default=dict)
    # 发送状态
    status = models.CharField(
        '发送状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # 返回信息
    response = models.TextField('返回信息', blank=True, default='')
    # 错误信息
    error_message = models.TextField('错误信息', blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'integration_logs'
        verbose_name = '集成日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_provider_display()} - {self.event_type}({self.get_status_display()})'


class WebhookConfig(models.Model):
    """
    Webhook 配置模型（事件订阅式 Webhook）
    用于向第三方系统推送指定事件类型的回调通知
    - name: 配置名称
    - url: 回调地址
    - secret: 签名密钥（用于校验请求来源）
    - is_active: 是否启用
    - events: 订阅的事件类型列表（JSON 数组）
    """

    # 配置名称
    name = models.CharField('名称', max_length=100)
    # 回调地址
    url = models.URLField('Webhook 地址')
    # 签名密钥
    secret = models.CharField('签名密钥', max_length=200, blank=True, default='')
    # 是否启用
    is_active = models.BooleanField('是否启用', default=True)
    # 订阅事件类型列表（JSON 数组，如 ["task.overdue", "project.closed"]）
    events = models.JSONField('订阅事件', default=list, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'webhook_configs'
        verbose_name = 'Webhook配置'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}({self.url})'

    @property
    def is_subscribed_all(self):
        """是否订阅全部事件（events 为空数组时视为订阅全部）"""
        return not self.events
