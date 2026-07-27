"""
通知视图
- NotificationViewSet: 通知查询 + 标记已读 + 未读数量统计 + 删除/清空
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from .models import Notification
from .serializers import NotificationSerializer, NotificationListSerializer
from .services import NotificationService


class NotificationViewSet(MultiSerializerMixin, ReadOnlyModelViewSet):
    """
    通知 ViewSet
    - list: 当前用户的通知列表，支持按 is_read/notification_type/category/channel 筛选
    - retrieve: 通知详情
    - mark_as_read: POST 标记单条通知已读
    - mark_all_as_read: POST 标记全部已读
    - unread_count: GET 获取未读数量
    - delete: DELETE/POST 删除单条通知
    - clear_all: POST 清空当前用户全部已读通知
    - delete_read: POST 删除当前用户全部已读通知
    """
    serializer_classes_by_action = {
        'list': NotificationListSerializer,
        'retrieve': NotificationSerializer,
    }
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户的通知"""
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        queryset = Notification.objects.select_related('recipient', 'sender').filter(
            recipient=self.request.user,
            channel=Notification.Channel.INAPP,
        )

        # 按是否已读筛选
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            if is_read.lower() in ('true', '1'):
                queryset = queryset.filter(is_read=True)
            elif is_read.lower() in ('false', '0'):
                queryset = queryset.filter(is_read=False)

        # 按通知类型筛选（notification_type，与 category 等价，兼容两种参数名）
        notification_type = self.request.query_params.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        # 按通知类型筛选（兼容旧参数名 category）
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(notification_type=category)

        # 按渠道筛选
        channel = self.request.query_params.get('channel')
        if channel:
            queryset = queryset.filter(channel=channel)

        return queryset

    def list(self, request, *args, **kwargs):
        """当前用户的通知列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """通知详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        标记单条通知已读
        POST /api/v1/notifications/{id}/mark_as_read/
        """
        success, message = NotificationService.mark_as_read(pk, request.user)
        if not success:
            return error_response(message=message, code=1004,
                                  http_status=status.HTTP_404_NOT_FOUND)
        return success_response(message=message)

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """
        标记当前用户全部通知已读
        POST /api/v1/notifications/mark_all_as_read/
        """
        count = NotificationService.mark_all_as_read(request.user)
        return success_response(
            data={'count': count},
            message=f'已标记 {count} 条通知为已读',
        )

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        获取当前用户未读通知数量
        GET /api/v1/notifications/unread_count/
        """
        count = NotificationService.get_unread_count(request.user)
        return success_response(data={'count': count})

    @action(detail=True, methods=['delete', 'post'])
    def delete(self, request, pk=None):
        """
        删除单条通知（仅可删除自己的通知）
        DELETE/POST /api/v1/notifications/{id}/delete/
        """
        instance = self.get_object()
        instance.delete()
        return success_response(message='通知已删除')

    @action(detail=False, methods=['post'])
    def clear_all(self, request):
        """
        清空当前用户全部已读通知
        POST /api/v1/notifications/clear_all/
        """
        count, _ = Notification.objects.filter(
            recipient=request.user,
            channel=Notification.Channel.INAPP,
            is_read=True,
        ).delete()
        return success_response(
            data={'count': count},
            message=f'已清空 {count} 条已读通知',
        )

    @action(detail=False, methods=['post'])
    def delete_read(self, request):
        """
        删除当前用户全部已读通知
        POST /api/v1/notifications/delete_read/
        """
        count, _ = Notification.objects.filter(
            recipient=request.user,
            channel=Notification.Channel.INAPP,
            is_read=True,
        ).delete()
        return success_response(
            data={'count': count},
            message=f'已删除 {count} 条已读通知',
        )
