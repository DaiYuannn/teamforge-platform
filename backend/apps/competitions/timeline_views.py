"""
比赛时间线视图
- CompetitionTimelineView: 返回单个比赛的时间线事件
  - 报名、材料截止、网评、答辩、各阶段比赛、结果公布
"""
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.project_access import scope_project_queryset, user_can_access_project
from common.schema import success_response_schema
from .models import Competition


class CompetitionTimelineView(APIView):
    """
    比赛时间线视图
    GET /api/v1/competitions/timeline/?competition=1
    返回指定比赛的关键节点时间线（按日期排序）
    """
    permission_classes = [IsAuthenticated]

    # 时间线节点定义: (字段名, 事件类型, 事件标签)
    TIMELINE_NODES = [
        ('register_date', 'registration', '报名'),
        ('material_deadline', 'material_deadline', '材料截止'),
        ('review_date', 'review', '网评'),
        ('defense_date', 'defense', '答辩'),
        ('school_date', 'school_comp', '校赛'),
        ('city_date', 'city_comp', '市赛'),
        ('province_date', 'province_comp', '省赛'),
        ('national_date', 'national_comp', '国赛'),
        ('result_date', 'results', '结果公布'),
    ]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='competition',
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description='比赛 ID。',
            ),
        ],
        responses={
            200: success_response_schema(
                'CompetitionTimelineResponse',
                inline_serializer(
                    name='CompetitionTimelineData',
                    fields={
                        'competition_id': serializers.IntegerField(),
                        'competition_name': serializers.CharField(),
                        'project_name': serializers.CharField(),
                        'level': serializers.CharField(),
                        'level_display': serializers.CharField(),
                        'status': serializers.CharField(),
                        'status_display': serializers.CharField(),
                        'is_promoted': serializers.BooleanField(),
                        'is_awarded': serializers.BooleanField(),
                        'award_level': serializers.CharField(),
                        'current_stage': serializers.CharField(),
                        'events': inline_serializer(
                            name='CompetitionTimelineEvent',
                            fields={
                                'event_type': serializers.CharField(),
                                'label': serializers.CharField(),
                                'date': serializers.DateField(),
                                'field': serializers.CharField(),
                            },
                            many=True,
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        competition_id = request.query_params.get('competition')
        if not competition_id:
            return error_response(message='请提供 competition 参数')

        queryset = scope_project_queryset(
            Competition.objects.select_related('project'),
            request.user,
            project_lookup='project',
        )
        try:
            competition = queryset.get(id=competition_id)
        except Competition.DoesNotExist:
            return error_response(message='比赛不存在', code=1004)
        if not user_can_access_project(request.user, competition.project):
            return error_response(message='比赛不存在', code=1004)

        events = []
        for field_name, event_type, label in self.TIMELINE_NODES:
            date_value = getattr(competition, field_name, None)
            if date_value:
                events.append({
                    'event_type': event_type,
                    'label': label,
                    'date': date_value.isoformat() if hasattr(date_value, 'isoformat') else str(date_value),
                    'field': field_name,
                })

        # 按日期排序
        events.sort(key=lambda e: e['date'])

        result = {
            'competition_id': competition.id,
            'competition_name': competition.name,
            'project_name': competition.project.name if competition.project else '',
            'level': competition.level,
            'level_display': competition.get_level_display(),
            'status': competition.status,
            'status_display': competition.get_status_display(),
            'is_promoted': competition.is_promoted,
            'is_awarded': competition.is_awarded,
            'award_level': competition.award_level,
            'current_stage': competition.current_stage,
            'events': events,
        }

        return success_response(result, message='比赛时间线查询成功')
