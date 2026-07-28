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
from common.project_access import scope_project_queryset
from .models import Competition, CompetitionParticipant
from .permissions import can_manage_competition
from .serializers import (
    CompetitionSerializer,
    CompetitionListSerializer,
    CompetitionParticipantSerializer,
)
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
        'update': [IsAuthenticated],
        'partial_update': [IsAuthenticated],
        'destroy': [IsAuthenticated],
        'award_tracking': [IsAuthenticated],
        'participants': [IsAuthenticated],
    }

    filterset_fields = ['project', 'level', 'status', 'is_promoted', 'is_awarded']
    search_fields = ['name', 'organizer', 'project__name']
    ordering_fields = ['created_at', 'register_date', 'defense_date', 'result_date']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'project', 'project__leader',
        ).prefetch_related(
            'participants__user',
            'project__members__user',
            'project__teams',
        )
        return scope_project_queryset(
            queryset,
            self.request.user,
            project_lookup='project',
        )

    def create(self, request, *args, **kwargs):
        """创建比赛"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        competition = serializer.save()
        return success_response(
            CompetitionSerializer(
                competition,
                context=self.get_serializer_context(),
            ).data,
            message='比赛创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新比赛"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if not can_manage_competition(request.user, instance):
            return error_response(
                message='仅比赛负责人或项目负责人可修改比赛',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        competition = serializer.save()
        return success_response(
            CompetitionSerializer(
                competition,
                context=self.get_serializer_context(),
            ).data,
            message='比赛更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除比赛"""
        instance = self.get_object()
        if not can_manage_competition(request.user, instance):
            return error_response(
                message='仅比赛负责人或项目负责人可删除比赛',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return success_response(message='比赛删除成功')

    @action(detail=True, methods=['get', 'post', 'patch', 'delete'])
    def participants(self, request, pk=None):
        """维护比赛拟参赛及已确认成员名单。"""
        competition = self.get_object()
        if request.method == 'GET':
            records = competition.participants.select_related('user').all()
            return success_response(
                CompetitionParticipantSerializer(
                    records,
                    many=True,
                    context=self.get_serializer_context(),
                ).data
            )

        if not can_manage_competition(request.user, competition):
            return error_response(
                message='仅比赛负责人或项目负责人可维护参赛名单',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == 'POST':
            data = request.data.copy()
            data['competition'] = competition.id
            serializer = CompetitionParticipantSerializer(
                data=data,
                context=self.get_serializer_context(),
            )
            serializer.is_valid(raise_exception=True)
            participant = serializer.save()
            return success_response(
                CompetitionParticipantSerializer(
                    participant,
                    context=self.get_serializer_context(),
                ).data,
                message='参赛成员已添加',
                http_status=status.HTTP_201_CREATED,
            )

        participant_id = request.data.get('participant_id') or request.query_params.get(
            'participant_id'
        )
        participant = competition.participants.filter(pk=participant_id).first()
        if participant is None:
            return error_response(
                message='参赛成员记录不存在',
                code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        if request.method == 'PATCH':
            data = request.data.copy()
            data.pop('participant_id', None)
            serializer = CompetitionParticipantSerializer(
                participant,
                data=data,
                partial=True,
                context=self.get_serializer_context(),
            )
            serializer.is_valid(raise_exception=True)
            participant = serializer.save()
            return success_response(
                CompetitionParticipantSerializer(
                    participant,
                    context=self.get_serializer_context(),
                ).data,
                message='参赛成员已更新',
            )

        participant.delete()
        return success_response(message='参赛成员已移除')

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
        if not can_manage_competition(request.user, competition):
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
