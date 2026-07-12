"""
自定义报表序列化器
"""
from rest_framework import serializers

from apps.users.models import User
from .custom_report_models import CustomReport
from .scheduled_report_models import ScheduledReport


class CustomReportSerializer(serializers.ModelSerializer):
    """自定义报表序列化器"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = CustomReport
        fields = '__all__'
        read_only_fields = ('id', 'created_by', 'created_by_name', 'created_at', 'updated_at')


class ScheduledReportSerializer(serializers.ModelSerializer):
    """定时报表序列化器"""
    report_name = serializers.CharField(source='report.name', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    recipient_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(),
        source='recipients', required=False
    )
    recipient_names = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledReport
        fields = '__all__'
        read_only_fields = (
            'id', 'last_run', 'next_run', 'created_at', 'updated_at',
            'report_name', 'frequency_display', 'recipient_names',
        )

    def get_recipient_names(self, obj):
        return [u.name for u in obj.recipients.all()]
