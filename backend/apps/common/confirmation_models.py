"""
敏感操作确认模型
- SensitiveConfirmation: 敏感操作确认令牌

放在独立文件中，避免迁移冲突。通过 apps/common/models.py 导入。
"""
from django.db import models


class SensitiveConfirmation(models.Model):
    """敏感操作确认"""

    class Type(models.TextChoices):
        """确认类型"""
        DELETE_PROJECT = 'delete_project', '删除项目'
        DELETE_FINANCE = 'delete_finance', '删除经费记录'
        BULK_DELETE = 'bulk_delete', '批量删除'
        DATA_EXPORT = 'data_export', '数据导出'
        PASSWORD_CHANGE = 'password_change', '修改密码'

    # 用户
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='confirmations',
        verbose_name='用户',
    )
    # 确认类型
    confirm_type = models.CharField('确认类型', max_length=50, choices=Type.choices)
    # 目标类型
    target_type = models.CharField('目标类型', max_length=50, default='')
    # 目标ID
    target_id = models.CharField('目标ID', max_length=100, default='')
    # 确认令牌（唯一）
    token = models.CharField('确认令牌', max_length=64, unique=True)
    # 是否已确认
    is_confirmed = models.BooleanField('已确认', default=False)
    # 过期时间
    expires_at = models.DateTimeField('过期时间')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'sensitive_confirmations'
        verbose_name = '敏感操作确认'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user}({self.get_confirm_type_display()})'
