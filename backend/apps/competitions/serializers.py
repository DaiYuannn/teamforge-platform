"""
比赛序列化器
"""
from rest_framework import serializers

from .models import Competition


class CompetitionSerializer(serializers.ModelSerializer):
    """比赛完整序列化器"""
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Competition
        fields = (
            'id', 'project', 'project_name', 'name', 'comp_type',
            'level', 'level_display', 'organizer',
            'register_date', 'material_deadline', 'review_date', 'defense_date',
            'school_date', 'city_date', 'province_date', 'national_date', 'result_date',
            'status', 'status_display',
            'is_promoted', 'is_awarded', 'award_level',
            'not_promoted_reason', 'improvement_suggestion', 'review_summary',
            'current_stage', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class CompetitionListSerializer(serializers.ModelSerializer):
    """比赛列表精简序列化器"""
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Competition
        fields = (
            'id', 'project', 'project_name', 'name', 'comp_type',
            'level', 'level_display', 'organizer', 'status', 'status_display',
            'is_promoted', 'is_awarded', 'award_level',
            'current_stage',
            'register_date', 'defense_date', 'result_date',
            'created_at',
        )
        read_only_fields = fields
