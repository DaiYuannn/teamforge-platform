"""Competition-entry workload assessment and objection models."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
import django
from django.db import models
from django.db.models import Q


CHECK_CONDITION_ARG = (
    'condition'
    if django.VERSION >= (5, 1)
    else 'check'
)


class CompetitionWorkloadAssessment(models.Model):
    """A versioned contribution-allocation decision for one competition entry."""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PUBLISHED = 'published', '已发布'
        SUPERSEDED = 'superseded', '已被新版本替代'

    competition = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.CASCADE,
        related_name='workload_assessments',
        verbose_name='比赛参赛队',
    )
    version = models.PositiveIntegerField('版本')
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    decision_note = models.TextField('评议说明', blank=True, default='')
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='decided_competition_workloads',
        verbose_name='评议人',
        null=True,
        blank=True,
    )
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    is_current = models.BooleanField('是否为当前发布版本', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'competition_workload_assessments'
        verbose_name = '比赛工作量评议'
        verbose_name_plural = verbose_name
        ordering = ['-version', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=('competition', 'version'),
                name='uniq_comp_workload_assessment_version',
            ),
            models.UniqueConstraint(
                fields=('competition',),
                condition=Q(is_current=True),
                name='uniq_current_comp_workload_assessment',
            ),
        ]

    def __str__(self):
        return f'{self.competition} v{self.version}'


class CompetitionWorkloadAllocation(models.Model):
    """One participant's percentage in a workload assessment."""

    assessment = models.ForeignKey(
        CompetitionWorkloadAssessment,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name='工作量评议',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='competition_workload_allocations',
        verbose_name='成员',
    )
    percentage = models.DecimalField(
        '贡献比例',
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )
    rationale = models.TextField('评议依据', blank=True, default='')

    class Meta:
        db_table = 'competition_workload_allocations'
        verbose_name = '比赛工作量分配'
        verbose_name_plural = verbose_name
        ordering = ['user_id']
        constraints = [
            models.UniqueConstraint(
                fields=('assessment', 'user'),
                name='uniq_comp_workload_allocation_user',
            ),
            models.CheckConstraint(
                name='comp_workload_percentage_0_100',
                **{
                    CHECK_CONDITION_ARG: (
                        Q(percentage__gte=0) & Q(percentage__lte=100)
                    ),
                },
            ),
        ]

    def __str__(self):
        return f'{self.assessment} - {self.user}: {self.percentage}%'


class CompetitionWorkloadObjection(models.Model):
    """A participant's objection to a published allocation."""

    class Status(models.TextChoices):
        OPEN = 'open', '待处理'
        RESOLVED = 'resolved', '已采纳处理'
        REJECTED = 'rejected', '未采纳'

    allocation = models.ForeignKey(
        CompetitionWorkloadAllocation,
        on_delete=models.CASCADE,
        related_name='objections',
        verbose_name='工作量分配',
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='competition_workload_objections',
        verbose_name='提出人',
    )
    reason = models.TextField('异议理由')
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    response = models.TextField('处理回复', blank=True, default='')
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='resolved_competition_workload_objections',
        verbose_name='处理人',
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField('处理时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'competition_workload_objections'
        verbose_name = '比赛工作量异议'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=('allocation', 'raised_by'),
                condition=Q(status='open'),
                name='uniq_open_comp_workload_objection',
            ),
        ]

    def __str__(self):
        return f'{self.raised_by} -> {self.allocation} ({self.status})'
