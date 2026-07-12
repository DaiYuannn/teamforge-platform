"""
N33: 文件分享链接序列化器
- FileShareLinkSerializer: 分享链接序列化
- FileShareLinkCreateSerializer: 创建分享链接时的输入序列化器
"""
from rest_framework import serializers

from .share_models import FileShareLink


class FileShareLinkSerializer(serializers.ModelSerializer):
    """文件分享链接序列化器"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')
    file_name = serializers.CharField(source='file.name', read_only=True, default='')
    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = FileShareLink
        fields = (
            'id', 'file', 'file_name', 'created_by', 'created_by_name',
            'token', 'expire_at', 'max_views', 'view_count',
            'is_active', 'is_expired', 'is_valid', 'created_at',
        )
        read_only_fields = (
            'id', 'created_by', 'token', 'view_count', 'is_active', 'created_at',
        )


class FileShareLinkCreateSerializer(serializers.Serializer):
    """创建分享链接请求序列化器"""
    file = serializers.IntegerField(help_text='文件ID')
    expire_at = serializers.DateTimeField(required=False, allow_null=True, help_text='过期时间')
    max_views = serializers.IntegerField(required=False, allow_null=True, min_value=1, help_text='最大访问次数')
