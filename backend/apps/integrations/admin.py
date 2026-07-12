"""integrations 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import IntegrationConfig, IntegrationLog, WebhookConfig


@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    """集成配置管理后台"""
    list_display = (
        'id', 'name', 'provider', 'webhook_url',
        'app_id', 'enabled', 'created_by', 'created_at', 'updated_at',
    )
    list_filter = ('provider', 'enabled')
    search_fields = ('name', 'app_id', 'webhook_url')
    ordering = ('-created_at',)
    raw_id_fields = ('created_by',)


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    """集成日志管理后台"""
    list_display = (
        'id', 'provider', 'event_type', 'target',
        'status', 'error_message', 'created_at',
    )
    list_filter = ('provider', 'status')
    search_fields = ('event_type', 'target', 'error_message')
    ordering = ('-created_at',)
    readonly_fields = (
        'provider', 'event_type', 'target', 'payload',
        'status', 'response', 'error_message', 'created_at',
    )


@admin.register(WebhookConfig)
class WebhookConfigAdmin(admin.ModelAdmin):
    """Webhook 配置管理后台"""
    list_display = (
        'id', 'name', 'url', 'is_active', 'events', 'created_at', 'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'url')
    ordering = ('-created_at',)
