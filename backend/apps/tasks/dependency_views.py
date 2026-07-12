"""
任务依赖关系视图
- TaskDependencyViewSet: 依赖关系 CRUD（防止循环依赖）
"""
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from .dependency_models import TaskDependency
from .dependency_serializers import TaskDependencySerializer


class TaskDependencyViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    任务依赖关系管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/destroy: 项目负责人/老师/管理员
    创建时自动检测循环依赖与自依赖
    """
    queryset = TaskDependency.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': TaskDependencySerializer,
        'retrieve': TaskDependencySerializer,
        'create': TaskDependencySerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
    }

    filterset_fields = ['task', 'depends_on']
    search_fields = ['task__title', 'depends_on__title']
    ordering_fields = ['created_at']

    def create(self, request, *args, **kwargs):
        """创建依赖关系（含循环依赖检测）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            dependency = serializer.save()
        except ValidationError as e:
            return error_response(
                message='; '.join(e.messages) if hasattr(e, 'messages') else str(e),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            TaskDependencySerializer(dependency).data,
            message='依赖关系创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """删除依赖关系"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='依赖关系已删除')
