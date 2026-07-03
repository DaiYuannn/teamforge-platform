"""
文件序列化器
"""
from rest_framework import serializers

from .models import FileAsset, FileVersion


class FileVersionSerializer(serializers.ModelSerializer):
    """文件版本序列化器"""
    uploader_name = serializers.CharField(source='uploader.name', read_only=True, default='')

    class Meta:
        model = FileVersion
        fields = ('id', 'file_asset', 'file', 'version', 'uploader', 'uploader_name', 'created_at')
        read_only_fields = ('id', 'uploader', 'created_at')


class FileAssetSerializer(serializers.ModelSerializer):
    """文件资源序列化器"""
    uploader_name = serializers.CharField(source='uploader.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FileAsset
        fields = (
            'id', 'project', 'project_name', 'name', 'file', 'file_url',
            'level', 'level_display', 'size', 'content_type',
            'uploader', 'uploader_name', 'version',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'size', 'content_type', 'uploader', 'version', 'created_at', 'updated_at')

    def get_file_url(self, obj):
        """获取文件访问URL"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class FileAssetListSerializer(serializers.ModelSerializer):
    """文件资源列表精简序列化器"""
    uploader_name = serializers.CharField(source='uploader.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    level_display = serializers.CharField(source='get_level_display', read_only=True)

    class Meta:
        model = FileAsset
        fields = (
            'id', 'project', 'project_name', 'name',
            'level', 'level_display', 'size', 'content_type',
            'uploader_name', 'version', 'created_at',
        )
        read_only_fields = fields
