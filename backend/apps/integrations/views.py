"""
第三方集成视图
- IntegrationConfigViewSet: 集成配置管理（仅管理员 CRUD）
- IntegrationLogViewSet: 集成日志查看（只读）
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from common.response import success_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsSysAdmin
from apps.audit.models import OperationLog
from .models import IntegrationConfig, IntegrationLog
from .serializers import (
    IntegrationConfigSerializer,
    IntegrationConfigListSerializer,
    IntegrationLogSerializer,
)


class IntegrationConfigViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    集成配置管理 ViewSet
    - 全部操作仅限系统管理员
    """
    queryset = IntegrationConfig.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': IntegrationConfigListSerializer,
        'retrieve': IntegrationConfigSerializer,
        'create': IntegrationConfigSerializer,
        'update': IntegrationConfigSerializer,
        'partial_update': IntegrationConfigSerializer,
    }

    # 全部操作仅限系统管理员
    permission_classes_by_action = {
        'list': [IsSysAdmin],
        'retrieve': [IsSysAdmin],
        'create': [IsSysAdmin],
        'update': [IsSysAdmin],
        'partial_update': [IsSysAdmin],
        'destroy': [IsSysAdmin],
    }

    filterset_fields = ['provider', 'enabled']
    search_fields = ['name', 'app_id']
    ordering_fields = ['created_at', 'updated_at']

    def create(self, request, *args, **kwargs):
        """创建集成配置"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 自动设置创建人
        config = serializer.save(created_by=request.user)
        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.CREATE,
            module='integrations',
            object_type='IntegrationConfig',
            object_id=str(config.id),
            description=f'创建集成配置: {config.name}',
        )
        return success_response(
            IntegrationConfigSerializer(config).data,
            message='集成配置创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新集成配置"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        config = serializer.save()
        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.UPDATE,
            module='integrations',
            object_type='IntegrationConfig',
            object_id=str(config.id),
            description=f'更新集成配置: {config.name}',
        )
        return success_response(
            IntegrationConfigSerializer(config).data,
            message='集成配置更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除集成配置"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        config_name = instance.name
        config_id = instance.id
        instance.delete()
        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.DELETE,
            module='integrations',
            object_type='IntegrationConfig',
            object_id=str(config_id),
            description=f'删除集成配置: {config_name}',
        )
        return success_response(message='集成配置删除成功')


class IntegrationLogViewSet(MultiPermissionMixin, ReadOnlyModelViewSet):
    """
    集成日志查看 ViewSet（只读）
    - 全部操作仅限系统管理员
    """
    queryset = IntegrationLog.objects.all().order_by('-created_at')
    serializer_class = IntegrationLogSerializer

    permission_classes_by_action = {
        'list': [IsSysAdmin],
        'retrieve': [IsSysAdmin],
    }

    filterset_fields = ['provider', 'status', 'event_type']
    search_fields = ['event_type', 'target']
    ordering_fields = ['created_at']
