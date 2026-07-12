"""
讨论区序列化器
- DiscussionTopicSerializer: 主题序列化（含回复列表）
- DiscussionReplySerializer: 回复序列化
- DiscussionReplyCreateSerializer: 创建回复时的精简序列化器
"""
from rest_framework import serializers

from .discussion_models import DiscussionTopic, DiscussionReply


class DiscussionReplySerializer(serializers.ModelSerializer):
    """讨论回复序列化器"""
    author_name = serializers.CharField(source='author.name', read_only=True, default='')
    parent = serializers.PrimaryKeyRelatedField(
        queryset=DiscussionReply.objects.all(),
        required=False, allow_null=True,
    )

    class Meta:
        model = DiscussionReply
        fields = (
            'id', 'topic', 'author', 'author_name',
            'content', 'parent', 'created_at',
        )
        read_only_fields = ('id', 'author', 'created_at')


class DiscussionTopicSerializer(serializers.ModelSerializer):
    """讨论主题序列化器"""
    author_name = serializers.CharField(source='author.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    replies = DiscussionReplySerializer(many=True, read_only=True)

    class Meta:
        model = DiscussionTopic
        fields = (
            'id', 'project', 'project_name', 'title', 'content',
            'author', 'author_name', 'is_pinned', 'is_closed',
            'view_count', 'reply_count', 'replies',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'author', 'view_count', 'reply_count',
            'created_at', 'updated_at',
        )


class DiscussionTopicListSerializer(serializers.ModelSerializer):
    """讨论主题列表精简序列化器（不含回复列表）"""
    author_name = serializers.CharField(source='author.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')

    class Meta:
        model = DiscussionTopic
        fields = (
            'id', 'project', 'project_name', 'title',
            'author', 'author_name', 'is_pinned', 'is_closed',
            'view_count', 'reply_count',
            'created_at', 'updated_at',
        )
        read_only_fields = fields
