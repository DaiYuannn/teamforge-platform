"""
经费管理模型
包含 FinanceBudget（经费总表）、FinanceExpense（经费明细）、FinanceReceipt（票据图片）
关键：经费明细和票据对所有认证用户可见（权限 IsAuthenticated 即可读取）
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.projects.models import Project
from apps.common.soft_delete import SoftDeleteMixin, SoftDeleteManager


def _check_constraint(*, condition, name):
    """Build CheckConstraint on both Django 5.0 (check) and 6.x (condition)."""
    try:
        return models.CheckConstraint(condition=condition, name=name)
    except TypeError:
        return models.CheckConstraint(check=condition, name=name)


def validate_allocation_scope(record, competition_entries):
    """Validate the tenant/event boundary for a cross-project allocation set.

    Existing allocations that only target the anchor project keep their former
    behaviour and may span several competitions.  Once any target belongs to a
    different project, every target must belong to one concrete competition
    edition and every involved project must resolve to that edition's root
    organization.
    """
    entries = list(competition_entries)
    if not entries or all(
        entry.project_id == record.project_id
        for entry in entries
    ):
        return

    event_ids = {entry.event_id for entry in entries}
    if None in event_ids or len(event_ids) != 1:
        raise ValidationError(
            '跨项目分摊只能选择同一比赛届次下的参赛条目'
        )

    from apps.common.team_models import Team
    from common.project_access import (
        active_user_root_team_ids,
        project_root_team_ids,
    )

    event = entries[0].event
    event_root_id = None
    if event.organization_id:
        event_root_id = event.organization.parent_id or event.organization_id

    active_roots = list(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)[:2]
    )
    projects = {record.project_id: record.project}
    projects.update({entry.project_id: entry.project for entry in entries})
    project_roots = []
    for project in projects.values():
        root_ids = set(project_root_team_ids(project))
        if not root_ids and project.leader_id:
            root_ids = set(active_user_root_team_ids(project.leader))
        if not root_ids and len(active_roots) == 1:
            # Legacy unlinked projects remain compatible in a single-root
            # deployment, exactly as project visibility does elsewhere.
            root_ids = {active_roots[0]}
        project_roots.append(root_ids)

    if event_root_id:
        if any(root_ids != {event_root_id} for root_ids in project_roots):
            raise ValidationError(
                '跨项目分摊的参赛条目和锚点项目必须属于比赛届次所在的同一总团队'
            )
        return

    if all(not root_ids for root_ids in project_roots) and not active_roots:
        # Pre-Team legacy installation: there is no tenant boundary to cross.
        return
    if (
        not project_roots
        or any(len(root_ids) != 1 for root_ids in project_roots)
        or len({next(iter(root_ids)) for root_ids in project_roots}) != 1
    ):
        raise ValidationError(
            '跨项目分摊只能发生在同一根组织授权范围内'
        )


class FinanceBudget(models.Model):
    """
    经费总表模型
    每个项目一个经费总表，记录奖金、收入、已用、待报销等
    """

    class Status(models.TextChoices):
        """经费状态"""
        NORMAL = 'normal', '正常'
        WARNING = 'warning', '预警'
        ABNORMAL = 'abnormal', '异常'

    # 所属项目
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='budgets',
        verbose_name='所属项目',
    )
    # 奖金总额
    bonus_amount = models.DecimalField('奖金总额', max_digits=12, decimal_places=2, default=Decimal('0'))
    # 其他收入
    other_income = models.DecimalField('其他收入', max_digits=12, decimal_places=2, default=Decimal('0'))
    # 核定的预计支出上限；与实际到账收入分开，0 表示沿用累计收入作为兼容基准。
    planned_amount = models.DecimalField(
        '核定预算上限',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
    )
    # 已用金额
    used_amount = models.DecimalField('已用金额', max_digits=12, decimal_places=2, default=Decimal('0'))
    # 待报销金额
    pending_reimbursement = models.DecimalField('待报销金额', max_digits=12, decimal_places=2, default=Decimal('0'))
    # 经费状态
    status = models.CharField(
        '经费状态',
        max_length=20,
        choices=Status.choices,
        default=Status.NORMAL,
    )
    # 统计周期
    period = models.CharField('统计周期', max_length=20, blank=True, default='')
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'finance_budgets'
        verbose_name = '经费总表'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.project.name} - 经费总表'

    @property
    def total_income(self):
        """总收入 = 奖金 + 其他收入"""
        return self.bonus_amount + self.other_income

    @property
    def remaining_amount(self):
        """账面余额 = 累计收入 - 已完成付款支出（兼容旧接口）。"""
        return self.total_income - self.used_amount

    @property
    def committed_amount(self):
        """已发生并进入流程的支出 = 已完成付款 + 待审核/待付款。"""
        return self.used_amount + self.pending_reimbursement

    @property
    def budget_basis(self):
        """预算控制基准；未设置核定上限的旧数据沿用累计收入。"""
        if self.planned_amount > Decimal('0'):
            return self.planned_amount
        return self.total_income

    @property
    def available_amount(self):
        """可继续承诺额度 = 控制基准 - 已发生支出。"""
        return self.budget_basis - self.committed_amount


class FinanceExpense(SoftDeleteMixin, models.Model):
    """
    经费明细模型
    记录每笔经费支出
    关键：经费明细对所有认证用户可见
    支持软删除（回收站）：删除后进入回收站，可恢复或永久删除
    """

    # 默认管理器：仅返回未软删除的经费明细；回收站请使用 all_objects
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Category(models.TextChoices):
        """经费类别"""
        MATERIAL = 'material', '材料费'
        EQUIPMENT = 'equipment', '设备费'
        PRINTING = 'printing', '打印费'
        TRAVEL = 'travel', '差旅费'
        SOFTWARE = 'software', '软件费'
        COMPETITION_FEE = 'competition_fee', '比赛报名费'
        PROMOTION = 'promotion', '推广费'
        LABOR = 'labor', '劳务费'
        OTHER = 'other', '其他'

    class ReimbursementStatus(models.TextChoices):
        """逐笔报销状态。"""

        DRAFT = 'draft', '草稿'
        PENDING = 'pending', '待报销审核'
        APPROVED = 'approved', '审核通过·待打款'
        PARTIALLY_PAID = 'partial_paid', '部分支付'
        PAYMENT_EXCEPTION = 'payment_exception', '付款异常'
        REJECTED = 'rejected', '已驳回'
        PAID = 'paid', '已打款·报销完成'
        NOT_REQUIRED = 'not_required', '无需报销'

    # 所属项目
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='expenses',
        verbose_name='所属项目',
    )
    competition_entry = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.PROTECT,
        related_name='finance_expenses',
        verbose_name='参赛条目',
        null=True,
        blank=True,
    )
    # 支出标题
    title = models.CharField('支出标题', max_length=200)
    # 金额
    amount = models.DecimalField('金额', max_digits=12, decimal_places=2)
    # 经办人
    spender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='expenses',
        verbose_name='经办人',
        null=True, blank=True,
    )
    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='received_reimbursements',
        verbose_name='实际收款人',
        null=True,
        blank=True,
    )
    # 支出日期
    expense_date = models.DateField('支出日期')
    # 经费类别
    category = models.CharField(
        '经费类别',
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    # 用途说明
    purpose = models.TextField('用途说明', blank=True, default='')
    # 审核人
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewed_expenses',
        verbose_name='审核人',
        null=True, blank=True,
    )
    # 报销流程
    reimbursement_status = models.CharField(
        '报销状态',
        max_length=20,
        choices=ReimbursementStatus.choices,
        default=ReimbursementStatus.DRAFT,
        db_index=True,
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='submitted_reimbursements',
        verbose_name='报销申请人',
        null=True,
        blank=True,
    )
    applied_at = models.DateTimeField('报销申请时间', null=True, blank=True)
    reviewed_at = models.DateTimeField('报销审核时间', null=True, blank=True)
    review_opinion = models.TextField('报销审核意见', blank=True, default='')
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='paid_reimbursements',
        verbose_name='付款登记人',
        null=True,
        blank=True,
    )
    paid_at = models.DateTimeField('付款时间', null=True, blank=True)
    payment_method = models.CharField('付款方式', max_length=50, blank=True, default='')
    payment_reference = models.CharField('付款流水号', max_length=100, blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'finance_expenses'
        verbose_name = '经费明细'
        verbose_name_plural = verbose_name
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f'{self.project.name} - {self.title}({self.amount})'

    def clean(self):
        super().clean()
        if (
            self.competition_entry_id
            and self.project_id
            and self.competition_entry.project_id != self.project_id
        ):
            raise ValidationError({'competition_entry': '参赛条目必须属于所选项目'})

    @property
    def fund_scope(self):
        if self.competition_entry_id:
            return 'competition_entry'
        if self.pk and self.allocations.exists():
            return 'allocated'
        return 'project_common'

    @property
    def paid_amount(self):
        if not self.pk:
            return Decimal('0')
        return (
            self.payments.filter(
                status=FinancePayment.Status.COMPLETED,
            ).aggregate(total=models.Sum('amount'))['total']
            or Decimal('0')
        )

    @property
    def remaining_payable(self):
        return max(Decimal('0'), self.amount - self.paid_amount)

    def submit_reimbursement(self, applicant):
        """提交或重新提交报销申请。"""
        if self.reimbursement_status not in {
            self.ReimbursementStatus.DRAFT,
            self.ReimbursementStatus.REJECTED,
        }:
            raise ValueError('仅草稿或已驳回的支出可以提交报销')
        self.reimbursement_status = self.ReimbursementStatus.PENDING
        self.applied_by = applicant
        self.applied_at = timezone.now()
        self.reviewer = None
        self.reviewed_at = None
        self.review_opinion = ''
        self.paid_by = None
        self.paid_at = None
        self.payment_method = ''
        self.payment_reference = ''
        self.save()

    def review_reimbursement(self, reviewer, approved, opinion=''):
        """审核一笔待审核报销。"""
        if self.reimbursement_status != self.ReimbursementStatus.PENDING:
            raise ValueError('仅待审核的报销可以审核')
        self.reimbursement_status = (
            self.ReimbursementStatus.APPROVED
            if approved
            else self.ReimbursementStatus.REJECTED
        )
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.review_opinion = opinion
        self.save()

    def mark_paid(self, operator, payment_method='', payment_reference=''):
        """登记付款完成。"""
        if self.reimbursement_status != self.ReimbursementStatus.APPROVED:
            raise ValueError('仅已审核的报销可以登记付款')
        self.reimbursement_status = self.ReimbursementStatus.PAID
        self.paid_by = operator
        self.paid_at = timezone.now()
        self.payment_method = payment_method
        self.payment_reference = payment_reference
        self.save()


class FinanceIncome(models.Model):
    """项目收入流水，是预算收入汇总的可追溯数据源。"""

    class IncomeType(models.TextChoices):
        BONUS = 'bonus', '比赛奖金'
        GRANT = 'grant', '项目拨款'
        SPONSORSHIP = 'sponsorship', '赞助收入'
        REFUND = 'refund', '退款入账'
        OTHER = 'other', '其他收入'

    class Stage(models.TextChoices):
        EXPECTED = 'expected', '预计收入'
        CONFIRMED = 'confirmed', '已确认应收'
        RECEIVED = 'received', '已到账'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='finance_incomes',
        verbose_name='所属项目',
    )
    competition_entry = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.PROTECT,
        related_name='finance_incomes',
        verbose_name='参赛条目',
        null=True,
        blank=True,
    )
    title = models.CharField('收入标题', max_length=200)
    amount = models.DecimalField('收入金额', max_digits=12, decimal_places=2)
    income_type = models.CharField(
        '收入类型',
        max_length=20,
        choices=IncomeType.choices,
        default=IncomeType.OTHER,
    )
    stage = models.CharField(
        '收入阶段',
        max_length=20,
        choices=Stage.choices,
        default=Stage.RECEIVED,
        db_index=True,
    )
    income_date = models.DateField('收入日期')
    confirmed_at = models.DateTimeField('确认应收时间', null=True, blank=True)
    received_at = models.DateTimeField('到账时间', null=True, blank=True)
    source = models.CharField('收入来源', max_length=200, blank=True, default='')
    reference_number = models.CharField('入账凭证号', max_length=100, blank=True, default='')
    note = models.TextField('备注', blank=True, default='')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='recorded_finance_incomes',
        verbose_name='登记人',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'finance_incomes'
        verbose_name = '收入流水'
        verbose_name_plural = verbose_name
        ordering = ['-income_date', '-created_at']

    def __str__(self):
        return f'{self.project.name} - {self.title}({self.amount})'

    def clean(self):
        super().clean()
        if (
            self.competition_entry_id
            and self.project_id
            and self.competition_entry.project_id != self.project_id
        ):
            raise ValidationError({'competition_entry': '参赛条目必须属于所选项目'})

    @property
    def fund_scope(self):
        if self.competition_entry_id:
            return 'competition_entry'
        if self.pk and self.allocations.exists():
            return 'allocated'
        return 'project_common'


class FinanceExpenseAllocation(models.Model):
    """将一笔支出原子分摊至多个参赛条目。"""

    expense = models.ForeignKey(
        FinanceExpense,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name='支出',
    )
    competition_entry = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.PROTECT,
        related_name='expense_allocations',
        verbose_name='参赛条目',
    )
    amount = models.DecimalField('分摊金额', max_digits=12, decimal_places=2)
    note = models.TextField('分摊说明', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'finance_expense_allocations'
        verbose_name = '支出分摊'
        verbose_name_plural = verbose_name
        ordering = ['competition_entry_id', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=('expense', 'competition_entry'),
                name='uniq_expense_competition_allocation',
            ),
            _check_constraint(
                condition=models.Q(amount__gt=0),
                name='finance_expense_allocation_amount_gt_zero',
            ),
        ]

    def clean(self):
        super().clean()
        if self.expense_id and self.expense.competition_entry_id:
            raise ValidationError('直接关联参赛条目的支出不能再进行分摊')
        if self.expense_id and self.competition_entry_id:
            siblings = (
                self.expense.allocations.exclude(pk=self.pk)
                .select_related(
                    'competition_entry__project__leader',
                    'competition_entry__event__organization',
                )
            )
            validate_allocation_scope(
                self.expense,
                [
                    self.competition_entry,
                    *[row.competition_entry for row in siblings],
                ],
            )


class FinanceIncomeAllocation(models.Model):
    """将一笔收入原子分摊至多个参赛条目。"""

    income = models.ForeignKey(
        FinanceIncome,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name='收入',
    )
    competition_entry = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.PROTECT,
        related_name='income_allocations',
        verbose_name='参赛条目',
    )
    amount = models.DecimalField('分摊金额', max_digits=12, decimal_places=2)
    note = models.TextField('分摊说明', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'finance_income_allocations'
        verbose_name = '收入分摊'
        verbose_name_plural = verbose_name
        ordering = ['competition_entry_id', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=('income', 'competition_entry'),
                name='uniq_income_competition_allocation',
            ),
            _check_constraint(
                condition=models.Q(amount__gt=0),
                name='finance_income_allocation_amount_gt_zero',
            ),
        ]

    def clean(self):
        super().clean()
        if self.income_id and self.income.competition_entry_id:
            raise ValidationError('直接关联参赛条目的收入不能再进行分摊')
        if self.income_id and self.competition_entry_id:
            siblings = (
                self.income.allocations.exclude(pk=self.pk)
                .select_related(
                    'competition_entry__project__leader',
                    'competition_entry__event__organization',
                )
            )
            validate_allocation_scope(
                self.income,
                [
                    self.competition_entry,
                    *[row.competition_entry for row in siblings],
                ],
            )


class FinancePayment(models.Model):
    """独立付款流水；只有带凭证的 completed 付款才计入团队实际支出。"""

    class Status(models.TextChoices):
        PENDING_PROOF = 'pending_proof', '待补付款凭证'
        COMPLETED = 'completed', '已付款'
        FAILED = 'failed', '付款异常'
        REVERSED = 'reversed', '已冲正'

    expense = models.ForeignKey(
        FinanceExpense,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='报销申请',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='finance_payments_received',
        verbose_name='收款人',
        null=True,
        blank=True,
    )
    amount = models.DecimalField('付款金额', max_digits=12, decimal_places=2)
    status = models.CharField(
        '付款状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PROOF,
        db_index=True,
    )
    payment_method = models.CharField('付款方式', max_length=50)
    payment_reference = models.CharField(
        '付款流水号',
        max_length=100,
        blank=True,
        default='',
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='finance_payments_made',
        verbose_name='付款登记人',
        null=True,
        blank=True,
    )
    paid_at = models.DateTimeField('付款时间', null=True, blank=True)
    failure_reason = models.TextField('付款异常原因', blank=True, default='')
    is_legacy = models.BooleanField('历史迁移付款', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'finance_payments'
        verbose_name = '报销付款'
        verbose_name_plural = verbose_name
        ordering = ['-paid_at', '-created_at']
        constraints = [
            _check_constraint(
                condition=models.Q(amount__gt=0),
                name='finance_payment_amount_gt_zero',
            ),
        ]

    def clean(self):
        super().clean()
        if self.expense_id and self.recipient_id and self.expense.payee_id:
            if self.recipient_id != self.expense.payee_id:
                raise ValidationError({'recipient': '付款收款人必须与报销收款人一致'})
        if self.status == self.Status.FAILED and not self.failure_reason.strip():
            raise ValidationError({'failure_reason': '付款异常时必须填写原因'})
        if self.status == self.Status.COMPLETED and self.expense_id:
            completed = (
                FinancePayment.objects.filter(
                    expense_id=self.expense_id,
                    status=self.Status.COMPLETED,
                )
                .exclude(pk=self.pk)
                .aggregate(total=models.Sum('amount'))['total']
                or Decimal('0')
            )
            if completed + self.amount > self.expense.amount:
                raise ValidationError({'amount': '累计付款金额不能超过报销申请金额'})


class FinanceInternalTransfer(models.Model):
    """项目内部资金转移，不重复计入项目收入或支出。"""

    class Status(models.TextChoices):
        PENDING_PROOF = 'pending_proof', '待补转账凭证'
        COMPLETED = 'completed', '转移完成'
        FAILED = 'failed', '转移异常'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='finance_internal_transfers',
        verbose_name='所属项目',
    )
    competition_entry = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.PROTECT,
        related_name='finance_internal_transfers',
        verbose_name='参赛条目',
        null=True,
        blank=True,
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='finance_transfers_sent',
        verbose_name='转出经办人',
        null=True,
        blank=True,
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='finance_transfers_received',
        verbose_name='转入经办人',
    )
    source_label = models.CharField('外部来源', max_length=200, blank=True, default='')
    amount = models.DecimalField('转移金额', max_digits=12, decimal_places=2)
    status = models.CharField(
        '转移状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PROOF,
        db_index=True,
    )
    payment_method = models.CharField('转账方式', max_length=50)
    payment_reference = models.CharField(
        '转账流水号',
        max_length=100,
        blank=True,
        default='',
    )
    transferred_at = models.DateTimeField('转账时间', null=True, blank=True)
    failure_reason = models.TextField('异常原因', blank=True, default='')
    note = models.TextField('备注', blank=True, default='')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='recorded_finance_transfers',
        verbose_name='登记人',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'finance_internal_transfers'
        verbose_name = '项目内部资金转移'
        verbose_name_plural = verbose_name
        ordering = ['-transferred_at', '-created_at']
        constraints = [
            _check_constraint(
                condition=models.Q(amount__gt=0),
                name='finance_internal_transfer_amount_gt_zero',
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.competition_entry_id
            and self.project_id
            and self.competition_entry.project_id != self.project_id
        ):
            raise ValidationError({'competition_entry': '参赛条目必须属于所选项目'})
        if self.from_user_id and self.from_user_id == self.to_user_id:
            raise ValidationError({'to_user': '转出人与转入人不能相同'})
        if not self.from_user_id and not self.source_label.strip():
            raise ValidationError({'source_label': '外部转入必须填写资金来源'})
        if self.status == self.Status.FAILED and not self.failure_reason.strip():
            raise ValidationError({'failure_reason': '转移异常时必须填写原因'})


class FinanceLedgerEvent(models.Model):
    """资金业务事件，用于不可丢失的操作时间线。"""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='finance_ledger_events',
        verbose_name='所属项目',
    )
    expense = models.ForeignKey(
        FinanceExpense,
        on_delete=models.SET_NULL,
        related_name='ledger_events',
        null=True,
        blank=True,
    )
    income = models.ForeignKey(
        FinanceIncome,
        on_delete=models.SET_NULL,
        related_name='ledger_events',
        null=True,
        blank=True,
    )
    payment = models.ForeignKey(
        FinancePayment,
        on_delete=models.SET_NULL,
        related_name='ledger_events',
        null=True,
        blank=True,
    )
    internal_transfer = models.ForeignKey(
        FinanceInternalTransfer,
        on_delete=models.SET_NULL,
        related_name='ledger_events',
        null=True,
        blank=True,
    )
    event_type = models.CharField('事件类型', max_length=50, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='finance_ledger_events',
        null=True,
        blank=True,
    )
    from_status = models.CharField('原状态', max_length=30, blank=True, default='')
    to_status = models.CharField('新状态', max_length=30, blank=True, default='')
    amount = models.DecimalField(
        '相关金额',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    description = models.TextField('事件说明', blank=True, default='')
    metadata = models.JSONField('扩展信息', default=dict, blank=True)
    created_at = models.DateTimeField('发生时间', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'finance_ledger_events'
        verbose_name = '资金时间线事件'
        verbose_name_plural = verbose_name
        ordering = ['created_at', 'id']


class FinanceReceipt(models.Model):
    """
    票据图片模型
    每笔经费明细可以关联多张票据图片
    关键：票据对所有认证用户可见
    """

    class AttachmentType(models.TextChoices):
        INVOICE = 'invoice', '发票'
        ORIGINAL_RECEIPT = 'original_receipt', '原始票据'
        PAYMENT_PROOF = 'payment_proof', '付款回单'
        INCOME_PROOF = 'income_proof', '奖金/收入到账凭证'
        TRANSFER_PROOF = 'transfer_proof', '内部转账凭证'
        OTHER = 'other', '其他'

    # 兼容旧接口：附件归属四选一。
    expense = models.ForeignKey(
        FinanceExpense,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name='关联经费明细',
        null=True,
        blank=True,
    )
    income = models.ForeignKey(
        FinanceIncome,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name='关联收入',
        null=True,
        blank=True,
    )
    payment = models.ForeignKey(
        FinancePayment,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name='关联付款',
        null=True,
        blank=True,
    )
    internal_transfer = models.ForeignKey(
        FinanceInternalTransfer,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name='关联内部转移',
        null=True,
        blank=True,
    )
    attachment_type = models.CharField(
        '附件类型',
        max_length=30,
        choices=AttachmentType.choices,
        default=AttachmentType.INVOICE,
    )
    # 票据文件
    file = models.FileField('票据图片', upload_to='finance/receipts/')
    # 上传人
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='uploaded_receipts',
        verbose_name='上传人',
        null=True, blank=True,
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'finance_receipts'
        verbose_name = '票据图片'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        constraints = [
            _check_constraint(
                condition=(
                    models.Q(expense__isnull=False, income__isnull=True, payment__isnull=True, internal_transfer__isnull=True)
                    | models.Q(expense__isnull=True, income__isnull=False, payment__isnull=True, internal_transfer__isnull=True)
                    | models.Q(expense__isnull=True, income__isnull=True, payment__isnull=False, internal_transfer__isnull=True)
                    | models.Q(expense__isnull=True, income__isnull=True, payment__isnull=True, internal_transfer__isnull=False)
                ),
                name='finance_receipt_exactly_one_owner',
            ),
        ]

    def __str__(self):
        owner = self.expense or self.income or self.payment or self.internal_transfer
        return f'{owner} - {self.get_attachment_type_display()}'

    def clean(self):
        super().clean()
        owners = [
            self.expense_id,
            self.income_id,
            self.payment_id,
            self.internal_transfer_id,
        ]
        if sum(value is not None for value in owners) != 1:
            raise ValidationError('附件必须且只能关联一项资金记录')
