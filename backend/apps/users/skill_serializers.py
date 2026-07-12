"""
成员技能序列化器
"""
from rest_framework import serializers

from .skill_models import MemberSkill


class MemberSkillSerializer(serializers.ModelSerializer):
    """成员技能序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')

    class Meta:
        model = MemberSkill
        fields = (
            'id', 'user', 'user_name', 'name',
            'level', 'certified', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_level(self, value):
        """熟练度范围 1-5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError('熟练度范围为 1-5')
        return value
