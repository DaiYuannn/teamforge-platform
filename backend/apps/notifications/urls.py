"""
通知路由（架构预留）
- notifications: 通知 CRUD + 标记已读等
- announcements: 公告 CRUD + 置顶 + 公开列表
- sse: SSE 实时通知推送
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet
from .announcement_views import AnnouncementViewSet
from .sse_views import NotificationSSEView

router = DefaultRouter()
# 公告路由需在空前缀的通知路由之前注册，避免通知详情路由 ^(?P<pk>[^/.]+)/$ 拦截 announcements/
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    # SSE 路由需在 router 之前，避免被通知详情路由 ^(?P<pk>[^/.]+)/$ 拦截
    path('sse/', NotificationSSEView.as_view(), name='notification-sse'),
    path('', include(router.urls)),
]
