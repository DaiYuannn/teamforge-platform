"""经费汇总、付款、分摊、时间线与流程通知等领域服务。"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    FinanceBudget,
    FinanceExpense,
    FinanceExpenseAllocation,
    FinanceIncome,
    FinanceIncomeAllocation,
    FinanceInternalTransfer,
    FinanceLedgerEvent,
    FinancePayment,
    FinanceReceipt,
    validate_allocation_scope,
)


ZERO = Decimal('0')


def record_finance_event(
    *,
    project,
    event_type,
    actor=None,
    expense=None,
    income=None,
    payment=None,
    internal_transfer=None,
    from_status='',
    to_status='',
    amount=None,
    description='',
    metadata=None,
):
    """Append one immutable business event for the finance detail timeline."""
    return FinanceLedgerEvent.objects.create(
        project=project,
        expense=expense,
        income=income,
        payment=payment,
        internal_transfer=internal_transfer,
        event_type=event_type,
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        from_status=from_status or '',
        to_status=to_status or '',
        amount=amount,
        description=description or '',
        metadata=metadata or {},
    )


def _completed_payments_by_expense(expenses):
    return {
        row['expense_id']: row['total'] or ZERO
        for row in (
            FinancePayment.objects.filter(
                expense__in=expenses,
                status=FinancePayment.Status.COMPLETED,
            )
            .values('expense_id')
            .annotate(total=Sum('amount'))
        )
    }


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
    received_incomes = incomes.filter(stage=FinanceIncome.Stage.RECEIVED)
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
            received_incomes.filter(income_type=FinanceIncome.IncomeType.BONUS)
            .aggregate(total=Sum('amount'))['total']
            or ZERO
        )
        other_income = (
            received_incomes.exclude(income_type=FinanceIncome.IncomeType.BONUS)
            .aggregate(total=Sum('amount'))['total']
            or ZERO
        )
    else:
        # 兼容迁移前或外部系统直接维护的预算收入。
        bonus_amount = budget.bonus_amount
        other_income = budget.other_income

    completed_payment_total = (
        FinancePayment.objects.filter(
            expense__in=expenses,
            status=FinancePayment.Status.COMPLETED,
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    non_reimbursable_total = (
        expenses.filter(
            reimbursement_status=FinanceExpense.ReimbursementStatus.NOT_REQUIRED,
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    legacy_paid_total = (
        expenses.filter(
            reimbursement_status=FinanceExpense.ReimbursementStatus.PAID,
            payments__isnull=True,
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    used_amount = (
        completed_payment_total
        + non_reimbursable_total
        + legacy_paid_total
    )

    reserving_expenses = expenses.filter(
        reimbursement_status__in=[
            FinanceExpense.ReimbursementStatus.PENDING,
            FinanceExpense.ReimbursementStatus.APPROVED,
            FinanceExpense.ReimbursementStatus.PARTIALLY_PAID,
            FinanceExpense.ReimbursementStatus.PAYMENT_EXCEPTION,
        ]
    )
    completed_by_expense = _completed_payments_by_expense(reserving_expenses)
    pending_reimbursement = sum(
        (
            max(
                ZERO,
                expense.amount - completed_by_expense.get(expense.id, ZERO),
            )
            for expense in reserving_expenses.only('id', 'amount')
        ),
        ZERO,
    )

    committed = used_amount + pending_reimbursement
    total_income = bonus_amount + other_income
    budget_basis = budget.planned_amount if budget.planned_amount > ZERO else total_income
    if committed > budget_basis and committed > ZERO:
        budget_status = FinanceBudget.Status.ABNORMAL
    elif budget_basis > ZERO and committed >= budget_basis * Decimal('0.80'):
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


def project_fund_totals(project_id):
    """Return the canonical project totals used by every traceability endpoint."""
    budget = recalculate_project_budget(project_id)
    incomes = FinanceIncome.objects.filter(project_id=project_id)
    expected_bonus = (
        incomes.filter(
            income_type=FinanceIncome.IncomeType.BONUS,
            stage=FinanceIncome.Stage.EXPECTED,
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    confirmed_bonus = (
        incomes.filter(
            income_type=FinanceIncome.IncomeType.BONUS,
            stage=FinanceIncome.Stage.CONFIRMED,
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    received_bonus = (
        incomes.filter(
            income_type=FinanceIncome.IncomeType.BONUS,
            stage=FinanceIncome.Stage.RECEIVED,
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    if budget is None:
        return {
            'expected_bonus': expected_bonus,
            'confirmed_bonus': confirmed_bonus,
            'received_bonus': received_bonus,
            'received_income': ZERO,
            'paid_expense': ZERO,
            'reserved': ZERO,
            'available': ZERO,
            'budget_basis': ZERO,
        }
    return {
        'expected_bonus': expected_bonus,
        'confirmed_bonus': confirmed_bonus,
        'received_bonus': received_bonus,
        'received_income': budget.total_income,
        'paid_expense': budget.used_amount,
        'reserved': budget.pending_reimbursement,
        'available': budget.available_amount,
        'budget_basis': budget.budget_basis,
    }


@transaction.atomic
def replace_allocations(record, allocations, actor=None):
    """Atomically replace a complete expense/income allocation set."""
    if record.competition_entry_id:
        raise ValidationError('直接关联参赛条目的记录不能再进行分摊')
    model = (
        FinanceExpenseAllocation
        if isinstance(record, FinanceExpense)
        else FinanceIncomeAllocation
    )
    parent_field = 'expense' if isinstance(record, FinanceExpense) else 'income'
    entries = {}
    total = ZERO
    normalized = []
    for item in allocations:
        entry = item['competition_entry']
        amount = Decimal(str(item['amount']))
        if entry.id in entries:
            raise ValidationError('同一参赛条目不能重复分摊')
        if amount <= ZERO:
            raise ValidationError('分摊金额必须大于 0')
        entries[entry.id] = True
        total += amount
        normalized.append({
            'competition_entry': entry,
            'amount': amount,
            'note': str(item.get('note', '') or ''),
        })
    if normalized and total != record.amount:
        raise ValidationError(
            f'分摊合计必须等于记录金额 {record.amount}，当前为 {total}'
        )
    validate_allocation_scope(
        record,
        [item['competition_entry'] for item in normalized],
    )
    if actor and normalized:
        from common.project_access import user_can_access_project

        target_projects = {
            item['competition_entry'].project_id: (
                item['competition_entry'].project
            )
            for item in normalized
        }
        if any(
            not user_can_access_project(actor, project)
            for project in target_projects.values()
        ):
            raise ValidationError(
                '无权将资金分摊到当前账号不可访问的项目'
            )
    getattr(record, 'allocations').all().delete()
    model.objects.bulk_create([
        model(**{parent_field: record}, **item)
        for item in normalized
    ])
    record_finance_event(
        project=record.project,
        event_type='allocation_updated',
        actor=actor,
        expense=record if isinstance(record, FinanceExpense) else None,
        income=record if isinstance(record, FinanceIncome) else None,
        amount=record.amount,
        description='更新比赛/参赛队资金分摊',
        metadata={
            'allocations': [
                {
                    'competition_entry': item['competition_entry'].id,
                    'project': item['competition_entry'].project_id,
                    'event': item['competition_entry'].event_id,
                    'amount': str(item['amount']),
                }
                for item in normalized
            ],
        },
    )
    return list(record.allocations.select_related('competition_entry'))


def sync_expense_payment_status(expense_id):
    """Synchronize the compatibility status/fields from independent payments."""
    expense = FinanceExpense.objects.filter(pk=expense_id).first()
    if expense is None:
        return None
    payments = FinancePayment.objects.filter(expense=expense)
    completed_total = (
        payments.filter(status=FinancePayment.Status.COMPLETED)
        .aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    has_failure = payments.filter(status=FinancePayment.Status.FAILED).exists()
    if completed_total >= expense.amount:
        new_status = FinanceExpense.ReimbursementStatus.PAID
    elif completed_total > ZERO:
        new_status = FinanceExpense.ReimbursementStatus.PARTIALLY_PAID
    elif has_failure:
        new_status = FinanceExpense.ReimbursementStatus.PAYMENT_EXCEPTION
    else:
        new_status = FinanceExpense.ReimbursementStatus.APPROVED

    latest_completed = (
        payments.filter(status=FinancePayment.Status.COMPLETED)
        .order_by('-paid_at', '-created_at')
        .first()
    )
    updates = {'reimbursement_status': new_status}
    if latest_completed:
        updates.update({
            'paid_by_id': latest_completed.paid_by_id,
            'paid_at': latest_completed.paid_at,
            'payment_method': latest_completed.payment_method,
            'payment_reference': latest_completed.payment_reference,
        })
    FinanceExpense.objects.filter(pk=expense.pk).update(**updates)
    recalculate_project_budget(expense.project_id)
    expense.refresh_from_db()
    return expense


@transaction.atomic
def complete_payment(payment, *, proof_file, actor):
    """Attach proof and make a payment count as actual team spending."""
    payment = FinancePayment.objects.select_for_update().select_related(
        'expense',
        'expense__project',
    ).get(pk=payment.pk)
    if payment.status == FinancePayment.Status.COMPLETED:
        raise ValidationError('付款已经完成')
    if payment.status == FinancePayment.Status.REVERSED:
        raise ValidationError('已冲正付款不能重新完成，请新建付款记录')
    if not proof_file:
        raise ValidationError('登记已付款必须上传转账凭证')
    from_status = payment.status
    payment.status = FinancePayment.Status.COMPLETED
    payment.paid_by = actor
    payment.paid_at = payment.paid_at or timezone.now()
    payment.failure_reason = ''
    payment.full_clean()
    payment.save()
    FinanceReceipt.objects.create(
        payment=payment,
        attachment_type=FinanceReceipt.AttachmentType.PAYMENT_PROOF,
        file=proof_file,
        uploaded_by=actor,
    )
    expense = sync_expense_payment_status(payment.expense_id)
    record_finance_event(
        project=payment.expense.project,
        event_type='payment_completed',
        actor=actor,
        expense=payment.expense,
        payment=payment,
        from_status=from_status,
        to_status=payment.status,
        amount=payment.amount,
        description='付款凭证已归档，计入团队实际支出',
    )
    return payment, expense


@transaction.atomic
def fail_payment(payment, *, reason, actor):
    payment = FinancePayment.objects.select_for_update().select_related(
        'expense',
        'expense__project',
    ).get(pk=payment.pk)
    if payment.status == FinancePayment.Status.COMPLETED:
        raise ValidationError('已完成付款不能直接标记异常，请先冲正')
    reason = str(reason or '').strip()
    if not reason:
        raise ValidationError('付款异常必须填写原因')
    from_status = payment.status
    payment.status = FinancePayment.Status.FAILED
    payment.failure_reason = reason
    payment.paid_by = actor
    payment.full_clean()
    payment.save()
    expense = sync_expense_payment_status(payment.expense_id)
    record_finance_event(
        project=payment.expense.project,
        event_type='payment_failed',
        actor=actor,
        expense=payment.expense,
        payment=payment,
        from_status=from_status,
        to_status=payment.status,
        amount=payment.amount,
        description=reason,
    )
    return payment, expense


@transaction.atomic
def set_income_stage(income, *, stage, actor, proof_file=None):
    income = FinanceIncome.objects.select_for_update().select_related(
        'project',
    ).get(pk=income.pk)
    allowed = {
        FinanceIncome.Stage.EXPECTED: {
            FinanceIncome.Stage.CONFIRMED,
            FinanceIncome.Stage.RECEIVED,
        },
        FinanceIncome.Stage.CONFIRMED: {FinanceIncome.Stage.RECEIVED},
        FinanceIncome.Stage.RECEIVED: set(),
    }
    if stage == income.stage:
        raise ValidationError('收入已经处于该阶段')
    if stage not in allowed.get(income.stage, set()):
        raise ValidationError('不允许执行该收入阶段转换')
    if (
        stage == FinanceIncome.Stage.RECEIVED
        and income.income_type == FinanceIncome.IncomeType.BONUS
        and not proof_file
    ):
        raise ValidationError('奖金到账必须上传到账凭证')
    from_status = income.stage
    income.stage = stage
    if stage in {FinanceIncome.Stage.CONFIRMED, FinanceIncome.Stage.RECEIVED}:
        income.confirmed_at = income.confirmed_at or timezone.now()
    if stage == FinanceIncome.Stage.RECEIVED:
        income.received_at = timezone.now()
    income.save(update_fields=['stage', 'confirmed_at', 'received_at', 'updated_at'])
    if proof_file:
        FinanceReceipt.objects.create(
            income=income,
            attachment_type=FinanceReceipt.AttachmentType.INCOME_PROOF,
            file=proof_file,
            uploaded_by=actor,
        )
    record_finance_event(
        project=income.project,
        event_type='income_stage_changed',
        actor=actor,
        income=income,
        from_status=from_status,
        to_status=stage,
        amount=income.amount,
        description='收入阶段已更新',
    )
    recalculate_project_budget(income.project_id)
    return income


@transaction.atomic
def complete_internal_transfer(transfer, *, proof_file, actor):
    transfer = FinanceInternalTransfer.objects.select_for_update().select_related(
        'project',
    ).get(pk=transfer.pk)
    if transfer.status == FinanceInternalTransfer.Status.COMPLETED:
        raise ValidationError('内部转移已经完成')
    if not proof_file:
        raise ValidationError('内部转移完成必须上传转账凭证')
    from_status = transfer.status
    transfer.status = FinanceInternalTransfer.Status.COMPLETED
    transfer.transferred_at = transfer.transferred_at or timezone.now()
    transfer.failure_reason = ''
    transfer.full_clean()
    transfer.save()
    FinanceReceipt.objects.create(
        internal_transfer=transfer,
        attachment_type=FinanceReceipt.AttachmentType.TRANSFER_PROOF,
        file=proof_file,
        uploaded_by=actor,
    )
    record_finance_event(
        project=transfer.project,
        event_type='internal_transfer_completed',
        actor=actor,
        internal_transfer=transfer,
        from_status=from_status,
        to_status=transfer.status,
        amount=transfer.amount,
        description='内部转账凭证已归档；该流水不重复计入收支',
    )
    return transfer


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
