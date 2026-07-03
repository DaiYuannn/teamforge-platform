"""
经费管理模型
包含 FinanceBudget（经费总表）、FinanceExpense（经费明细）、FinanceReceipt（票据图片）
关键：经费明细和票据对所有认证用户可见（权限 IsAuthenticated 即可读取）
"""
from decimal import Decimal
from django.db import models
from django.conf import settings

from apps.projects.models import Project


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


class FinanceExpense(models.Model):
    """
    经费明细模型
    记录每笔经费支出
    关键：经费明细对所有认证用户可见
    """

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
