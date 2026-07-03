"""notifications 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """通知 Admin 配置"""
    list_display = (
        'id', 'title', 'recipient', 'sender',
        'notification_type', 'channel', 'priority',
        'is_read', 'created_at',
    )
    list_filter = (
        'notification_type', 'channel', 'priority',
        'is_read', 'created_at',
    )
    search_fields = ('title', 'content', 'recipient__name', 'recipient__email')
    readonly_fields = (
        'recipient', 'sender', 'title', 'content',
        'notification_type', 'channel', 'priority',
        'is_read', 'read_at', 'related_object_type',
        'related_object_id', 'created_at',
    )
    list_per_page = 30
    date_hierarchy = 'created_at'
