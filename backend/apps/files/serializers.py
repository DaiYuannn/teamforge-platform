"""
文件序列化器
"""
from rest_framework import serializers

from .models import FileAsset, FileVersion
from .tag_models import FileTag, FileTagRelation


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
            'file_hash', 'watermark_text',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'size', 'content_type', 'uploader', 'version', 'file_hash', 'created_at', 'updated_at')

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
            'uploader_name', 'version', 'file_hash', 'watermark_text', 'created_at',
        )
        read_only_fields = fields


class FileTagSerializer(serializers.ModelSerializer):
    """文件标签序列化器"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')

    class Meta:
        model = FileTag
        fields = (
            'id', 'name', 'color', 'project', 'project_name',
            'created_by', 'created_by_name', 'created_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at')
        extra_kwargs = {
            # project 允许为空（全局标签），显式声明非必填
            'project': {'required': False, 'allow_null': True},
        }
        # 清除自动生成的 UniqueTogetherValidator：它会把 unique_together 中的
        # project 字段强制变为必填，与"全局标签 project 可为空"的需求冲突。
        # 唯一性约束仍由数据库层面的 unique_together 保证。
        validators = []


class FileTagRelationSerializer(serializers.ModelSerializer):
    """文件-标签关联序列化器"""
    tag_name = serializers.CharField(source='tag.name', read_only=True, default='')
    tag_color = serializers.CharField(source='tag.color', read_only=True, default='')
    file_name = serializers.CharField(source='file.name', read_only=True, default='')

    class Meta:
        model = FileTagRelation
        fields = (
            'id', 'file', 'file_name', 'tag', 'tag_name', 'tag_color', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class AssignTagsSerializer(serializers.Serializer):
    """分配/取消标签请求序列化器"""
    file = serializers.IntegerField(help_text='文件ID')
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='标签ID列表',
    )
