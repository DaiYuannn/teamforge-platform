"""
比赛对比视图
- CompetitionComparisonView: 多个比赛横向对比
"""
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.project_access import scope_project_queryset
from common.schema import success_response_schema
from .models import Competition
from .serializers import CompetitionSerializer


class CompetitionComparisonView(APIView):
    """
    比赛对比视图
    GET /api/v1/competitions/comparison/?ids=1,2,3
    对多个比赛进行横向对比
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='ids',
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description='逗号分隔的比赛 ID，至少 2 个、最多 10 个。',
            ),
        ],
        responses={
            200: success_response_schema(
                'CompetitionComparisonResponse',
                inline_serializer(
                    name='CompetitionComparisonData',
                    fields={
                        'total': serializers.IntegerField(),
                        'awarded_count': serializers.IntegerField(),
                        'promoted_count': serializers.IntegerField(),
                        'comparison_fields': serializers.ListField(
                            child=serializers.CharField(),
                        ),
                        'items': inline_serializer(
                            name='CompetitionComparisonItem',
                            fields={
                                'id': serializers.IntegerField(),
                                'project_name': serializers.CharField(),
                                'name': serializers.CharField(),
                                'comp_type': serializers.CharField(),
                                'level': serializers.CharField(),
                                'level_display': serializers.CharField(),
                                'organizer': serializers.CharField(),
                                'register_date': serializers.DateField(allow_null=True),
                                'material_deadline': serializers.DateField(allow_null=True),
                                'review_date': serializers.DateField(allow_null=True),
                                'defense_date': serializers.DateField(allow_null=True),
                                'school_date': serializers.DateField(allow_null=True),
                                'city_date': serializers.DateField(allow_null=True),
                                'province_date': serializers.DateField(allow_null=True),
                                'national_date': serializers.DateField(allow_null=True),
                                'result_date': serializers.DateField(allow_null=True),
                                'status': serializers.CharField(),
                                'status_display': serializers.CharField(),
                                'is_promoted': serializers.BooleanField(),
                                'is_awarded': serializers.BooleanField(),
                                'award_level': serializers.CharField(),
                                'current_stage': serializers.CharField(),
                                'review_summary': serializers.CharField(),
                                'improvement_suggestion': serializers.CharField(),
                            },
                            many=True,
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        ids_param = request.query_params.get('ids', '')
        if not ids_param:
            return error_response(message='请提供 ids 参数（逗号分隔的比赛ID）')

        try:
            ids = [int(i.strip()) for i in ids_param.split(',') if i.strip()]
        except ValueError:
            return error_response(message='ids 参数需为数字，逗号分隔')

        if len(ids) < 2:
            return error_response(message='对比至少需要 2 个比赛')

        if len(ids) > 10:
            return error_response(message='对比最多支持 10 个比赛')

        competitions = scope_project_queryset(
            Competition.objects.filter(id__in=ids).select_related('project'),
            request.user,
            project_lookup='project',
        )
        competitions = sorted(competitions, key=lambda c: ids.index(c.id) if c.id in ids else 0)

        # 构建对比数据
        comparison_fields = [
            'name', 'comp_type', 'level', 'level_display', 'organizer',
            'register_date', 'material_deadline', 'review_date', 'defense_date',
            'school_date', 'city_date', 'province_date', 'national_date', 'result_date',
            'status', 'status_display',
            'is_promoted', 'is_awarded', 'award_level',
            'current_stage', 'review_summary', 'improvement_suggestion',
        ]

        items = []
        for comp in competitions:
            serializer = CompetitionSerializer(comp)
            data = serializer.data
            # 提取对比字段
            item = {
                'id': comp.id,
                'project_name': comp.project.name if comp.project else '',
            }
            for field in comparison_fields:
                item[field] = data.get(field)
            items.append(item)

        # 汇总统计
        total = len(items)
        awarded_count = sum(1 for c in items if c.get('is_awarded'))
        promoted_count = sum(1 for c in items if c.get('is_promoted'))

        result = {
            'total': total,
            'awarded_count': awarded_count,
            'promoted_count': promoted_count,
            'comparison_fields': comparison_fields,
            'items': items,
        }

        return success_response(result, message='比赛对比查询成功')
