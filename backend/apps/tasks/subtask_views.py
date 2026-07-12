"""
子任务视图
- SubTaskViewSet: 子任务 CRUD + 完成/取消完成
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from .subtask_models import SubTask
from .subtask_serializers import SubTaskSerializer


class SubTaskViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    子任务管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 项目负责人/老师/管理员
    - toggle: 切换完成状态
    """
    queryset = SubTask.objects.all().order_by('sort_order', 'id')

    serializer_classes_by_action = {
        'list': SubTaskSerializer,
        'retrieve': SubTaskSerializer,
        'create': SubTaskSerializer,
        'update': SubTaskSerializer,
        'partial_update': SubTaskSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
        'toggle': [IsAuthenticated],
    }

    filterset_fields = ['parent', 'assignee', 'is_completed']
    search_fields = ['title']
    ordering_fields = ['sort_order', 'created_at']

    def create(self, request, *args, **kwargs):
        """创建子任务"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subtask = serializer.save()
        return success_response(
            SubTaskSerializer(subtask).data,
            message='子任务创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新子任务"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        subtask = serializer.save()
        return success_response(SubTaskSerializer(subtask).data, message='子任务更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除子任务"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='子任务已删除')

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """
        切换子任务完成状态
        POST /api/v1/tasks/subtasks/{id}/toggle/
        """
        subtask = self.get_object()
        if subtask.is_completed:
            subtask.mark_incomplete()
            message = '子任务已标记为未完成'
        else:
            subtask.mark_completed()
            message = '子任务已完成'
        return success_response(SubTaskSerializer(subtask).data, message=message)
