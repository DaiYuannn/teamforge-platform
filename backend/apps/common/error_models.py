"""
前端错误日志模型（N57 错误监控）
- ErrorLog: 记录前端上报的错误/警告/信息日志

放在独立文件中，避免迁移冲突。通过 apps/common/models.py 导入。
"""
from django.conf import settings
from django.db import models


class ErrorLog(models.Model):
    """前端错误日志"""

    class Level(models.TextChoices):
        """日志级别"""
        ERROR = 'error', '错误'
        WARNING = 'warning', '警告'
        INFO = 'info', '信息'

    # 级别
    level = models.CharField('级别', max_length=20, default='error',
                             choices=Level.choices)
    # 错误信息
    message = models.TextField('错误信息')
    # 堆栈
    stack = models.TextField('堆栈', blank=True, default='')
    # 页面 URL
    url = models.URLField('页面URL', max_length=500, blank=True, default='')
    # User-Agent
    user_agent = models.TextField('User-Agent', blank=True, default='')
    # 关联用户（可为空，未登录用户也会上报）
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='error_logs',
        verbose_name='用户',
    )
    # 元数据（JSON）
    metadata = models.JSONField('元数据', default=dict, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'error_logs'
        verbose_name = '前端错误日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.level}] {self.message[:50]}'
