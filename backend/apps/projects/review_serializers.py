"""
项目复盘序列化器
"""
from rest_framework import serializers

from .review_models import ProjectReview


class ProjectReviewSerializer(serializers.ModelSerializer):
    """项目复盘序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProjectReview
        fields = '__all__'
        read_only_fields = ('id', 'reviewer', 'review_date', 'created_at', 'updated_at')

    def validate_score(self, value):
        """评分校验：1-5，允许为空"""
        if value is None:
            return value
        if not isinstance(value, int) or value < 1 or value > 5:
            raise serializers.ValidationError('评分必须在 1-5 之间')
        return value

    def validate_overall_score(self, value):
        return self.validate_score(value)

    def validate_schedule_score(self, value):
        return self.validate_score(value)

    def validate_budget_score(self, value):
        return self.validate_score(value)

    def validate_team_score(self, value):
        return self.validate_score(value)

    def validate_quality_score(self, value):
        return self.validate_score(value)
