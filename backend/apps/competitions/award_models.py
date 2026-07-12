"""
比赛获奖记录模型
单独文件存放，避免与现有 models.py 产生迁移冲突
"""
from django.db import models
from django.conf import settings


class CompetitionAward(models.Model):
    """比赛获奖记录"""

    # 关联比赛
    competition = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.CASCADE,
        related_name='awards',
        verbose_name='关联比赛',
    )
    # 奖项名称
    award_name = models.CharField('奖项名称', max_length=200)
    # 获奖等级（如 一等奖、特等奖、金奖等）
    award_level = models.CharField('获奖等级', max_length=50, blank=True, default='')
    # 获奖日期
    award_date = models.DateField('获奖日期', null=True, blank=True)
    # 获奖人（多人，使用 M2M 关联用户）
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='competition_awards',
        verbose_name='获奖人',
        blank=True,
    )
    # 备注
    notes = models.TextField('备注', blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'competition_awards'
        verbose_name = '比赛获奖记录'
        verbose_name_plural = verbose_name
        ordering = ['-award_date', '-created_at']

    def __str__(self):
        return f'{self.competition.name} - {self.award_name}'
