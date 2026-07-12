"""
双因素认证（2FA）模型
- TwoFactorSecret: 保存用户的 TOTP 密钥与备用码

放在独立文件中，避免迁移冲突。通过 apps/users/models.py 导入。
"""
from django.db import models


class TwoFactorSecret(models.Model):
    """双因素认证"""

    # 关联用户（一对一）
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='two_factor',
        verbose_name='用户',
    )
    # TOTP 密钥
    secret = models.CharField('密钥', max_length=64)
    # 是否已启用
    is_enabled = models.BooleanField('已启用', default=False)
    # 备用码（一次性使用，JSON 数组）
    backup_codes = models.JSONField('备用码', default=list)
    # 启用时间
    enabled_at = models.DateTimeField('启用时间', null=True, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'two_factor_secrets'
        verbose_name = '双因素认证'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user}({"已启用" if self.is_enabled else "未启用"})'
