"""
数据导入序列化器
"""
import os

from rest_framework import serializers

from .models import ImportTask


def _display_file_name(file_path):
    name = os.path.basename(file_path)
    prefix, separator, original = name.partition('_')
    if separator and len(prefix) == 32 and all(char in '0123456789abcdef' for char in prefix.lower()):
        return original
    return name


class ImportTaskSerializer(serializers.ModelSerializer):
    """导入任务序列化器"""
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
    file_name = serializers.SerializerMethodField()
    can_rollback = serializers.SerializerMethodField()

    class Meta:
        model = ImportTask
        fields = (
            'id', 'module', 'module_display', 'file_path', 'file_name',
            'team', 'team_name',
            'status', 'status_display', 'can_rollback',
            'field_mapping', 'preview_data', 'snapshot',
            'total_rows', 'valid_rows', 'error_rows', 'error_details',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'module', 'file_path', 'team', 'field_mapping',
            'status', 'preview_data', 'snapshot',
            'total_rows', 'valid_rows', 'error_rows', 'error_details',
            'created_by', 'created_at', 'updated_at',
        )

    def get_file_name(self, obj) -> str:
        return _display_file_name(obj.file_path)

    def get_can_rollback(self, obj) -> bool:
        return obj.status == ImportTask.Status.CONFIRMED and bool(obj.snapshot)


class ImportTaskListSerializer(serializers.ModelSerializer):
    """导入任务列表精简序列化器"""
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
    file_name = serializers.SerializerMethodField()
    can_rollback = serializers.SerializerMethodField()

    class Meta:
        model = ImportTask
        fields = (
            'id', 'module', 'module_display', 'file_name', 'team', 'team_name',
            'status', 'status_display',
            'total_rows', 'valid_rows', 'error_rows',
            'error_details', 'created_by_name', 'can_rollback', 'created_at', 'updated_at',
        )
        read_only_fields = fields

    def get_file_name(self, obj) -> str:
        return _display_file_name(obj.file_path)

    def get_can_rollback(self, obj) -> bool:
        return obj.status == ImportTask.Status.CONFIRMED and bool(obj.snapshot)


class ImportPreviewSerializer(serializers.Serializer):
    """导入预览请求序列化器"""
    file = serializers.FileField(required=True)
    module = serializers.ChoiceField(choices=ImportTask.Module.choices, required=True)
    team = serializers.IntegerField(required=False, allow_null=True)
    field_mapping = serializers.JSONField(required=False, default=dict)


class ImportConfirmSerializer(serializers.Serializer):
    """导入确认请求序列化器"""
    field_mapping = serializers.JSONField(required=False, default=dict)


class MaterialArchivePreviewSerializer(serializers.Serializer):
    """ZIP material package containing a root manifest.json."""

    file = serializers.FileField(required=True)
    team = serializers.IntegerField(required=True)

    def validate_file(self, value):
        if os.path.splitext(value.name)[1].lower() != '.zip':
            raise serializers.ValidationError('资料包必须是 .zip 文件')
        if value.size <= 0:
            raise serializers.ValidationError('资料包不能为空')
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError('资料包压缩文件不能超过 50 MB')
        return value
