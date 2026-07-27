"""
贡献度排行榜视图
- ContributionLeaderboardView: 按贡献得分排名的成员列表
"""
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response
from common.project_access import scope_project_queryset
from common.schema import success_response_schema
from .models import Contribution


class ContributionLeaderboardView(APIView):
    """
    贡献度排行榜视图
    GET /api/v1/contributions/leaderboard/
    返回按贡献得分排名的成员列表
    支持按 project、period 筛选
    支持按 limit 限制返回数量（默认全部）
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter('project', int, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('period', str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                'limit',
                int,
                OpenApiParameter.QUERY,
                required=False,
                description='仅返回排名靠前的指定人数；非正整数会被忽略。',
            ),
        ],
        responses={
            200: success_response_schema(
                'ContributionLeaderboardResponse',
                inline_serializer(
                    name='ContributionLeaderboardData',
                    fields={
                        'total_members': serializers.IntegerField(),
                        'leaderboard': inline_serializer(
                            name='ContributionLeaderboardItem',
                            fields={
                                'rank': serializers.IntegerField(),
                                'user_id': serializers.IntegerField(),
                                'user_name': serializers.CharField(),
                                'email': serializers.EmailField(),
                                'global_role': serializers.CharField(),
                                'contribution_score': serializers.FloatField(),
                                'contribution_count': serializers.IntegerField(),
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
        period = params.get('period')
        limit_param = params.get('limit')

        queryset = scope_project_queryset(
            Contribution.objects.filter(status=Contribution.Status.APPROVED),
            request.user,
            project_lookup='project',
        )
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if period:
            queryset = queryset.filter(period=period)

        # 按用户聚合贡献得分，降序排列
        leaderboard_qs = queryset.values(
            'user_id', 'user__name', 'user__email', 'user__global_role',
        ).annotate(
            total_score=Coalesce(
                Sum('weight'),
                Decimal('0'),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
            contribution_count=Count('id'),
        ).order_by('-total_score')

        leaderboard = []
        for index, item in enumerate(leaderboard_qs, start=1):
            leaderboard.append({
                'rank': index,
                'user_id': item['user_id'],
                'user_name': item['user__name'],
                'email': item['user__email'],
                'global_role': item['user__global_role'],
                'contribution_score': float(item['total_score'] or 0),
                'contribution_count': item['contribution_count'],
            })

        # 限制返回数量
        if limit_param:
            try:
                limit = int(limit_param)
                if limit > 0:
                    leaderboard = leaderboard[:limit]
            except ValueError:
                pass

        result = {
            'total_members': len(leaderboard),
            'leaderboard': leaderboard,
        }

        return success_response(result, message='贡献度排行榜查询成功')
