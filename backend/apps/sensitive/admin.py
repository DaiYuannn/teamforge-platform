"""sensitive 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import SensitiveData, SensitiveAccessRequest


@admin.register(SensitiveData)
class SensitiveDataAdmin(admin.ModelAdmin):
    """敏感数据管理后台"""
    list_display = (
        'id', 'title', 'display_name', 'data_type', 'project',
        'uploader', 'is_encrypted', 'key_version', 'created_at',
    )
    list_filter = ('data_type', 'is_encrypted')
    search_fields = ('title', 'display_name')
    ordering = ('-created_at',)
    raw_id_fields = ('project', 'uploader', 'file_attachment')


@admin.register(SensitiveAccessRequest)
class SensitiveAccessRequestAdmin(admin.ModelAdmin):
    """敏感数据访问申请管理后台"""
    list_display = (
        'id', 'sensitive_data', 'applicant', 'status', 'approver',
        'approved_at', 'access_expires_at', 'viewed_at', 'is_download', 'created_at',
    )
    list_filter = ('status', 'is_download')
    search_fields = ('sensitive_data__title', 'applicant__name', 'reason')
    ordering = ('-created_at',)
    raw_id_fields = ('sensitive_data', 'applicant', 'approver', 'project')
