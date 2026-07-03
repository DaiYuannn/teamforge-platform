"""imports 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import ImportTask


@admin.register(ImportTask)
class ImportTaskAdmin(admin.ModelAdmin):
    """导入任务管理后台"""
    list_display = (
        'id', 'module', 'status', 'total_rows', 'valid_rows',
        'error_rows', 'created_by', 'created_at',
    )
    list_filter = ('module', 'status')
    search_fields = ('module', 'file_path')
    ordering = ('-created_at',)
    raw_id_fields = ('created_by',)
