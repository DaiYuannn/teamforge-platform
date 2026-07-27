"""
经费预警视图
- FinanceAlertView: 检查各项目经费预算使用情况，发出预警
  - 使用率 > 80%: warning（预警）
  - 使用率 > 100%: danger（超支）
"""
from decimal import Decimal

from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.views import APIView

from common.permissions import IsInternalTeamMember
from common.response import success_response
from common.schema import success_response_schema
from .models import FinanceBudget


class FinanceAlertView(APIView):
    """
    经费预警视图
    GET /api/v1/finance/alerts/
    检查所有经费预算的使用情况
    支持按 project 筛选
    """
    permission_classes = [IsInternalTeamMember]

    # 预警阈值
    WARNING_THRESHOLD = Decimal('0.8')   # 80%
    DANGER_THRESHOLD = Decimal('1.0')    # 100%

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='project',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='按项目 ID 筛选经费总表。',
            ),
        ],
        responses={
            200: success_response_schema(
                'FinanceAlertResponse',
                inline_serializer(
                    name='FinanceAlertData',
                    fields={
                        'summary': inline_serializer(
                            name='FinanceAlertSummary',
                            fields={
                                'total_budgets': serializers.IntegerField(),
                                'normal': serializers.IntegerField(),
                                'warning': serializers.IntegerField(),
                                'danger': serializers.IntegerField(),
                            },
                        ),
                        'warning_count': serializers.IntegerField(),
                        'alerts': inline_serializer(
                            name='FinanceAlertItem',
                            fields={
                                'budget_id': serializers.IntegerField(),
                                'project_id': serializers.IntegerField(),
                                'project_name': serializers.CharField(),
                                'total_income': serializers.FloatField(),
                                'used_amount': serializers.FloatField(),
                                'remaining_amount': serializers.FloatField(),
                                'pending_reimbursement': serializers.FloatField(),
                                'usage_rate': serializers.FloatField(),
                                'alert_level': serializers.ChoiceField(
                                    choices=['normal', 'warning', 'danger'],
                                ),
                                'alert_message': serializers.CharField(),
                                'period': serializers.CharField(),
                            },
                            many=True,
                        ),
                        'warnings': inline_serializer(
                            name='FinanceWarningItem',
                            fields={
                                'budget_id': serializers.IntegerField(),
                                'project_id': serializers.IntegerField(),
                                'project_name': serializers.CharField(),
                                'total_income': serializers.FloatField(),
                                'used_amount': serializers.FloatField(),
                                'remaining_amount': serializers.FloatField(),
                                'pending_reimbursement': serializers.FloatField(),
                                'usage_rate': serializers.FloatField(),
                                'alert_level': serializers.ChoiceField(
                                    choices=['warning', 'danger'],
                                ),
                                'alert_message': serializers.CharField(),
                                'period': serializers.CharField(),
                            },
                            many=True,
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        params = request.query_params
        project_id = params.get('project')

        queryset = FinanceBudget.objects.all().select_related('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        alerts = []
        summary = {
            'total_budgets': 0,
            'normal': 0,
            'warning': 0,
            'danger': 0,
        }

        for budget in queryset:
            total_income = budget.total_income
            used_amount = budget.used_amount

            if total_income > 0:
                usage_rate = used_amount / total_income
            else:
                # 没有收入但有支出，视为严重超支
                usage_rate = Decimal('2.0') if used_amount > 0 else Decimal('0')

            usage_percent = round(float(usage_rate) * 100, 2)

            if usage_rate > self.DANGER_THRESHOLD:
                alert_level = 'danger'
                alert_message = '经费已超支，请立即处理'
            elif usage_rate > self.WARNING_THRESHOLD:
                alert_level = 'warning'
                alert_message = '经费使用率超过 80%，请注意控制'
            else:
                alert_level = 'normal'
                alert_message = '经费使用正常'

            summary['total_budgets'] += 1
            summary[alert_level] += 1

            # 仅返回需要关注的（warning 和 danger），但也包含 normal 以便完整展示
            alerts.append({
                'budget_id': budget.id,
                'project_id': budget.project_id,
                'project_name': budget.project.name if budget.project else '',
                'total_income': float(total_income),
                'used_amount': float(used_amount),
                'remaining_amount': float(budget.remaining_amount),
                'pending_reimbursement': float(budget.pending_reimbursement),
                'usage_rate': usage_percent,
                'alert_level': alert_level,
                'alert_message': alert_message,
                'period': budget.period,
            })

        # 仅预警项
        warning_items = [a for a in alerts if a['alert_level'] != 'normal']

        result = {
            'summary': summary,
            'warning_count': len(warning_items),
            'alerts': alerts,
            'warnings': warning_items,
        }

        return success_response(result, message='经费预警查询成功')
