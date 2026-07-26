"""
比赛统计视图
- CompetitionStatisticsView: 返回比赛总体统计
  - 比赛总数
  - 按级别分布
  - 按状态分布
  - 获奖率
  - 晋级率
"""
from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response
from common.project_access import scope_project_queryset
from .models import Competition


class CompetitionStatisticsView(APIView):
    """
    比赛统计视图
    GET /api/v1/competitions/statistics/
    支持按 project 筛选
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = request.query_params
        project_id = params.get('project')

        queryset = scope_project_queryset(
            Competition.objects.all(),
            request.user,
            project_lookup='project',
        )
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        total = queryset.count()

        # 按级别统计
        by_level = {}
        for level_key, level_label in Competition.Level.choices:
            by_level[level_key] = queryset.filter(level=level_key).count()

        # 按状态统计
        by_status = {}
        for status_key, status_label in Competition.Status.choices:
            by_status[status_key] = queryset.filter(status=status_key).count()

        # 获奖率
        awarded_count = queryset.filter(is_awarded=True).count()
        award_rate = round(awarded_count / total * 100, 2) if total > 0 else 0.0

        # 晋级率
        promoted_count = queryset.filter(is_promoted=True).count()
        promotion_rate = round(promoted_count / total * 100, 2) if total > 0 else 0.0

        # 按级别统计获奖率
        award_by_level = {}
        for level_key, level_label in Competition.Level.choices:
            level_total = queryset.filter(level=level_key).count()
            level_awarded = queryset.filter(level=level_key, is_awarded=True).count()
            award_by_level[level_key] = {
                'total': level_total,
                'awarded': level_awarded,
                'rate': round(level_awarded / level_total * 100, 2) if level_total > 0 else 0.0,
            }

        result = {
            'total': total,
            'awarded_count': awarded_count,
            'promoted_count': promoted_count,
            'by_level': by_level,
            'by_status': by_status,
            'award_rate': award_rate,
            'promotion_rate': promotion_rate,
            'award_by_level': award_by_level,
        }

        return success_response(result, message='比赛统计查询成功')
