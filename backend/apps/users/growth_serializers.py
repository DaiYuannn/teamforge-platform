"""
成员成长记录序列化器
"""
from rest_framework import serializers

from .growth_models import MemberGrowth


class MemberGrowthSerializer(serializers.ModelSerializer):
    """成员成长记录序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')

    class Meta:
        model = MemberGrowth
        fields = (
            'id', 'user', 'user_name', 'period',
            'project_count', 'task_count', 'contribution_score',
            'skill_count', 'notes', 'created_at',
        )
        read_only_fields = ('id', 'created_at')
