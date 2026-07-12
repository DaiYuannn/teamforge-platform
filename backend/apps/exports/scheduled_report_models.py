"""
定时报表模型
- ScheduledReport: 定时报表发送计划
单独文件存放，便于管理与迁移
"""
from django.db import models


class ScheduledReport(models.Model):
    """定时报表"""

    # 发送频率
    class Frequency(models.TextChoices):
        DAILY = 'daily', '每日'
        WEEKLY = 'weekly', '每周'
        MONTHLY = 'monthly', '每月'

    report = models.ForeignKey(
        'exports.CustomReport',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='关联报表',
    )
    recipients = models.ManyToManyField(
        'users.User',
        related_name='scheduled_reports',
        verbose_name='接收人',
        blank=True,
    )
    frequency = models.CharField(
        '频率', max_length=20, choices=Frequency.choices, default=Frequency.DAILY,
    )
    last_run = models.DateTimeField('上次运行', null=True, blank=True)
    next_run = models.DateTimeField('下次运行', null=True, blank=True)
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'scheduled_reports'
        verbose_name = '定时报表'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.report.name} - {self.get_frequency_display()}'
