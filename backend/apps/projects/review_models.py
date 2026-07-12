"""
项目复盘模型
单独文件存放，避免与现有 models.py 产生迁移冲突
"""
from django.db import models
from django.utils import timezone


class ProjectReview(models.Model):
    """项目复盘"""
    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        SUBMITTED = 'submitted', '已提交'
        REVIEWED = 'reviewed', '已审阅'

    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='关联项目',
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # 复盘内容
    summary = models.TextField('项目总结', blank=True, default='')  # 项目整体总结
    achievements = models.TextField('主要成果', blank=True, default='')  # 主要成果
    problems = models.TextField('遇到的问题', blank=True, default='')  # 遇到的问题
    lessons = models.TextField('经验教训', blank=True, default='')  # 经验教训
    improvements = models.TextField('改进建议', blank=True, default='')  # 改进建议
    team_feedback = models.TextField('团队反馈', blank=True, default='')  # 团队成员反馈

    # 评分 (1-5)
    overall_score = models.IntegerField('总体评分', null=True, blank=True)  # 1-5
    schedule_score = models.IntegerField('进度管理评分', null=True, blank=True)
    budget_score = models.IntegerField('经费管理评分', null=True, blank=True)
    team_score = models.IntegerField('团队协作评分', null=True, blank=True)
    quality_score = models.IntegerField('成果质量评分', null=True, blank=True)

    # 元数据
    reviewer = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_projects',
        verbose_name='复盘人',
    )
    review_date = models.DateTimeField('复盘日期', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'project_reviews'
        verbose_name = '项目复盘'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.project.name} - 复盘({self.get_status_display()})'
