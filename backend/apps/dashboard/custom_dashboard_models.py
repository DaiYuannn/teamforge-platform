"""
自定义看板模型
- CustomDashboard: 用户自定义看板布局（widgets, positions, filters）
单独文件存放，便于管理与迁移
"""
from django.db import models
from django.conf import settings


class CustomDashboard(models.Model):
    """自定义看板"""

    # 所属用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='custom_dashboards',
        verbose_name='所属用户',
    )
    # 看板名称
    name = models.CharField('看板名称', max_length=200)
    # 看板配置（widgets, positions, filters）
    config = models.JSONField('看板配置', default=dict)
    # 是否默认
    is_default = models.BooleanField('默认看板', default=False)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'custom_dashboards'
        verbose_name = '自定义看板'
        verbose_name_plural = verbose_name
        ordering = ['-is_default', '-updated_at']
        # 同一用户看板名称唯一
        unique_together = [('user', 'name')]

    def __str__(self):
        return f'{self.user.name} - {self.name}'
