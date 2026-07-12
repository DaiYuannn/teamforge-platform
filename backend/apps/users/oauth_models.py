"""
第三方登录（OAuth）模型
- OAuthAccount: 第三方账号绑定记录

放在独立文件中，避免迁移冲突。通过 apps/users/models.py 导入。
"""
from django.db import models


class OAuthAccount(models.Model):
    """第三方账号绑定"""

    # 服务提供商（如 github / google / wechat）
    provider = models.CharField('提供商', max_length=50)
    # 第三方用户唯一标识
    provider_uid = models.CharField('第三方用户ID', max_length=200)
    # 关联本系统用户
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='oauth_accounts',
        verbose_name='用户',
    )
    # 访问令牌
    access_token = models.CharField('访问令牌', max_length=500, blank=True, default='')
    # 刷新令牌
    refresh_token = models.CharField('刷新令牌', max_length=500, blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'oauth_accounts'
        verbose_name = '第三方账号绑定'
        verbose_name_plural = verbose_name
        unique_together = [('provider', 'provider_uid')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.provider}:{self.provider_uid} -> {self.user}'
