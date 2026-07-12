"""
子任务序列化器
"""
from rest_framework import serializers

from .subtask_models import SubTask
from apps.users.serializers import UserListSerializer


class SubTaskSerializer(serializers.ModelSerializer):
    """子任务序列化器"""
    assignee_detail = UserListSerializer(source='assignee', read_only=True)
    assignee_name = serializers.CharField(source='assignee.name', read_only=True, default='')
    parent_title = serializers.CharField(source='parent.title', read_only=True)

    class Meta:
        model = SubTask
        fields = (
            'id', 'parent', 'parent_title', 'title',
            'assignee', 'assignee_detail', 'assignee_name',
            'is_completed', 'completed_at', 'sort_order', 'created_at',
        )
        read_only_fields = ('id', 'completed_at', 'created_at')
