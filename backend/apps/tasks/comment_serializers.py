"""
任务评论序列化器
"""
from rest_framework import serializers

from .comment_models import TaskComment
from apps.users.serializers import UserListSerializer


class TaskCommentSerializer(serializers.ModelSerializer):
    """任务评论序列化器"""
    author_detail = UserListSerializer(source='author', read_only=True)
    author_name = serializers.CharField(source='author.name', read_only=True, default='')
    task_title = serializers.CharField(source='task.title', read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = (
            'id', 'task', 'task_title', 'author', 'author_detail', 'author_name',
            'content', 'parent', 'replies',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'author', 'created_at', 'updated_at')

    def get_replies(self, obj):
        """获取直接回复（一级）"""
        replies = obj.replies.all()
        return TaskCommentSerializer(replies, many=True, context=self.context).data
