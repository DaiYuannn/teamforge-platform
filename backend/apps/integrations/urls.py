"""
第三方集成路由
- configs: 集成配置管理
- logs: 集成日志查看
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import IntegrationConfigViewSet, IntegrationLogViewSet

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'configs', IntegrationConfigViewSet, basename='integration-configs')
router.register(r'logs', IntegrationLogViewSet, basename='integration-logs')

urlpatterns = [
    path('', include(router.urls)),
]
