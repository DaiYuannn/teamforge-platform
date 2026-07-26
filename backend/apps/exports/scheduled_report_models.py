"""定时报表模型。"""
from datetime import time

from django.conf import settings
from django.db import models


class ScheduledReport(models.Model):
    """账户创建的报表发送计划。"""

    class Frequency(models.TextChoices):
        DAILY = 'daily', '每日'
        WEEKLY = 'weekly', '每周'
        MONTHLY = 'monthly', '每月'

    class FileFormat(models.TextChoices):
        XLSX = 'xlsx', 'Excel'
        DOCX = 'docx', 'Word'
        PDF = 'pdf', 'PDF'

    class RunStatus(models.TextChoices):
        NEVER = 'never', '尚未运行'
        RUNNING = 'running', '运行中'
        SUCCESS = 'success', '成功'
        PARTIAL = 'partial', '文件已生成，邮件未发送'
        FAILED = 'failed', '失败'

    report = models.ForeignKey(
        'exports.CustomReport',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='关联报表',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_scheduled_reports',
        verbose_name='创建人',
        null=True,
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='scheduled_reports',
        verbose_name='接收人',
        blank=True,
    )
    frequency = models.CharField(
        '频率',
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.DAILY,
    )
    execution_time = models.TimeField('执行时间', default=time(9, 0))
    weekday = models.PositiveSmallIntegerField(
        '周几',
        default=0,
        help_text='0 表示周一，6 表示周日，仅每周计划使用。',
    )
    day_of_month = models.PositiveSmallIntegerField(
        '每月日期',
        default=1,
        help_text='1-28，仅每月计划使用。',
    )
    timezone = models.CharField('时区', max_length=64, default='Asia/Shanghai')
    file_format = models.CharField(
        '文件格式',
        max_length=10,
        choices=FileFormat.choices,
        default=FileFormat.XLSX,
    )
    last_run = models.DateTimeField('上次运行', null=True, blank=True)
    next_run = models.DateTimeField('下次运行', null=True, blank=True)
    last_status = models.CharField(
        '最近状态',
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.NEVER,
    )
    last_error = models.TextField('最近错误', blank=True, default='')
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


class ScheduledReportExecution(models.Model):
    """一次可审计、可下载的报表运行记录。"""

    class Trigger(models.TextChoices):
        MANUAL = 'manual', '手动'
        SCHEDULED = 'scheduled', '定时'

    class DeliveryStatus(models.TextChoices):
        NOT_REQUESTED = 'not_requested', '未配置接收人'
        NOT_CONFIGURED = 'not_configured', '邮件服务未配置'
        SENT = 'sent', '已发送'
        FAILED = 'failed', '发送失败'

    schedule = models.ForeignKey(
        ScheduledReport,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='定时报表',
    )
    trigger = models.CharField(
        '触发方式',
        max_length=20,
        choices=Trigger.choices,
        default=Trigger.MANUAL,
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=ScheduledReport.RunStatus.choices,
        default=ScheduledReport.RunStatus.RUNNING,
    )
    file = models.FileField(
        '报表文件',
        upload_to='scheduled_reports/%Y/%m/',
        blank=True,
        null=True,
    )
    file_name = models.CharField('文件名', max_length=255, blank=True, default='')
    file_format = models.CharField('文件格式', max_length=10, blank=True, default='')
    file_size = models.PositiveBigIntegerField('文件大小', default=0)
    delivery_status = models.CharField(
        '投递状态',
        max_length=30,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.NOT_REQUESTED,
    )
    recipient_snapshot = models.JSONField('接收人快照', default=list)
    message = models.CharField('运行说明', max_length=500, blank=True, default='')
    error = models.TextField('错误详情', blank=True, default='')
    started_at = models.DateTimeField('开始时间', auto_now_add=True)
    finished_at = models.DateTimeField('完成时间', null=True, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='generated_report_executions',
        verbose_name='触发人',
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'scheduled_report_executions'
        verbose_name = '定时报表执行记录'
        verbose_name_plural = verbose_name
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.schedule} - {self.get_status_display()}'
