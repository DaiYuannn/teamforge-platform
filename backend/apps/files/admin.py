"""files 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import FileAsset, FileVersion


@admin.register(FileAsset)
class FileAssetAdmin(admin.ModelAdmin):
    """文件资源管理后台"""
    list_display = (
        'id', 'name', 'project', 'level', 'size',
        'content_type', 'uploader', 'version', 'created_at',
    )
    list_filter = ('level',)
    search_fields = ('name', 'project__name')
    raw_id_fields = ('project', 'uploader')


@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):
    """文件版本管理后台"""
    list_display = ('id', 'file_asset', 'version', 'uploader', 'created_at')
    search_fields = ('file_asset__name',)
    raw_id_fields = ('file_asset', 'uploader')
