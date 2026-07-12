"""
自定义表单模型
- CustomForm: 自定义表单定义
- FormSubmission: 表单提交记录

放在独立文件中，避免迁移冲突。通过 apps/common/models.py 导入。
"""
from django.db import models


class CustomForm(models.Model):
    """自定义表单"""

    # 表单名称
    name = models.CharField('表单名称', max_length=200)
    # 描述
    description = models.TextField('描述', blank=True, default='')
    # 表单字段定义（JSON 数组，描述字段类型/标题/校验等）
    fields = models.JSONField('字段定义', default=list)
    # 创建人
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_forms',
        verbose_name='创建人',
    )
    # 是否启用
    is_active = models.BooleanField('是否启用', default=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'custom_forms'
        verbose_name = '自定义表单'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class FormSubmission(models.Model):
    """表单提交记录"""

    # 关联表单
    form = models.ForeignKey(
        'common.CustomForm',
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='表单',
    )
    # 提交人
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='form_submissions',
        verbose_name='提交人',
    )
    # 提交数据（JSON 对象）
    data = models.JSONField('提交数据', default=dict)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'form_submissions'
        verbose_name = '表单提交'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.form} 提交记录({self.created_at})'
