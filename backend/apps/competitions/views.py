"""
比赛视图
- CompetitionViewSet: 比赛 CRUD
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from .models import Competition
from .serializers import CompetitionSerializer, CompetitionListSerializer


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
