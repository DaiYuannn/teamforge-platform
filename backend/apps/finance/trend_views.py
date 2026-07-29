"""
经费趋势分析视图
- FinanceTrendView: 月度支出趋势、类别分布
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.views import APIView

from common.permissions import IsInternalTeamMember
from common.project_access import scope_project_queryset
from common.response import success_response
from common.schema import success_response_schema
from .models import FinanceExpense, FinancePayment


class FinanceTrendView(APIView):
    """
    经费趋势分析视图
    GET /api/v1/finance/trends/
    返回月度支出趋势和类别分布
    支持按 project 筛选
    """
    permission_classes = [IsInternalTeamMember]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='project',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='按项目 ID 筛选支出。',
            ),
        ],
        responses={
            200: success_response_schema(
                'FinanceTrendResponse',
                inline_serializer(
                    name='FinanceTrendData',
                    fields={
                        'total_expense': serializers.FloatField(),
                        'monthly_trend': inline_serializer(
                            name='FinanceMonthlyTrendItem',
                            fields={
                                'month': serializers.RegexField(r'^\d{4}-\d{2}$'),
                                'amount': serializers.FloatField(),
                            },
                            many=True,
                        ),
                        'category_breakdown': serializers.DictField(
                            child=inline_serializer(
                                name='FinanceCategoryBreakdownItem',
                                fields={
                                    'label': serializers.CharField(),
                                    'amount': serializers.FloatField(),
                                },
                            ),
                        ),
                        'category_percentage': serializers.DictField(
                            child=serializers.FloatField(),
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        params = request.query_params
        project_id = params.get('project')

        queryset = scope_project_queryset(
            FinanceExpense.objects.all(),
            request.user,
            project_lookup='project',
        ).exclude(
            reimbursement_status__in=[
                FinanceExpense.ReimbursementStatus.DRAFT,
                FinanceExpense.ReimbursementStatus.REJECTED,
            ],
        ).select_related(
            'competition_entry',
        ).prefetch_related(
            'allocations__competition_entry',
        )
        if project_id:
            queryset = queryset.filter(
                Q(competition_entry__project_id=project_id)
                | Q(allocations__competition_entry__project_id=project_id)
                | Q(
                    project_id=project_id,
                    competition_entry__isnull=True,
                    allocations__isnull=True,
                )
            ).distinct()

        def attributed_amount(expense):
            if not project_id:
                return expense.amount
            allocations = list(expense.allocations.all())
            if allocations:
                return sum(
                    (
                        allocation.amount
                        for allocation in allocations
                        if str(allocation.competition_entry.project_id)
                        == str(project_id)
                    ),
                    Decimal('0'),
                )
            if expense.competition_entry_id:
                return (
                    expense.amount
                    if str(expense.competition_entry.project_id)
                    == str(project_id)
                    else Decimal('0')
                )
            return (
                expense.amount
                if str(expense.project_id) == str(project_id)
                else Decimal('0')
            )

        # 月度趋势与支出结构统一使用“真实完成付款”；无需报销记录按
        # expense_date 计入。待审核、待付款只占额度，不冒充实际支出。
        monthly_trend = {}
        category_amounts = {
            category_key: Decimal('0')
            for category_key, _ in FinanceExpense.Category.choices
        }
        completed_payments = (
            FinancePayment.objects.filter(
                expense__in=queryset,
                status=FinancePayment.Status.COMPLETED,
            )
            .select_related('expense')
        )
        for payment in completed_payments:
            expense_share = attributed_amount(payment.expense)
            amount = (
                payment.amount * expense_share / payment.expense.amount
                if payment.expense.amount else Decimal('0')
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            effective_date = payment.paid_at.date() if payment.paid_at else payment.expense.expense_date
            month_key = effective_date.strftime('%Y-%m')
            monthly_trend.setdefault(month_key, Decimal('0'))
            monthly_trend[month_key] += amount
            category_amounts[payment.expense.category] += amount
        for expense in queryset.filter(
            reimbursement_status=FinanceExpense.ReimbursementStatus.NOT_REQUIRED,
        ):
            amount = attributed_amount(expense)
            if expense.expense_date:
                month_key = expense.expense_date.strftime('%Y-%m')
                monthly_trend.setdefault(month_key, Decimal('0'))
                monthly_trend[month_key] += amount
            category_amounts[expense.category] += amount
        for expense in queryset.filter(
            reimbursement_status=FinanceExpense.ReimbursementStatus.PAID,
            payments__isnull=True,
        ):
            amount = attributed_amount(expense)
            if expense.expense_date:
                month_key = expense.expense_date.strftime('%Y-%m')
                monthly_trend.setdefault(month_key, Decimal('0'))
                monthly_trend[month_key] += amount
            category_amounts[expense.category] += amount

        monthly_data = [
            {
                'month': month,
                'amount': float(amount),
            }
            for month, amount in sorted(monthly_trend.items())
        ]

        # 类别分布
        category_breakdown = {}
        for category_key, category_label in FinanceExpense.Category.choices:
            category_breakdown[category_key] = {
                'label': category_label,
                'amount': float(category_amounts[category_key]),
            }

        total_amount = float(sum(category_amounts.values(), Decimal('0')))

        # 各类别占比
        category_percentage = {}
        for cat_key, cat_data in category_breakdown.items():
            if total_amount > 0:
                category_percentage[cat_key] = round(
                    cat_data['amount'] / total_amount * 100, 2
                )
            else:
                category_percentage[cat_key] = 0.0

        result = {
            'total_expense': total_amount,
            'monthly_trend': monthly_data,
            'category_breakdown': category_breakdown,
            'category_percentage': category_percentage,
        }

        return success_response(result, message='经费趋势查询成功')
