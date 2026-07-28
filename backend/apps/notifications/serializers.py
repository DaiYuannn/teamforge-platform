"""
通知序列化器
"""
from rest_framework import serializers

from .models import Notification, Announcement


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
            'email_delivery_status', 'email_digest_frequency',
            'email_attempted_at', 'email_sent_at', 'email_delivery_error',
            'is_read', 'read_at', 'related_object_type', 'related_object_id',
            'created_at',
        )
        read_only_fields = fields


class AnnouncementSerializer(serializers.ModelSerializer):
    """公告序列化器"""
    # 类别显示
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    # 状态显示
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    # 发布人姓名
    author_name = serializers.CharField(source='author.name', read_only=True, default='')

    class Meta:
        model = Announcement
        fields = (
            'id', 'title', 'content', 'resource_links',
            'category', 'category_display',
            'status', 'status_display', 'is_pinned', 'is_public',
            'author', 'author_name', 'published_at',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'category_display', 'status_display', 'author_name', 'created_at', 'updated_at')

    def validate_resource_links(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('资源链接必须是列表')
        if len(value) > 20:
            raise serializers.ValidationError('一条公告最多添加 20 个资源链接')

        normalized = []
        url_field = serializers.URLField(max_length=500)
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    f'第 {index + 1} 个资源链接格式不正确'
                )
            title = str(item.get('title') or '').strip()
            url = str(item.get('url') or '').strip()
            if not title or not url:
                raise serializers.ValidationError(
                    f'第 {index + 1} 个资源链接需填写名称和网址'
                )
            if len(title) > 100:
                raise serializers.ValidationError(
                    f'第 {index + 1} 个资源名称不能超过 100 字'
                )
            if not url.lower().startswith(('http://', 'https://')):
                raise serializers.ValidationError(
                    f'第 {index + 1} 个资源链接仅支持 http/https'
                )
            normalized.append({
                'title': title,
                'url': url_field.run_validation(url),
            })
        return normalized


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
            'email_delivery_status', 'email_digest_frequency',
            'email_attempted_at', 'email_sent_at', 'email_delivery_error',
            'is_read', 'read_at', 'related_object_type', 'related_object_id',
            'created_at',
        )
        read_only_fields = fields
