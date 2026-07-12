"""安全扫描路由"""
from django.urls import path

from .security_views import SecurityScanView

urlpatterns = [
    path('', SecurityScanView.as_view(), name='security-scan'),
]
