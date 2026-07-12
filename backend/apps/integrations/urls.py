"""
第三方集成路由
- configs: 集成配置管理
- logs: 集成日志查看
- bot-push/test: 群机器人推送测试
- external-platforms: 外部平台集成（N44）
- git-repositories: Git 集成（N45）
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import IntegrationConfigViewSet, IntegrationLogViewSet, BotPushTestView, WebhookConfigViewSet

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'configs', IntegrationConfigViewSet, basename='integration-configs')
router.register(r'logs', IntegrationLogViewSet, basename='integration-logs')
router.register(r'webhooks', WebhookConfigViewSet, basename='webhook-configs')

urlpatterns = [
    # 群机器人推送测试
    path('bot-push/test/', BotPushTestView.as_view(), name='bot-push-test'),
    # 外部平台集成（N44）- 必须在空前缀路由之前
    path('external-platforms/', include('apps.integrations.external_urls')),
    # Git 集成（N45）- 必须在空前缀路由之前
    path('git-repositories/', include('apps.integrations.git_urls')),
    path('', include(router.urls)),
]
