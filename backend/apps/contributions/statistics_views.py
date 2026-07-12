"""
贡献度统计视图
- ContributionStatisticsView: 按成员和按项目的贡献度统计
"""
from decimal import Decimal

from django.db.models import Sum, Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response
from .models import Contribution


class ContributionStatisticsView(APIView):
    """
    贡献度统计视图
    GET /api/v1/contributions/statistics/
    返回：
    - 按成员统计贡献得分
    - 按项目统计贡献得分
    支持按 project、period 筛选
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = request.query_params
        project_id = params.get('project')
        period = params.get('period')

        queryset = Contribution.objects.all()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if period:
            queryset = queryset.filter(period=period)

        # 总览
        total = queryset.count()
        approved_qs = queryset.filter(status=Contribution.Status.APPROVED)
        approved_count = approved_qs.count()
        total_score = approved_qs.aggregate(total=Sum('weight'))
        total_score_value = float(total_score['total'] or 0)

        # 按类型统计
        by_type = {}
        for type_key, type_label in Contribution.ContributionType.choices:
            type_qs = queryset.filter(contribution_type=type_key)
            type_count = type_qs.count()
            type_score = type_qs.aggregate(total=Sum('weight'))
            by_type[type_key] = {
                'label': type_label,
                'count': type_count,
                'score': float(type_score['total'] or 0),
            }

        # 按状态统计
        by_status = {}
        for status_key, status_label in Contribution.Status.choices:
            by_status[status_key] = {
                'label': status_label,
                'count': queryset.filter(status=status_key).count(),
            }

        # 按成员统计（仅已通过的）
        member_stats = []
        member_agg = approved_qs.values('user_id', 'user__name').annotate(
            total_score=Sum('weight'),
            contribution_count=Count('id'),
        ).order_by('-total_score')
        for item in member_agg:
            member_stats.append({
                'user_id': item['user_id'],
                'user_name': item['user__name'],
                'contribution_score': float(item['total_score'] or 0),
                'contribution_count': item['contribution_count'],
            })

        # 按项目统计（仅已通过的）
        project_stats = []
        project_agg = approved_qs.values('project_id', 'project__name').annotate(
            total_score=Sum('weight'),
            contribution_count=Count('id'),
        ).order_by('-total_score')
        for item in project_agg:
            project_stats.append({
                'project_id': item['project_id'],
                'project_name': item['project__name'] or '未关联项目',
                'contribution_score': float(item['total_score'] or 0),
                'contribution_count': item['contribution_count'],
            })

        result = {
            'total': total,
            'approved_count': approved_count,
            'total_score': total_score_value,
            'by_type': by_type,
            'by_status': by_status,
            'by_member': member_stats,
            'by_project': project_stats,
        }

        return success_response(result, message='贡献度统计查询成功')
