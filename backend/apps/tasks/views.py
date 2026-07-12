"""
任务视图
- TaskViewSet: 任务 CRUD + 状态变更
关键：任务完成情况对所有认证用户可见
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from .models import Task
from .serializers import TaskSerializer, TaskListSerializer, TaskCreateSerializer
from .services import task_service


class TaskViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    任务管理 ViewSet
    - list/retrieve: 所有认证用户可查看（任务完成情况对所有认证用户开放）
    - create/update/destroy: 项目负责人/老师/管理员
    - change_status: POST 修改任务状态
    """
    queryset = Task.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': TaskListSerializer,
        'retrieve': TaskSerializer,
        'create': TaskCreateSerializer,
        'update': TaskSerializer,
        'partial_update': TaskSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
        'change_status': [IsAuthenticated],
    }

    filterset_fields = ['project', 'assignee', 'creator', 'status', 'priority', 'reviewer']
    search_fields = ['title', 'description', 'project__name']
    ordering_fields = [
        'created_at', 'updated_at', 'title', 'status', 'priority',
        'deadline', 'start_date',
    ]

    def create(self, request, *args, **kwargs):
        """创建任务"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return success_response(
            TaskSerializer(task).data,
            message='任务创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新任务"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return success_response(TaskSerializer(task).data, message='任务更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除任务（软删除，移入回收站）"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        self.perform_destroy(instance)
        return success_response(message='任务已移入回收站')

    def perform_destroy(self, instance):
        """软删除而非物理删除，可通过回收站恢复"""
        instance.soft_delete(getattr(self.request, 'user', None))

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """
        修改任务状态
        POST /api/v1/tasks/{id}/change_status/
        body: {"to_status": "done", "delay_reason": "xxx"}
        """
        task = self.get_object()

        # 权限校验：只有任务指派人、协作者、创建者、审核人或管理员/老师可以修改状态
        user = request.user
        can_change = (
            task.assignee_id == user.id or
            task.creator_id == user.id or
            task.reviewer_id == user.id or
            task.collaborators.filter(id=user.id).exists() or
            user.global_role in ['sys_admin', 'teacher']
        )
        if not can_change:
            return error_response(message='无权修改此任务状态', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)

        to_status = request.data.get('to_status')
        delay_reason = request.data.get('delay_reason', '')

        if not to_status:
            return error_response(message='请提供 to_status 参数')

        # 校验状态值有效性
        valid_statuses = [choice[0] for choice in Task.Status.choices]
        if to_status not in valid_statuses:
            return error_response(message=f'无效的任务状态，可选值: {valid_statuses}')

        success, result = task_service.change_status(
            task=task,
            to_status=to_status,
            operator=user,
            delay_reason=delay_reason,
        )

        if not success:
            return error_response(message=result)

        return success_response(
            TaskSerializer(result).data,
            message='任务状态更新成功',
        )
