"""
第三方集成视图
- IntegrationConfigViewSet: 集成配置管理（仅管理员 CRUD）
- IntegrationLogViewSet: 集成日志查看（只读）
- BotPushTestView: 群机器人推送测试
"""
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsSysAdmin
from common.schema import success_response_schema
from apps.audit.models import OperationLog
from .models import IntegrationConfig, IntegrationLog, WebhookConfig
from .serializers import (
    IntegrationConfigSerializer,
    IntegrationConfigListSerializer,
    IntegrationLogSerializer,
    WebhookConfigSerializer,
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


class BotPushTestView(APIView):
    """
    群机器人推送测试
    POST /api/v1/integrations/bot-push/test/
    仅限系统管理员
    """
    permission_classes = [IsAuthenticated, IsSysAdmin]

    @extend_schema(
        request=inline_serializer(
            name='BotPushTestRequest',
            fields={
                'title': serializers.CharField(required=False),
                'content': serializers.CharField(required=False),
                'markdown': serializers.CharField(
                    required=False,
                    allow_null=True,
                    allow_blank=True,
                ),
            },
        ),
        responses={
            200: success_response_schema(
                'BotPushTestResponse',
                inline_serializer(
                    name='BotPushTestResult',
                    fields={
                        'total': serializers.IntegerField(),
                        'success': serializers.IntegerField(),
                        'failed': serializers.IntegerField(),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        from .services import BotPushService

        title = request.data.get('title', '群机器人推送测试')
        content = request.data.get('content', '这是一条来自团队管理系统的测试消息')
        markdown = request.data.get('markdown')

        result = BotPushService.push_to_all_active(
            event_type='test',
            title=title,
            content=content,
            markdown=markdown,
        )

        if result['total'] == 0:
            return error_response(
                message='未找到已启用的集成配置，请先在集成配置页面添加并启用企业微信或 Webhook 配置',
                code=1001,
            )

        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.CREATE,
            module='integrations',
            object_type='BotPush',
            description=f'测试群机器人推送: {title}',
        )

        return success_response(result, message=f'推送完成: {result["success"]} 成功, {result["failed"]} 失败')


class WebhookConfigViewSet(MultiPermissionMixin, ModelViewSet):
    """
    Webhook 配置管理 ViewSet（事件订阅式 Webhook）
    - 全部操作仅限系统管理员
    """
    queryset = WebhookConfig.objects.all().order_by('-created_at')
    serializer_class = WebhookConfigSerializer

    permission_classes_by_action = {
        'list': [IsSysAdmin],
        'retrieve': [IsSysAdmin],
        'create': [IsSysAdmin],
        'update': [IsSysAdmin],
        'partial_update': [IsSysAdmin],
        'destroy': [IsSysAdmin],
    }

    filterset_fields = ['is_active']
    search_fields = ['name', 'url']
    ordering_fields = ['created_at', 'updated_at', 'name']

    def create(self, request, *args, **kwargs):
        """创建 Webhook 配置"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = serializer.save()
        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.CREATE,
            module='integrations',
            object_type='WebhookConfig',
            object_id=str(config.id),
            description=f'创建 Webhook 配置: {config.name}',
        )
        return success_response(
            WebhookConfigSerializer(config).data,
            message='Webhook 配置创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新 Webhook 配置"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        config = serializer.save()
        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.UPDATE,
            module='integrations',
            object_type='WebhookConfig',
            object_id=str(config.id),
            description=f'更新 Webhook 配置: {config.name}',
        )
        return success_response(
            WebhookConfigSerializer(config).data,
            message='Webhook 配置更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除 Webhook 配置"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        config_name = instance.name
        config_id = instance.id
        instance.delete()
        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.DELETE,
            module='integrations',
            object_type='WebhookConfig',
            object_id=str(config_id),
            description=f'删除 Webhook 配置: {config_name}',
        )
        return success_response(message='Webhook 配置删除成功')
