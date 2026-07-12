"""健康检查路由（N58）"""
from django.urls import path

from .health_check_views import HealthCheckView

urlpatterns = [
    path('', HealthCheckView.as_view(), name='health-check'),
]
