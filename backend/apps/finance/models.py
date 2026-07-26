"""
经费管理模型
包含 FinanceBudget（经费总表）、FinanceExpense（经费明细）、FinanceReceipt（票据图片）
关键：经费明细和票据对所有认证用户可见（权限 IsAuthenticated 即可读取）
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.projects.models import Project
from apps.common.soft_delete import SoftDeleteMixin, SoftDeleteManager


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
        """剩余金额 = 总收入 - 已用金额"""
        return self.total_income - self.used_amount


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
        PENDING = 'pending', '待审核'
        APPROVED = 'approved', '已审核'
        REJECTED = 'rejected', '已驳回'
        PAID = 'paid', '已付款'
        NOT_REQUIRED = 'not_required', '无需报销'

    # 所属项目
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='expenses',
        verbose_name='所属项目',
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

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='finance_incomes',
        verbose_name='所属项目',
    )
    title = models.CharField('收入标题', max_length=200)
    amount = models.DecimalField('收入金额', max_digits=12, decimal_places=2)
    income_type = models.CharField(
        '收入类型',
        max_length=20,
        choices=IncomeType.choices,
        default=IncomeType.OTHER,
    )
    income_date = models.DateField('收入日期')
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


class FinanceReceipt(models.Model):
    """
    票据图片模型
    每笔经费明细可以关联多张票据图片
    关键：票据对所有认证用户可见
    """

    # 关联经费明细
    expense = models.ForeignKey(
        FinanceExpense,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name='关联经费明细',
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

    def __str__(self):
        return f'{self.expense.title} - 票据'
