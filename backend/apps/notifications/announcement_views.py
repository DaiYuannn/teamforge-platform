"""
公告视图
- AnnouncementViewSet: 公告 CRUD + 置顶/取消置顶 + 公开列表
关键：
- 已发布公告对所有认证用户可见；草稿仅老师/管理员可见
- 创建/更新/删除仅老师/管理员可操作
- public 接口无需登录，返回公开（is_public=True）的已发布公告
"""
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ModelViewSet

from common.response import success_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from .models import Announcement
from .serializers import AnnouncementSerializer
from .announcement_access import (
    can_manage_announcement,
    can_manage_announcements,
    scope_announcements_for_user,
)


class IsAnnouncementManager(BasePermission):
    def has_permission(self, request, view):
        return can_manage_announcements(getattr(request, 'user', None))

    def has_object_permission(self, request, view, obj):
        return can_manage_announcement(request.user, obj)


class AnnouncementViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    公告管理 ViewSet
    - list/retrieve: 所有认证用户可查看已发布公告；老师/管理员可查看草稿
    - create/update/destroy: 老师/管理员
    - pin: POST 置顶/取消置顶（老师/管理员）
    - public: GET 公开公告列表（无需登录）
    """
    queryset = (
        Announcement.objects
        .select_related('author', 'organization')
        .prefetch_related('target_teams', 'target_projects')
        .all()
    )

    serializer_classes_by_action = {
        'list': AnnouncementSerializer,
        'retrieve': AnnouncementSerializer,
        'create': AnnouncementSerializer,
        'update': AnnouncementSerializer,
        'partial_update': AnnouncementSerializer,
        'pin': AnnouncementSerializer,
        'public': AnnouncementSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAnnouncementManager],
        'update': [IsAnnouncementManager],
        'partial_update': [IsAnnouncementManager],
        'destroy': [IsAnnouncementManager],
        'pin': [IsAnnouncementManager],
        'public': [AllowAny],
    }

    filterset_fields = [
        'category', 'status', 'audience', 'organization',
        'target_teams', 'target_projects', 'is_pinned', 'is_public', 'author',
    ]
    search_fields = ['title', 'content', 'author__name']
    ordering_fields = ['created_at', 'published_at', 'updated_at']

    def get_queryset(self):
        """
        - 老师/管理员：可见全部公告（含草稿、已归档）
        - 普通成员及其他认证用户：仅可见已发布公告
        """
        queryset = super().get_queryset()
        user = self.request.user
        # public 接口走 AllowAny，可能为匿名用户，单独在 action 中处理
        if self.action == 'public':
            return queryset.filter(
                status=Announcement.Status.PUBLISHED,
            ).filter(
                Q(audience=Announcement.Audience.PUBLIC) | Q(is_public=True)
            )
        return scope_announcements_for_user(
            queryset,
            user,
            include_manageable=can_manage_announcements(user),
        )

    def list(self, request, *args, **kwargs):
        """公告列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """公告详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """创建公告"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(
            self.get_serializer(serializer.instance).data,
            message='公告创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer):
        """创建时设置作者，并在发布时记录发布时间"""
        published_at = None
        if serializer.validated_data.get('status') == Announcement.Status.PUBLISHED:
            published_at = timezone.now()
        serializer.save(author=self.request.user, published_at=published_at)

    def update(self, request, *args, **kwargs):
        """更新公告"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(
            self.get_serializer(serializer.instance).data,
            message='公告更新成功',
        )

    def perform_update(self, serializer):
        """更新时若状态变为已发布且尚未发布，则记录发布时间"""
        instance = serializer.instance
        new_status = serializer.validated_data.get('status', instance.status)
        published_at = instance.published_at
        if new_status == Announcement.Status.PUBLISHED and not published_at:
            published_at = timezone.now()
        serializer.save(published_at=published_at)

    def destroy(self, request, *args, **kwargs):
        """删除公告"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='公告删除成功')

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """
        置顶/取消置顶公告
        POST /api/v1/notifications/announcements/{id}/pin/
        """
        announcement = self.get_object()
        announcement.is_pinned = not announcement.is_pinned
        announcement.save(update_fields=['is_pinned', 'updated_at'])
        message = '已置顶' if announcement.is_pinned else '已取消置顶'
        return success_response(
            self.get_serializer(announcement).data,
            message=message,
        )

    @action(detail=False, methods=['get'])
    def public(self, request):
        """
        公开公告列表（无需登录）
        GET /api/v1/notifications/announcements/public/
        返回 is_public=True 且已发布的公告
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)
