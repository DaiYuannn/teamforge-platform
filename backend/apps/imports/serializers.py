"""
数据导入序列化器
"""
from rest_framework import serializers

from .models import ImportTask


class ImportTaskSerializer(serializers.ModelSerializer):
    """导入任务序列化器"""
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = ImportTask
        fields = (
            'id', 'module', 'module_display', 'file_path', 'status', 'status_display',
            'field_mapping', 'preview_data', 'snapshot',
            'total_rows', 'valid_rows', 'error_rows', 'error_details',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'status', 'preview_data', 'snapshot',
            'total_rows', 'valid_rows', 'error_rows', 'error_details',
            'created_by', 'created_at', 'updated_at',
        )


class ImportTaskListSerializer(serializers.ModelSerializer):
    """导入任务列表精简序列化器"""
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = ImportTask
        fields = (
            'id', 'module', 'module_display', 'status', 'status_display',
            'total_rows', 'valid_rows', 'error_rows',
            'created_by_name', 'created_at',
        )
        read_only_fields = fields


class ImportPreviewSerializer(serializers.Serializer):
    """导入预览请求序列化器"""
    file = serializers.FileField(required=True)
    module = serializers.ChoiceField(choices=ImportTask.Module.choices, required=True)
    field_mapping = serializers.JSONField(required=False, default=dict)


class ImportConfirmSerializer(serializers.Serializer):
    """导入确认请求序列化器"""
    field_mapping = serializers.JSONField(required=False, default=dict)
