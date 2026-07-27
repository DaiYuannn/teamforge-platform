"""
外部平台集成模型
- ExternalPlatform: 外部平台对接配置

放在独立文件中，避免迁移冲突。通过 apps/integrations/models.py 导入。
"""
from django.db import models
from django.utils import timezone

from common.encryption import get_field_cipher


ENCRYPTED_PREFIX = 'enc:v1:'


class ExternalPlatform(models.Model):
    """外部平台集成"""

    # 平台名称
    name = models.CharField('平台名称', max_length=200)
    # 平台类型（如 dingtalk / feishu / jira / github）
    platform_type = models.CharField('平台类型', max_length=50)
    # API 地址
    api_url = models.URLField('API地址', blank=True, default='')
    # API 密钥
    api_key = models.CharField('API密钥', max_length=500, blank=True, default='')
    # 是否启用
    is_active = models.BooleanField('是否启用', default=True)
    # 扩展配置（JSON）
    config = models.JSONField('扩展配置', default=dict, blank=True)
    connection_status = models.CharField(max_length=20, default='unchecked')
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')
    remote_metadata = models.JSONField(default=dict, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'external_platforms'
        verbose_name = '外部平台集成'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}({self.platform_type})'

    def save(self, *args, **kwargs):
        if self.api_key and not self.api_key.startswith(ENCRYPTED_PREFIX):
            self.api_key = ENCRYPTED_PREFIX + get_field_cipher().encrypt(self.api_key)
        super().save(*args, **kwargs)

    def get_api_key(self):
        if not self.api_key:
            return ''
        if not self.api_key.startswith(ENCRYPTED_PREFIX):
            return self.api_key
        return get_field_cipher().decrypt(self.api_key[len(ENCRYPTED_PREFIX):])

    def record_connection(self, *, connected, error='', metadata=None, synced=False):
        now = timezone.now()
        self.connection_status = 'connected' if connected else 'error'
        self.last_checked_at = now
        self.last_error = error
        fields = ['connection_status', 'last_checked_at', 'last_error', 'updated_at']
        if metadata is not None:
            self.remote_metadata = metadata
            fields.append('remote_metadata')
        if synced and connected:
            self.last_synced_at = now
            fields.append('last_synced_at')
        self.save(update_fields=fields)
