"""
项目模板模型
单独文件存放，避免与现有 models.py 产生迁移冲突
关键：config(JSON) 存储任务结构、里程碑等，可用于实例化项目
"""
from django.db import models


class ProjectTemplate(models.Model):
    """项目模板"""

    # 模板名称
    name = models.CharField('模板名称', max_length=200)
    # 模板描述
    description = models.TextField('模板描述', blank=True, default='')
    # 模板类别
    category = models.CharField('模板类别', max_length=100, blank=True, default='')
    # 模板配置（包含任务结构、里程碑等）
    config = models.JSONField('模板配置', default=dict)
    # 创建人
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='project_templates',
        verbose_name='创建人',
    )
    # 是否启用
    is_active = models.BooleanField('启用', default=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'project_templates'
        verbose_name = '项目模板'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}'
