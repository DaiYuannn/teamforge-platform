"""
项目里程碑序列化器
"""
from rest_framework import serializers

from .milestone_models import Milestone


class MilestoneSerializer(serializers.ModelSerializer):
    """项目里程碑序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Milestone
        fields = (
            'id', 'project', 'project_name', 'title', 'description',
            'due_date', 'is_completed', 'completed_at',
            'sort_order', 'created_at',
        )
        read_only_fields = ('id', 'completed_at', 'created_at')
