"""
项目风险序列化器
"""
from rest_framework import serializers

from .risk_models import ProjectRisk


class ProjectRiskSerializer(serializers.ModelSerializer):
    """项目风险序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    identified_by_name = serializers.CharField(source='identified_by.name', read_only=True, default='')

    class Meta:
        model = ProjectRisk
        fields = (
            'id', 'project', 'project_name', 'title', 'description',
            'level', 'level_display', 'status', 'status_display',
            'mitigation_plan', 'identified_by', 'identified_by_name',
            'identified_at', 'resolved_at',
        )
        read_only_fields = ('id', 'identified_at', 'resolved_at')
