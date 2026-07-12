"""
项目风险模型
单独文件存放，避免与现有 models.py 产生迁移冲突
"""
from django.db import models


class ProjectRisk(models.Model):
    """项目风险"""

    class Level(models.TextChoices):
        """风险级别"""
        LOW = 'low', '低'
        MEDIUM = 'medium', '中'
        HIGH = 'high', '高'
        CRITICAL = 'critical', '严重'

    class Status(models.TextChoices):
        """风险状态"""
        OPEN = 'open', '开放'
        MITIGATING = 'mitigating', '处理中'
        CLOSED = 'closed', '已关闭'

    # 所属项目
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='risks',
        verbose_name='项目',
    )
    # 风险标题
    title = models.CharField('风险标题', max_length=200)
    # 风险描述
    description = models.TextField('风险描述', blank=True, default='')
    # 风险级别
    level = models.CharField(
        '风险级别',
        max_length=20,
        choices=Level.choices,
        default=Level.MEDIUM,
    )
    # 状态
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    # 缓解措施
    mitigation_plan = models.TextField('缓解措施', blank=True, default='')
    # 识别人
    identified_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='identified_risks',
        verbose_name='识别人',
    )
    # 识别时间
    identified_at = models.DateTimeField('识别时间', auto_now_add=True)
    # 解决时间
    resolved_at = models.DateTimeField('解决时间', null=True, blank=True)

    class Meta:
        db_table = 'project_risks'
        verbose_name = '项目风险'
        verbose_name_plural = verbose_name
        ordering = ['-level', '-identified_at']

    def __str__(self):
        return f'{self.project.name} - {self.title}({self.get_level_display()})'

    def resolve(self):
        """标记为已关闭并记录解决时间"""
        from django.utils import timezone
        self.status = self.Status.CLOSED
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])
