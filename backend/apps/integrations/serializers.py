"""
第三方集成序列化器
"""
from rest_framework import serializers

from .models import IntegrationConfig, IntegrationLog


class IntegrationConfigSerializer(serializers.ModelSerializer):
    """集成配置完整序列化器"""
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = IntegrationConfig
        fields = (
            'id', 'name', 'provider', 'provider_display',
            'webhook_url', 'app_id', 'encrypted_secret', 'enabled',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')


class IntegrationConfigListSerializer(serializers.ModelSerializer):
    """集成配置列表精简序列化器"""
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)

    class Meta:
        model = IntegrationConfig
        fields = (
            'id', 'name', 'provider', 'provider_display',
            'webhook_url', 'enabled', 'created_at', 'updated_at',
        )
        read_only_fields = fields


class IntegrationLogSerializer(serializers.ModelSerializer):
    """集成日志序列化器（只读）"""
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = IntegrationLog
        fields = (
            'id', 'provider', 'provider_display', 'event_type', 'target',
            'payload', 'status', 'status_display', 'response', 'error_message',
            'created_at',
        )
        read_only_fields = fields
