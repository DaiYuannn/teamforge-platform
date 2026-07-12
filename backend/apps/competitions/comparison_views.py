"""
比赛对比视图
- CompetitionComparisonView: 多个比赛横向对比
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from .models import Competition
from .serializers import CompetitionSerializer


class CompetitionComparisonView(APIView):
    """
    比赛对比视图
    GET /api/v1/competitions/comparison/?ids=1,2,3
    对多个比赛进行横向对比
    """
    permission_classes = [IsAuthenticated]

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

        competitions = Competition.objects.filter(id__in=ids).select_related('project')
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
