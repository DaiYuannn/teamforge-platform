"""
自定义看板序列化器
"""
from rest_framework import serializers

from .custom_dashboard_models import CustomDashboard


class CustomDashboardSerializer(serializers.ModelSerializer):
    """自定义看板序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = CustomDashboard
        fields = '__all__'
        read_only_fields = ('id', 'user', 'user_name', 'created_at', 'updated_at')

    def validate_name(self, value):
        """校验同一用户下看板名称唯一"""
        user = self.context['request'].user
        qs = CustomDashboard.objects.filter(user=user, name=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError('该看板名称已存在')
        return value
