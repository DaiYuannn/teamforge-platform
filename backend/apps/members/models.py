"""
成员管理模型
第一期：只基本信息和联系方式（信息在User模型中）
第二期：技能标签和灵活工时（架构预留）
"""
from django.db import models
from django.conf import settings


class SkillTag(models.Model):
    """
    技能标签模型（架构预留，第二期实现）
    """

    # 技能名称（唯一）
    name = models.CharField('技能名称', max_length=100, unique=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'skill_tags'
        verbose_name = '技能标签'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class MemberSkill(models.Model):
    """
    成员技能模型（架构预留，第二期实现）
    记录成员掌握的技能及熟练度
    """

    # 用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='skills',
        verbose_name='用户',
    )
    # 技能
    skill = models.ForeignKey(
        SkillTag,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name='技能',
    )
    # 熟练度（1-5）
    proficiency = models.IntegerField('熟练度', default=1)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'member_skills'
        verbose_name = '成员技能'
        verbose_name_plural = verbose_name
        unique_together = ('user', 'skill')

    def __str__(self):
        return f'{self.user.name} - {self.skill.name}({self.proficiency})'


class FlexibleWorkSchedule(models.Model):
    """
    灵活工时模型（架构预留，第二期实现）
    记录成员在某段时间的可用工时和状态
    """

    # 用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='work_schedules',
        verbose_name='用户',
    )
    # 时段开始
    period_start = models.DateField('时段开始')
    # 时段结束
    period_end = models.DateField('时段结束')
    # 可用工时
    work_hours = models.DecimalField('可用工时', max_digits=5, decimal_places=1, default=0)
    # 工时明细（JSON格式）
    detail = models.JSONField('工时明细', default=dict, blank=True)
    # 是否可以线下
    can_offline = models.BooleanField('可以线下', default=False)
    # 是否可以紧急任务
    can_urgent = models.BooleanField('可以紧急任务', default=False)
    # 是否已饱和
    is_saturated = models.BooleanField('已饱和', default=False)
    # 备注
    notes = models.TextField('备注', blank=True, default='')
    # 填写时间
    filled_at = models.DateTimeField('填写时间', auto_now_add=True)

    class Meta:
        db_table = 'flexible_work_schedules'
        verbose_name = '灵活工时'
        verbose_name_plural = verbose_name
        # 同一用户同一时段唯一
        unique_together = ('user', 'period_start')
        ordering = ['-period_start']

    def __str__(self):
        return f'{self.user.name} ({self.period_start} ~ {self.period_end})'
