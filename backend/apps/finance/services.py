"""经费汇总、流程通知等领域服务。"""
from decimal import Decimal

from django.db.models import Sum

from .models import FinanceBudget, FinanceExpense, FinanceIncome


ZERO = Decimal('0')


def recalculate_project_budget(project_id):
    """
    从收入流水和逐笔报销状态重算项目预算缓存。

    FinanceBudget 的金额字段继续保留以兼容既有 API；收入流水存在后，
    奖金/其他收入以流水为准。已付款及无需报销计入已用，待审核和已审核
    计入待报销。
    """
    if not project_id:
        return None

    incomes = FinanceIncome.objects.filter(project_id=project_id)
    expenses = FinanceExpense.objects.filter(project_id=project_id)
    budget = (
        FinanceBudget.objects.filter(project_id=project_id)
        .order_by('-updated_at', '-id')
        .first()
    )
    if budget is None:
        # 项目级联删除完成后不要被信号重新创建空预算。
        if not incomes.exists() and not expenses.exists():
            return None
        budget = FinanceBudget.objects.create(project_id=project_id)

    if incomes.exists():
        bonus_amount = (
            incomes.filter(income_type=FinanceIncome.IncomeType.BONUS)
            .aggregate(total=Sum('amount'))['total']
            or ZERO
        )
        other_income = (
            incomes.exclude(income_type=FinanceIncome.IncomeType.BONUS)
            .aggregate(total=Sum('amount'))['total']
            or ZERO
        )
    else:
        # 兼容迁移前或外部系统直接维护的预算收入。
        bonus_amount = budget.bonus_amount
        other_income = budget.other_income

    used_amount = (
        expenses.filter(
            reimbursement_status__in=[
                FinanceExpense.ReimbursementStatus.PAID,
                FinanceExpense.ReimbursementStatus.NOT_REQUIRED,
            ]
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    pending_reimbursement = (
        expenses.filter(
            reimbursement_status__in=[
                FinanceExpense.ReimbursementStatus.PENDING,
                FinanceExpense.ReimbursementStatus.APPROVED,
            ]
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )

    total_income = bonus_amount + other_income
    committed = used_amount + pending_reimbursement
    if committed > total_income and committed > ZERO:
        budget_status = FinanceBudget.Status.ABNORMAL
    elif total_income > ZERO and committed >= total_income * Decimal('0.80'):
        budget_status = FinanceBudget.Status.WARNING
    else:
        budget_status = FinanceBudget.Status.NORMAL

    FinanceBudget.objects.filter(pk=budget.pk).update(
        bonus_amount=bonus_amount,
        other_income=other_income,
        used_amount=used_amount,
        pending_reimbursement=pending_reimbursement,
        status=budget_status,
    )
    budget.refresh_from_db()
    return budget


def finance_project_recipients(project, exclude_user=None):
    """返回需要关注项目财务变动的活跃成员，自动去重。"""
    from apps.projects.models import ProjectMember
    from apps.users.models import User

    user_ids = set(
        ProjectMember.objects.filter(
            project=project,
            status__in=[
                ProjectMember.Status.ACTIVE,
                ProjectMember.Status.ON_LEAVE,
            ],
            user__is_active=True,
        )
        .values_list('user_id', flat=True)
    )
    if project.leader_id:
        user_ids.add(project.leader_id)
    if exclude_user and getattr(exclude_user, 'id', None):
        user_ids.discard(exclude_user.id)
    return list(User.objects.filter(
        id__in=user_ids,
        is_active=True,
        membership_status__in=['active', 'on_leave'],
    ))


def notify_finance_change(project, title, content, sender=None, ref_type='', ref_id=None):
    """向项目相关成员发送可由账户偏好关闭的经费更新通知。"""
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService

    return NotificationService.bulk_create_and_send_email(
        recipients=finance_project_recipients(project, exclude_user=sender),
        title=title,
        content=content,
        category=Notification.NotificationType.FINANCE,
        ref_type=ref_type,
        ref_id=ref_id,
        sender=sender,
        priority=Notification.Priority.NORMAL,
    )
