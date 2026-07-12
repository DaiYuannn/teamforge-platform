"""
登录安全模型
- LoginAttempt: 登录尝试记录
- IPBlocklist: IP 黑名单

放在独立文件中，避免迁移冲突。通过 apps/users/models.py 导入。
"""
from django.db import models


class LoginAttempt(models.Model):
    """登录尝试记录"""

    # 邮箱
    email = models.EmailField('邮箱')
    # IP 地址
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    # User-Agent
    user_agent = models.TextField('User-Agent', blank=True, default='')
    # 是否成功
    is_success = models.BooleanField('是否成功', default=False)
    # 失败原因
    failure_reason = models.CharField('失败原因', max_length=200, blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'login_attempts'
        verbose_name = '登录尝试记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        status = '成功' if self.is_success else '失败'
        return f'{self.email}({status})'


class IPBlocklist(models.Model):
    """IP 黑名单"""

    # IP 地址（唯一）
    ip_address = models.GenericIPAddressField('IP地址', unique=True)
    # 封禁原因
    reason = models.CharField('原因', max_length=200, blank=True, default='')
    # 封禁截止时间
    blocked_until = models.DateTimeField('封禁至', null=True, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ip_blocklist'
        verbose_name = 'IP黑名单'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.ip_address}({self.reason or "封禁"})'
