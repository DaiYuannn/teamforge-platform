"""audit 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import OperationLog


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    """操作日志 Admin 配置"""
    list_display = (
        'id', 'operator', 'operation_type', 'module',
        'object_type', 'object_id', 'request_method',
        'response_status', 'is_success', 'created_at',
    )
    list_filter = (
        'operation_type', 'module', 'request_method',
        'is_success', 'created_at',
    )
    search_fields = ('operator__name', 'operator__email', 'description', 'request_path')
    readonly_fields = (
        'operator', 'operation_type', 'module', 'object_type', 'object_id',
        'description', 'request_method', 'request_path', 'request_ip',
        'user_agent', 'request_data', 'response_status', 'is_success',
        'error_message', 'created_at',
    )
    list_per_page = 30
    date_hierarchy = 'created_at'
