"""
前端错误监控路由（N57 错误监控）
- GET  /api/v1/common/error-logs/   列表
- POST /api/v1/common/error-logs/   创建
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .error_monitoring_views import ErrorLogViewSet

router = DefaultRouter()
router.register(r'', ErrorLogViewSet, basename='error-log')

urlpatterns = [
    path('', include(router.urls)),
]
