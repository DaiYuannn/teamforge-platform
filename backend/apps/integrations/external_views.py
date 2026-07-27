"""
外部平台集成序列化器与视图
- ExternalPlatformViewSet: 外部平台 CRUD
"""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from common.response import error_response, success_response
from common.mixins import MultiSerializerMixin
from common.permissions import IsSysAdminOrReadOnly
from .external_models import ExternalPlatform
from .connection_services import IntegrationConnectionError, connect_external_platform


class ExternalPlatformSerializer(serializers.ModelSerializer):
    """外部平台序列化器"""

    class Meta:
        model = ExternalPlatform
        fields = (
            'id', 'name', 'platform_type', 'api_url',
            'api_key', 'is_active', 'config', 'connection_status',
            'last_checked_at', 'last_synced_at', 'last_error',
            'remote_metadata', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'connection_status', 'last_checked_at', 'last_synced_at',
            'last_error', 'remote_metadata', 'created_at', 'updated_at',
        )
        extra_kwargs = {'api_key': {'write_only': True, 'required': False, 'allow_blank': True}}


class ExternalPlatformViewSet(MultiSerializerMixin, ModelViewSet):
    """外部平台集成 CRUD"""
    queryset = ExternalPlatform.objects.all().order_by('-created_at')
    serializer_class = ExternalPlatformSerializer
    serializer_classes_by_action = {
        'list': ExternalPlatformSerializer,
        'retrieve': ExternalPlatformSerializer,
        'create': ExternalPlatformSerializer,
        'update': ExternalPlatformSerializer,
        'partial_update': ExternalPlatformSerializer,
    }
    permission_classes = [IsAuthenticated, IsSysAdminOrReadOnly]
    filterset_fields = ['platform_type', 'is_active']
    search_fields = ['name', 'platform_type']
    ordering_fields = ['created_at', 'updated_at']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        platform = serializer.save()
        return success_response(
            ExternalPlatformSerializer(platform).data,
            message='外部平台创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def _connect(self, platform, *, sync):
        if not platform.is_active:
            return error_response(
                message='Connection is disabled', code=1001,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if not platform.api_url:
            return error_response(
                message='API URL is required', code=1001,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            metadata = connect_external_platform(platform, sync=sync)
        except IntegrationConnectionError as exc:
            platform.record_connection(connected=False, error=str(exc))
            return error_response(
                message=str(exc), code=2501,
                http_status=status.HTTP_502_BAD_GATEWAY,
            )
        platform.record_connection(
            connected=True, metadata=metadata, synced=sync,
        )
        return success_response(
            ExternalPlatformSerializer(platform).data,
            message='Platform sync completed' if sync else 'Connection succeeded',
        )

    @action(detail=True, methods=['post'], url_path='test-connection')
    def test_connection(self, request, pk=None):
        return self._connect(self.get_object(), sync=False)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        return self._connect(self.get_object(), sync=True)
