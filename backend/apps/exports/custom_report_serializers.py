"""自定义报表与定时报表序列化器。"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.users.models import User
from .custom_report_models import CustomReport
from .scheduled_report_models import ScheduledReport, ScheduledReportExecution


class CustomReportSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')

    class Meta:
        model = CustomReport
        fields = '__all__'
        read_only_fields = ('id', 'created_by', 'created_by_name', 'created_at', 'updated_at')

    def validate_report_type(self, value):
        if value not in CustomReport.ReportType.values:
            raise serializers.ValidationError('Unsupported report type')
        return value

    def validate_config(self, value):
        value = value or {}
        if value.get('data_source', 'project') not in {
            'project', 'task', 'finance', 'competition',
        }:
            raise serializers.ValidationError('Unsupported data source')
        if value.get('chart_type', 'table') not in {'table', 'bar', 'line', 'pie'}:
            raise serializers.ValidationError('Unsupported chart type')
        if not isinstance(value.get('filters', {}), dict):
            raise serializers.ValidationError('filters must be an object')
        return value


class ScheduledReportExecutionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    trigger_display = serializers.CharField(source='get_trigger_display', read_only=True)
    delivery_status_display = serializers.CharField(
        source='get_delivery_status_display',
        read_only=True,
    )
    download_url = serializers.SerializerMethodField()
    last_run = serializers.DateTimeField(source='schedule.last_run', read_only=True)
    next_run = serializers.DateTimeField(source='schedule.next_run', read_only=True)

    class Meta:
        model = ScheduledReportExecution
        fields = (
            'id', 'schedule', 'trigger', 'trigger_display', 'status', 'status_display',
            'file_name', 'file_format', 'file_size', 'delivery_status',
            'delivery_status_display', 'recipient_snapshot', 'message', 'error',
            'started_at', 'finished_at', 'generated_by', 'download_url',
            'last_run', 'next_run',
        )
        read_only_fields = fields

    def get_download_url(self, obj) -> str:
        if not obj.file:
            return ''
        return f'/exports/scheduled-reports/{obj.schedule_id}/executions/{obj.pk}/download/'


class ScheduledReportSerializer(serializers.ModelSerializer):
    report_name = serializers.CharField(source='report.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    file_format_display = serializers.CharField(source='get_file_format_display', read_only=True)
    last_status_display = serializers.CharField(source='get_last_status_display', read_only=True)
    recipient_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.filter(
            is_active=True,
            membership_status__in=[
                User.MembershipStatus.ACTIVE,
                User.MembershipStatus.ON_LEAVE,
            ],
        ),
        source='recipients',
        required=False,
    )
    recipient_names = serializers.SerializerMethodField()
    recent_executions = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledReport
        fields = (
            'id', 'report', 'report_name', 'created_by', 'created_by_name',
            'recipient_ids', 'recipient_names', 'frequency', 'frequency_display',
            'execution_time', 'weekday', 'day_of_month', 'timezone',
            'file_format', 'file_format_display', 'last_run', 'next_run',
            'last_status', 'last_status_display', 'last_error', 'is_active',
            'recent_executions', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'created_by', 'created_by_name', 'last_run', 'next_run',
            'last_status', 'last_status_display', 'last_error', 'created_at',
            'updated_at', 'report_name', 'frequency_display',
            'file_format_display', 'recipient_names', 'recent_executions',
        )

    def validate_weekday(self, value):
        if not 0 <= value <= 6:
            raise serializers.ValidationError('周几必须在 0（周一）到 6（周日）之间。')
        return value

    def validate_day_of_month(self, value):
        if not 1 <= value <= 28:
            raise serializers.ValidationError('每月日期必须在 1 到 28 之间。')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        report = attrs.get('report') or getattr(self.instance, 'report', None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError('需要登录后配置定时报表。')
        if (
            report
            and user.global_role not in ('teacher', 'sys_admin')
            and report.created_by_id != user.id
        ):
            raise serializers.ValidationError({
                'report': '只能为自己创建的报表配置发送计划。'
            })
        recipients = attrs.get('recipients')
        if recipients is None and self.instance is not None:
            recipients = list(self.instance.recipients.all())
        if recipients is not None:
            invalid = [
                recipient.id
                for recipient in recipients
                if (
                    not recipient.is_active
                    or recipient.membership_status
                    not in {
                        User.MembershipStatus.ACTIVE,
                        User.MembershipStatus.ON_LEAVE,
                    }
                )
            ]
            if invalid:
                raise serializers.ValidationError({
                    'recipient_ids': '接收人必须是在队或暂离的内部成员。'
                })
        return attrs

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_recipient_names(self, obj):
        return [user.name for user in obj.recipients.all()]

    @extend_schema_field(ScheduledReportExecutionSerializer(many=True))
    def get_recent_executions(self, obj):
        records = list(obj.executions.all()[:5])
        return ScheduledReportExecutionSerializer(records, many=True).data
