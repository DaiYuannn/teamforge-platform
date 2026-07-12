"""
项目里程碑模型
单独文件存放，避免与现有 models.py 产生迁移冲突
"""
from django.db import models
from django.utils import timezone


class Milestone(models.Model):
    """项目里程碑"""

    # 所属项目
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='milestones',
        verbose_name='项目',
    )
    # 标题
    title = models.CharField('标题', max_length=200)
    # 描述
    description = models.TextField('描述', blank=True, default='')
    # 截止日期
    due_date = models.DateField('截止日期', null=True, blank=True)
    # 是否已完成
    is_completed = models.BooleanField('已完成', default=False)
    # 完成时间
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    # 排序
    sort_order = models.IntegerField('排序', default=0)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'milestones'
        verbose_name = '项目里程碑'
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'due_date']

    def __str__(self):
        return f'{self.project.name} - {self.title}'

    def mark_completed(self):
        """标记为已完成"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['is_completed', 'completed_at'])

    def mark_incomplete(self):
        """标记为未完成"""
        self.is_completed = False
        self.completed_at = None
        self.save(update_fields=['is_completed', 'completed_at'])
