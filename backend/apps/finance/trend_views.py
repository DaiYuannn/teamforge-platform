"""
经费趋势分析视图
- FinanceTrendView: 月度支出趋势、类别分布
"""
from decimal import Decimal

from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response
from .models import FinanceExpense


class FinanceTrendView(APIView):
    """
    经费趋势分析视图
    GET /api/v1/finance/trends/
    返回月度支出趋势和类别分布
    支持按 project 筛选
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = request.query_params
        project_id = params.get('project')

        queryset = FinanceExpense.objects.all()
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # 月度趋势：按 expense_date 的年月分组
        monthly_trend = {}
        for expense in queryset:
            if expense.expense_date:
                month_key = expense.expense_date.strftime('%Y-%m')
                monthly_trend.setdefault(month_key, Decimal('0'))
                monthly_trend[month_key] += expense.amount

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
            cat_sum = queryset.filter(category=category_key).aggregate(
                total=Sum('amount')
            )
            total = cat_sum['total'] or Decimal('0')
            category_breakdown[category_key] = {
                'label': category_label,
                'amount': float(total),
            }

        # 总支出
        total_expense = queryset.aggregate(total=Sum('amount'))
        total_amount = float(total_expense['total'] or 0)

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
