"""
比赛视图
- CompetitionViewSet: 比赛 CRUD + 获奖记录管理
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from .models import Competition
from .serializers import CompetitionSerializer, CompetitionListSerializer
from .award_models import CompetitionAward
from .award_serializers import CompetitionAwardSerializer, CompetitionAwardCreateSerializer


class CompetitionViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    比赛管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 项目负责人/老师/管理员
    """
    queryset = Competition.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': CompetitionListSerializer,
        'retrieve': CompetitionSerializer,
        'create': CompetitionSerializer,
        'update': CompetitionSerializer,
        'partial_update': CompetitionSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
        'award_tracking': [IsAuthenticated],
    }

    filterset_fields = ['project', 'level', 'status', 'is_promoted', 'is_awarded']
    search_fields = ['name', 'organizer', 'project__name']
    ordering_fields = ['created_at', 'register_date', 'defense_date', 'result_date']

    def create(self, request, *args, **kwargs):
        """创建比赛"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        competition = serializer.save()
        return success_response(
            CompetitionSerializer(competition).data,
            message='比赛创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新比赛"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        competition = serializer.save()
        return success_response(CompetitionSerializer(competition).data, message='比赛更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除比赛"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='比赛删除成功')

    @action(detail=True, methods=['get', 'post'])
    def award_tracking(self, request, pk=None):
        """
        比赛获奖记录管理
        GET /api/v1/competitions/{id}/award_tracking/
            - 获取该比赛的所有获奖记录
        POST /api/v1/competitions/{id}/award_tracking/
            - 创建获奖记录
            body: {"award_name": "一等奖", "award_level": "校级", "award_date": "2026-07-01", "recipients": [1,2], "notes": ""}
        """
        competition = self.get_object()

        if request.method == 'GET':
            awards = competition.awards.all().order_by('-award_date', '-created_at')
            serializer = CompetitionAwardSerializer(awards, many=True)
            return success_response(serializer.data, message='获奖记录查询成功')

        # POST: 创建获奖记录
        # 权限校验：项目负责人/老师/管理员
        self.check_object_permissions(request, competition)
        if not request.user.global_role in ['teacher', 'sys_admin'] and \
                competition.project.leader_id != request.user.id:
            return error_response(
                message='仅项目负责人/老师/管理员可创建获奖记录', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['competition'] = competition.id
        serializer = CompetitionAwardCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        award = serializer.save(competition=competition)

        return success_response(
            CompetitionAwardSerializer(award).data,
            message='获奖记录创建成功',
            http_status=status.HTTP_201_CREATED,
        )
