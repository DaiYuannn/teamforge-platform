"""
自定义报表模型
- CustomReport: 自定义报表配置（数据源、过滤器、分组、图表类型）
单独文件存放，便于管理与迁移
"""
from django.db import models


class CustomReport(models.Model):
    """自定义报表"""

    # 报表类型
    class ReportType(models.TextChoices):
        SUMMARY = 'summary', '汇总'
        COMPARISON = 'comparison', '对比'
        TREND = 'trend', '趋势'

    name = models.CharField('报表名称', max_length=200)
    description = models.TextField('描述', blank=True, default='')
    report_type = models.CharField('报表类型', max_length=50)  # summary, comparison, trend
    config = models.JSONField('报表配置', default=dict)  # data sources, filters, group_by, chart_type
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='custom_reports',
        verbose_name='创建人',
    )
    is_scheduled = models.BooleanField('定时生成', default=False)
    schedule_cron = models.CharField('定时表达式', max_length=100, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'custom_reports'
        verbose_name = '自定义报表'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name
