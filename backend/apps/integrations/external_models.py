"""
外部平台集成模型
- ExternalPlatform: 外部平台对接配置

放在独立文件中，避免迁移冲突。通过 apps/integrations/models.py 导入。
"""
from django.db import models


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
