"""
外部平台集成序列化器与视图
- ExternalPlatformViewSet: 外部平台 CRUD
"""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response
from common.mixins import MultiSerializerMixin
from common.permissions import IsSysAdminOrReadOnly
from .external_models import ExternalPlatform


class ExternalPlatformSerializer(serializers.ModelSerializer):
    """外部平台序列化器"""

    class Meta:
        model = ExternalPlatform
        fields = (
            'id', 'name', 'platform_type', 'api_url',
            'api_key', 'is_active', 'config', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
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
