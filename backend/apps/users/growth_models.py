"""
成员成长记录模型
单独文件存放，避免与现有 models.py 产生迁移冲突
"""
from django.db import models


class MemberGrowth(models.Model):
    """成员成长记录"""

    # 关联用户
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='growth_records',
        verbose_name='用户',
    )
    # 统计周期，例如 "2026-Q1"
    period = models.CharField('统计周期', max_length=20)
    # 参与项目数
    project_count = models.IntegerField('参与项目数', default=0)
    # 完成任务数
    task_count = models.IntegerField('完成任务数', default=0)
    # 贡献得分
    contribution_score = models.DecimalField(
        '贡献得分', max_digits=10, decimal_places=2, default=0,
    )
    # 技能数
    skill_count = models.IntegerField('技能数', default=0)
    # 备注
    notes = models.TextField('备注', blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'member_growth'
        verbose_name = '成员成长记录'
        verbose_name_plural = verbose_name
        ordering = ['-period']
        # 同一用户同一周期唯一
        unique_together = [('user', 'period')]

    def __str__(self):
        return f'{self.user.name} - {self.period}'
