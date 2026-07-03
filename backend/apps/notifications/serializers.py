"""
通知序列化器
"""
from rest_framework import serializers

from .models import Notification


class NotificationListSerializer(serializers.ModelSerializer):
    """通知列表精简序列化器"""
    # 接收人姓名
    recipient_name = serializers.CharField(source='recipient.name', read_only=True, default='')
    # 发送人姓名
    sender_name = serializers.CharField(source='sender.name', read_only=True, default='')
    # 通知类型显示
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    # 优先级显示
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True
    )
    # 渠道显示
    channel_display = serializers.CharField(
        source='get_channel_display', read_only=True
    )

    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'recipient_name', 'sender', 'sender_name',
            'title', 'content', 'notification_type', 'notification_type_display',
            'priority', 'priority_display', 'channel', 'channel_display',
            'is_read', 'read_at', 'related_object_type', 'related_object_id',
            'created_at',
        )
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    """通知完整序列化器（详情）"""
    # 接收人姓名
    recipient_name = serializers.CharField(source='recipient.name', read_only=True, default='')
    # 发送人姓名
    sender_name = serializers.CharField(source='sender.name', read_only=True, default='')
    # 通知类型显示
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )
    # 优先级显示
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True
    )
    # 渠道显示
    channel_display = serializers.CharField(
        source='get_channel_display', read_only=True
    )

    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'recipient_name', 'sender', 'sender_name',
            'title', 'content', 'notification_type', 'notification_type_display',
            'priority', 'priority_display', 'channel', 'channel_display',
            'is_read', 'read_at', 'related_object_type', 'related_object_id',
            'created_at',
        )
        read_only_fields = fields
