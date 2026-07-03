"""
通知视图
- NotificationViewSet: 通知只读查询 + 标记已读 + 未读数量统计
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
    - list: 当前用户的通知列表，支持按 is_read/category 筛选
    - retrieve: 通知详情
    - mark_as_read: POST 标记单条通知已读
    - mark_all_as_read: POST 标记全部已读
    - unread_count: GET 获取未读数量
    """
    serializer_classes_by_action = {
        'list': NotificationListSerializer,
        'retrieve': NotificationSerializer,
    }
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户的通知"""
        queryset = Notification.objects.select_related('recipient', 'sender').filter(
            recipient=self.request.user
        )

        # 按是否已读筛选
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            if is_read.lower() in ('true', '1'):
                queryset = queryset.filter(is_read=True)
            elif is_read.lower() in ('false', '0'):
                queryset = queryset.filter(is_read=False)

        # 按通知类型筛选
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
