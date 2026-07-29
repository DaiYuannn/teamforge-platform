"""Project/competition-entry traceability summaries, detail, timeline and todos."""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.views import APIView

from apps.competitions.models import Competition, CompetitionEvent
from apps.projects.models import Project
from common.permissions import IsInternalTeamMember
from common.project_access import scope_project_queryset
from common.response import error_response, success_response
from .models import (
    FinanceExpense,
    FinanceExpenseAllocation,
    FinanceIncome,
    FinanceIncomeAllocation,
    FinanceInternalTransfer,
    FinanceLedgerEvent,
    FinancePayment,
    FinanceReceipt,
)
from .permissions import can_manage_finance, can_pay_finance, can_review_expense
from .serializers import (
    FinanceExpenseSerializer,
    FinanceIncomeSerializer,
    FinanceInternalTransferSerializer,
    FinanceLedgerEventSerializer,
    FinancePaymentSerializer,
)


ZERO = Decimal('0')
CENT = Decimal('0.01')
RESERVING_STATUSES = {
    FinanceExpense.ReimbursementStatus.PENDING,
    FinanceExpense.ReimbursementStatus.APPROVED,
    FinanceExpense.ReimbursementStatus.PARTIALLY_PAID,
    FinanceExpense.ReimbursementStatus.PAYMENT_EXCEPTION,
}


def _money(value):
    return str((value or ZERO).quantize(CENT, rounding=ROUND_HALF_UP))


def _sum_dicts(items):
    keys = {
        'expected_bonus',
        'confirmed_bonus',
        'received_bonus',
        'received_income',
        'recorded_expense',
        'paid_expense',
        'reserved',
    }
    result = {key: ZERO for key in keys}
    for item in items:
        for key in keys:
            result[key] += Decimal(str(item.get(key, ZERO)))
    return result


def _serialize_totals(totals):
    return {key: _money(value) for key, value in totals.items()}


def _payment_total(expense):
    prefetched = getattr(expense, '_prefetched_objects_cache', {}).get('payments')
    if prefetched is not None:
        total = sum(
            (
                payment.amount
                for payment in prefetched
                if payment.status == FinancePayment.Status.COMPLETED
            ),
            ZERO,
        )
        if (
            total == ZERO
            and expense.reimbursement_status
            == FinanceExpense.ReimbursementStatus.PAID
            and not prefetched
        ):
            return expense.amount
        return total
    total = (
        expense.payments.filter(
            status=FinancePayment.Status.COMPLETED,
        ).aggregate(total=Sum('amount'))['total']
        or ZERO
    )
    if (
        total == ZERO
        and expense.reimbursement_status
        == FinanceExpense.ReimbursementStatus.PAID
        and not expense.payments.exists()
    ):
        return expense.amount
    return total


def _income_totals_for_entry(entry):
    direct = FinanceIncome.objects.filter(competition_entry=entry)
    allocated = FinanceIncomeAllocation.objects.filter(
        competition_entry=entry,
    ).select_related('income')
    totals = {
        'expected_bonus': ZERO,
        'confirmed_bonus': ZERO,
        'received_bonus': ZERO,
        'received_income': ZERO,
    }
    for income in direct:
        amount = income.amount
        if income.stage == FinanceIncome.Stage.RECEIVED:
            totals['received_income'] += amount
        if income.income_type == FinanceIncome.IncomeType.BONUS:
            totals[f'{income.stage}_bonus'] += amount
    for allocation in allocated:
        income = allocation.income
        amount = allocation.amount
        if income.stage == FinanceIncome.Stage.RECEIVED:
            totals['received_income'] += amount
        if income.income_type == FinanceIncome.IncomeType.BONUS:
            totals[f'{income.stage}_bonus'] += amount
    return totals


def _expense_totals_for_entry(entry):
    direct = list(
        FinanceExpense.objects.filter(competition_entry=entry)
        .prefetch_related('payments')
    )
    allocated = list(
        FinanceExpenseAllocation.objects.filter(
            competition_entry=entry,
        )
        .select_related('expense')
        .prefetch_related('expense__payments')
    )
    totals = {
        'recorded_expense': ZERO,
        'paid_expense': ZERO,
        'reserved': ZERO,
    }
    for expense in direct:
        if expense.reimbursement_status in {
            FinanceExpense.ReimbursementStatus.DRAFT,
            FinanceExpense.ReimbursementStatus.REJECTED,
        }:
            continue
        paid = min(expense.amount, _payment_total(expense))
        totals['recorded_expense'] += expense.amount
        totals['paid_expense'] += (
            expense.amount
            if expense.reimbursement_status
            == FinanceExpense.ReimbursementStatus.NOT_REQUIRED
            else paid
        )
        if expense.reimbursement_status in RESERVING_STATUSES:
            totals['reserved'] += max(ZERO, expense.amount - paid)
    for allocation in allocated:
        expense = allocation.expense
        if expense.reimbursement_status in {
            FinanceExpense.ReimbursementStatus.DRAFT,
            FinanceExpense.ReimbursementStatus.REJECTED,
        }:
            continue
        paid = min(expense.amount, _payment_total(expense))
        ratio = allocation.amount / expense.amount if expense.amount else ZERO
        attributed_paid = (paid * ratio).quantize(CENT, rounding=ROUND_HALF_UP)
        totals['recorded_expense'] += allocation.amount
        totals['paid_expense'] += (
            allocation.amount
            if expense.reimbursement_status
            == FinanceExpense.ReimbursementStatus.NOT_REQUIRED
            else attributed_paid
        )
        if expense.reimbursement_status in RESERVING_STATUSES:
            totals['reserved'] += max(ZERO, allocation.amount - attributed_paid)
    return totals


def _entry_summary(entry):
    totals = {
        **_income_totals_for_entry(entry),
        **_expense_totals_for_entry(entry),
    }
    participant_rows = entry.participants.select_related('user').exclude(
        participation_status='withdrawn',
    )
    return {
        'competition_entry': entry.id,
        'entry_name': entry.entry_name or entry.project.name,
        'project': entry.project_id,
        'project_name': entry.project.name,
        'event': entry.event_id,
        'event_name': entry.event.name if entry.event_id else entry.name,
        'edition': entry.event.edition if entry.event_id else '',
        'competition_status': entry.status,
        'award_level': entry.award_level,
        'is_awarded': entry.is_awarded,
        'participants': [
            {
                'id': row.user_id,
                'name': row.user.name,
                'role': row.role,
            }
            for row in participant_rows
        ],
        'totals': _serialize_totals(totals),
    }


def _project_common_totals(project):
    incomes = FinanceIncome.objects.filter(
        project=project,
        competition_entry__isnull=True,
        allocations__isnull=True,
    )
    expenses = (
        FinanceExpense.objects.filter(
            project=project,
            competition_entry__isnull=True,
            allocations__isnull=True,
        )
        .prefetch_related('payments')
        .distinct()
    )
    totals = {
        'expected_bonus': ZERO,
        'confirmed_bonus': ZERO,
        'received_bonus': ZERO,
        'received_income': ZERO,
        'recorded_expense': ZERO,
        'paid_expense': ZERO,
        'reserved': ZERO,
    }
    for income in incomes:
        if income.stage == FinanceIncome.Stage.RECEIVED:
            totals['received_income'] += income.amount
        if income.income_type == FinanceIncome.IncomeType.BONUS:
            totals[f'{income.stage}_bonus'] += income.amount
    for expense in expenses:
        if expense.reimbursement_status in {
            FinanceExpense.ReimbursementStatus.DRAFT,
            FinanceExpense.ReimbursementStatus.REJECTED,
        }:
            continue
        paid = min(expense.amount, _payment_total(expense))
        totals['recorded_expense'] += expense.amount
        totals['paid_expense'] += (
            expense.amount
            if expense.reimbursement_status
            == FinanceExpense.ReimbursementStatus.NOT_REQUIRED
            else paid
        )
        if expense.reimbursement_status in RESERVING_STATUSES:
            totals['reserved'] += max(ZERO, expense.amount - paid)
    return totals


def _visible_projects(user):
    return scope_project_queryset(
        Project.objects.all(),
        user,
        project_lookup='',
    )


def _trace_totals_for_project(project, entry_rows):
    common = _project_common_totals(project)
    entry_totals = [
        {
            key: Decimal(value)
            for key, value in row['totals'].items()
        }
        for row in entry_rows
        if row['project'] == project.id
    ]
    return _sum_dicts([common, *entry_totals]), common


def _reservation_split_for_projects(project_ids):
    project_ids = set(project_ids)
    if not project_ids:
        return ZERO, ZERO
    expenses = (
        FinanceExpense.objects.filter(
            Q(competition_entry__project_id__in=project_ids)
            | Q(
                allocations__competition_entry__project_id__in=project_ids,
            )
            | Q(
                project_id__in=project_ids,
                competition_entry__isnull=True,
                allocations__isnull=True,
            ),
            reimbursement_status__in=RESERVING_STATUSES,
        )
        .select_related('competition_entry')
        .prefetch_related('allocations__competition_entry', 'payments')
        .distinct()
    )
    pending_review = ZERO
    approved_pending_payment = ZERO
    for expense in expenses:
        allocations = list(expense.allocations.all())
        if allocations:
            attributed_amount = sum(
                (
                    allocation.amount
                    for allocation in allocations
                    if allocation.competition_entry.project_id in project_ids
                ),
                ZERO,
            )
        elif expense.competition_entry_id:
            attributed_amount = (
                expense.amount
                if expense.competition_entry.project_id in project_ids
                else ZERO
            )
        else:
            attributed_amount = (
                expense.amount
                if expense.project_id in project_ids
                else ZERO
            )
        if attributed_amount <= ZERO:
            continue
        paid = min(expense.amount, _payment_total(expense))
        attributed_paid = (
            paid * attributed_amount / expense.amount
            if expense.amount else ZERO
        )
        remaining = max(ZERO, attributed_amount - attributed_paid)
        if (
            expense.reimbursement_status
            == FinanceExpense.ReimbursementStatus.PENDING
        ):
            pending_review += remaining
        else:
            approved_pending_payment += remaining
    return pending_review, approved_pending_payment


def _overview_metrics(projects, entry_rows):
    """Canonical top-strip metrics for the currently selected project scope."""
    project_list = list(projects)
    totals = [
        _trace_totals_for_project(project, entry_rows)[0]
        for project in project_list
    ]
    pending_review, approved_pending_payment = (
        _reservation_split_for_projects(
            project.id for project in project_list
        )
    )
    received = sum((item['received_income'] for item in totals), ZERO)
    paid = sum((item['paid_expense'] for item in totals), ZERO)
    return {
        'received_funds': _money(received),
        'pending_review_reserved': _money(pending_review),
        'approved_pending_payment': _money(approved_pending_payment),
        'actual_paid': _money(paid),
        'expected_bonus': _money(sum(
            (item['expected_bonus'] for item in totals),
            ZERO,
        )),
        'confirmed_bonus': _money(sum(
            (item['confirmed_bonus'] for item in totals),
            ZERO,
        )),
        'available_funds': _money(
            received - paid - pending_review - approved_pending_payment
        ),
    }


class FinanceTraceabilitySummaryView(APIView):
    permission_classes = [IsInternalTeamMember]

    def get(self, request):
        perspective = request.query_params.get('perspective', 'project')
        if perspective not in {'project', 'competition'}:
            return error_response(message='perspective 仅支持 project 或 competition')
        projects = _visible_projects(request.user)
        project_id = request.query_params.get('project')
        if project_id:
            projects = projects.filter(pk=project_id)
        entries = (
            Competition.objects.filter(project__in=projects)
            .select_related('project', 'event')
            .prefetch_related('participants__user')
        )
        event_id = request.query_params.get('event')
        if event_id:
            entries = entries.filter(event_id=event_id)

        entry_rows = [_entry_summary(entry) for entry in entries]
        if perspective == 'project':
            rows_by_project = defaultdict(list)
            for row in entry_rows:
                rows_by_project[row['project']].append(row)
            groups = []
            for project in projects.order_by('name', 'id'):
                project_entries = rows_by_project.get(project.id, [])
                attributed, common = _trace_totals_for_project(
                    project,
                    entry_rows,
                )
                groups.append({
                    'project': project.id,
                    'project_name': project.name,
                    'can_manage': can_manage_finance(request.user, project),
                    'can_pay': can_pay_finance(request.user, project),
                    'totals': {
                        **_serialize_totals(attributed),
                        'available': _money(
                            attributed['received_income']
                            - attributed['paid_expense']
                            - attributed['reserved']
                        ),
                        'budget_basis': _money(
                            attributed['received_income']
                        ),
                    },
                    'project_common': _serialize_totals(common),
                    'entries': project_entries,
                })
        else:
            rows_by_event = defaultdict(list)
            for row in entry_rows:
                rows_by_event[row['event']].append(row)
            events = CompetitionEvent.objects.filter(
                pk__in=[key for key in rows_by_event if key],
            ).order_by('-edition', 'name')
            groups = []
            for event in events:
                event_entries = rows_by_event[event.id]
                raw_totals = _sum_dicts(
                    [
                        {
                            key: Decimal(value)
                            for key, value in row['totals'].items()
                        }
                        for row in event_entries
                    ]
                )
                groups.append({
                    'event': event.id,
                    'event_name': event.name,
                    'edition': event.edition,
                    'organizer': event.organizer,
                    'totals': _serialize_totals(raw_totals),
                    'entries': event_entries,
                })

        response_data = {
            'perspective': perspective,
            'group_count': len(groups),
            'groups': groups,
        }
        # “可动用资金”是项目资金池口径；按某一比赛筛选时交由前端
        # 使用比赛流水计算，避免把整个项目余额误标成该比赛余额。
        if not event_id:
            response_data['metrics'] = _overview_metrics(
                projects,
                entry_rows,
            )
        return success_response(response_data)


class FinanceTraceabilityDetailView(APIView):
    permission_classes = [IsInternalTeamMember]

    def get(self, request):
        entry_id = request.query_params.get('competition_entry')
        if not entry_id:
            return error_response(message='必须提供 competition_entry')
        entry = (
            Competition.objects.filter(
                pk=entry_id,
                project__in=_visible_projects(request.user),
            )
            .select_related('project', 'event')
            .prefetch_related('participants__user')
            .first()
        )
        if entry is None:
            return error_response(message='参赛条目不存在或无权访问')

        direct_expenses = list(
            FinanceExpense.objects.filter(competition_entry=entry)
            .select_related('project', 'competition_entry__event')
            .prefetch_related(
                'receipts',
                'payments__receipts',
                'allocations__competition_entry__event',
                'allocations__competition_entry__project',
            )
        )
        expense_allocations = list(
            FinanceExpenseAllocation.objects.filter(
                competition_entry=entry,
            ).select_related('expense')
        )
        allocated_expense_map = {
            allocation.expense_id: allocation.amount
            for allocation in expense_allocations
        }
        allocated_expenses = list(
            FinanceExpense.objects.filter(pk__in=allocated_expense_map)
            .select_related('project', 'competition_entry__event')
            .prefetch_related(
                'receipts',
                'payments__receipts',
                'allocations__competition_entry__event',
                'allocations__competition_entry__project',
            )
        )
        expense_rows = []
        for expense in direct_expenses + allocated_expenses:
            data = FinanceExpenseSerializer(
                expense,
                context={'request': request},
            ).data
            data['attributed_amount'] = _money(
                allocated_expense_map.get(expense.id, expense.amount)
            )
            expense_rows.append(data)

        direct_incomes = list(
            FinanceIncome.objects.filter(competition_entry=entry)
            .select_related('project', 'competition_entry__event')
            .prefetch_related(
                'receipts',
                'allocations__competition_entry__event',
                'allocations__competition_entry__project',
            )
        )
        income_allocations = list(
            FinanceIncomeAllocation.objects.filter(
                competition_entry=entry,
            ).select_related('income')
        )
        allocated_income_map = {
            allocation.income_id: allocation.amount
            for allocation in income_allocations
        }
        allocated_incomes = list(
            FinanceIncome.objects.filter(pk__in=allocated_income_map)
            .select_related('project', 'competition_entry__event')
            .prefetch_related(
                'receipts',
                'allocations__competition_entry__event',
                'allocations__competition_entry__project',
            )
        )
        income_rows = []
        for income in direct_incomes + allocated_incomes:
            data = FinanceIncomeSerializer(
                income,
                context={'request': request},
            ).data
            data['attributed_amount'] = _money(
                allocated_income_map.get(income.id, income.amount)
            )
            income_rows.append(data)

        expense_ids = [row['id'] for row in expense_rows]
        attributed_expense_amounts = {
            row['id']: Decimal(row['attributed_amount'])
            for row in expense_rows
        }
        payments = (
            FinancePayment.objects.filter(expense_id__in=expense_ids)
            .select_related('expense__project', 'recipient', 'paid_by')
            .prefetch_related('receipts')
        )
        payment_rows = []
        for payment in payments:
            data = FinancePaymentSerializer(
                payment,
                context={'request': request},
            ).data
            attributed_expense = attributed_expense_amounts.get(
                payment.expense_id,
                payment.expense.amount,
            )
            ratio = (
                attributed_expense / payment.expense.amount
                if payment.expense.amount else ZERO
            )
            data['attributed_amount'] = _money(payment.amount * ratio)
            payment_rows.append(data)
        transfers = (
            FinanceInternalTransfer.objects.filter(competition_entry=entry)
            .select_related('project', 'from_user', 'to_user', 'recorded_by')
            .prefetch_related('receipts')
        )
        return success_response({
            'entry': _entry_summary(entry),
            'expenses': expense_rows,
            'incomes': income_rows,
            'payments': payment_rows,
            'internal_transfers': FinanceInternalTransferSerializer(
                transfers,
                many=True,
                context={'request': request},
            ).data,
        })


class FinanceTimelineView(APIView):
    permission_classes = [IsInternalTeamMember]

    def get(self, request):
        owner_fields = {
            'project': Project,
            'expense': FinanceExpense,
            'income': FinanceIncome,
            'payment': FinancePayment,
            'transfer': FinanceInternalTransfer,
        }
        supplied = [
            (key, request.query_params.get(key))
            for key in owner_fields
            if request.query_params.get(key)
        ]
        if len(supplied) != 1:
            return error_response(
                message='必须且只能提供 project、expense、income、payment 或 transfer 之一'
            )
        key, object_id = supplied[0]
        lookup = 'internal_transfer' if key == 'transfer' else key
        events = FinanceLedgerEvent.objects.filter(
            **{f'{lookup}_id': object_id},
        ).select_related('project', 'actor')
        visible_ids = _visible_projects(request.user).values_list('id', flat=True)
        events = events.filter(project_id__in=visible_ids)
        return success_response(
            FinanceLedgerEventSerializer(events, many=True).data
        )


def _expense_todo(expense, item_type, request):
    return {
        'id': expense.id,
        'type': item_type,
        'title': expense.title,
        'amount': _money(expense.amount),
        'project': expense.project_id,
        'project_name': expense.project.name,
        'competition_entry': expense.competition_entry_id,
        'competition_entry_name': (
            expense.competition_entry.entry_name
            if expense.competition_entry_id else ''
        ),
        'status': expense.reimbursement_status,
        'status_display': expense.get_reimbursement_status_display(),
        'can_review': can_review_expense(request.user, expense),
        'can_pay': can_pay_finance(request.user, expense.project),
        'created_at': expense.created_at,
    }


class FinanceFundTodoView(APIView):
    permission_classes = [IsInternalTeamMember]

    def get(self, request):
        try:
            overdue_days = max(1, int(request.query_params.get('overdue_days', 7)))
        except (TypeError, ValueError):
            return error_response(message='overdue_days 必须为正整数')
        project_ids = _visible_projects(request.user).values_list('id', flat=True)
        expenses = (
            FinanceExpense.objects.filter(project_id__in=project_ids)
            .select_related('project', 'competition_entry')
            .prefetch_related('receipts', 'payments')
        )
        groups = {
            'missing_invoice': [],
            'pending_review': [],
            'pending_payment': [],
            'missing_payment_proof': [],
            'partial_payment': [],
            'payment_exception': [],
            'overdue': [],
        }
        for expense in expenses:
            source_documents = [
                receipt for receipt in expense.receipts.all()
                if receipt.attachment_type in {
                    FinanceReceipt.AttachmentType.INVOICE,
                    FinanceReceipt.AttachmentType.ORIGINAL_RECEIPT,
                }
            ]
            if (
                not source_documents
                and expense.reimbursement_status
                in {
                    FinanceExpense.ReimbursementStatus.DRAFT,
                    FinanceExpense.ReimbursementStatus.REJECTED,
                    FinanceExpense.ReimbursementStatus.PENDING,
                }
            ):
                groups['missing_invoice'].append(
                    _expense_todo(expense, 'missing_invoice', request)
                )
            if expense.reimbursement_status == FinanceExpense.ReimbursementStatus.PENDING:
                groups['pending_review'].append(
                    _expense_todo(expense, 'pending_review', request)
                )
            if expense.reimbursement_status == FinanceExpense.ReimbursementStatus.APPROVED:
                groups['pending_payment'].append(
                    _expense_todo(expense, 'pending_payment', request)
                )
            if expense.reimbursement_status == FinanceExpense.ReimbursementStatus.PARTIALLY_PAID:
                groups['partial_payment'].append(
                    _expense_todo(expense, 'partial_payment', request)
                )
            if expense.reimbursement_status == FinanceExpense.ReimbursementStatus.PAYMENT_EXCEPTION:
                groups['payment_exception'].append(
                    _expense_todo(expense, 'payment_exception', request)
                )

        pending_proof_payments = (
            FinancePayment.objects.filter(
                expense__project_id__in=project_ids,
                status=FinancePayment.Status.PENDING_PROOF,
            )
            .select_related(
                'expense',
                'expense__project',
                'expense__competition_entry',
                'recipient',
            )
        )
        groups['missing_payment_proof'] = [
            {
                'id': payment.id,
                'type': 'missing_payment_proof',
                'title': payment.expense.title,
                'amount': _money(payment.amount),
                'project': payment.expense.project_id,
                'project_name': payment.expense.project.name,
                'competition_entry': payment.expense.competition_entry_id,
                'competition_entry_name': (
                    payment.expense.competition_entry.entry_name
                    if payment.expense.competition_entry_id else ''
                ),
                'recipient': payment.recipient_id,
                'recipient_name': payment.recipient.name if payment.recipient_id else '',
                'status': payment.status,
                'status_display': payment.get_status_display(),
                'can_pay': can_pay_finance(request.user, payment.expense.project),
                'created_at': payment.created_at,
            }
            for payment in pending_proof_payments
        ]

        cutoff = timezone.now() - timedelta(days=overdue_days)
        overdue_expenses = expenses.filter(
            reimbursement_status__in=RESERVING_STATUSES,
            created_at__lt=cutoff,
        )
        groups['overdue'] = [
            _expense_todo(expense, 'overdue', request)
            for expense in overdue_expenses
        ]
        return success_response({
            'overdue_days': overdue_days,
            'summary': {
                key: {
                    'count': len(items),
                    'amount': _money(sum(
                        (Decimal(item['amount']) for item in items),
                        ZERO,
                    )),
                }
                for key, items in groups.items()
            },
            'groups': groups,
        })
