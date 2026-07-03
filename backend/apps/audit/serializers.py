"""
审计日志序列化器
"""
from rest_framework import serializers

from .models import OperationLog


class OperationLogListSerializer(serializers.ModelSerializer):
    """操作日志列表精简序列化器"""
    # 操作人姓名
    operator_name = serializers.CharField(source='operator.name', read_only=True, default='')
    # 操作类型显示名称
    operation_type_display = serializers.CharField(
        source='get_operation_type_display', read_only=True
    )
    # 是否成功显示
    is_success_display = serializers.SerializerMethodField()

    class Meta:
        model = OperationLog
        fields = (
            'id', 'operator', 'operator_name', 'operation_type',
            'operation_type_display', 'module', 'object_type', 'object_id',
            'request_method', 'request_path', 'response_status',
            'is_success', 'is_success_display', 'created_at',
        )
        read_only_fields = fields

    def get_is_success_display(self, obj):
        """获取是否成功的显示文本"""
        return '成功' if obj.is_success else '失败'


class OperationLogSerializer(serializers.ModelSerializer):
    """操作日志完整序列化器（详情）"""
    # 操作人姓名
    operator_name = serializers.CharField(source='operator.name', read_only=True, default='')
    # 操作人邮箱
    operator_email = serializers.CharField(source='operator.email', read_only=True, default='')
    # 操作类型显示名称
    operation_type_display = serializers.CharField(
        source='get_operation_type_display', read_only=True
    )
    # 是否成功显示
    is_success_display = serializers.SerializerMethodField()

    class Meta:
        model = OperationLog
        fields = (
            'id', 'operator', 'operator_name', 'operator_email',
            'operation_type', 'operation_type_display',
            'module', 'object_type', 'object_id',
            'description', 'request_method', 'request_path',
            'request_ip', 'user_agent', 'request_data',
            'response_status', 'is_success', 'is_success_display',
            'error_message', 'created_at',
        )
        read_only_fields = fields

    def get_is_success_display(self, obj):
        """获取是否成功的显示文本"""
        return '成功' if obj.is_success else '失败'
