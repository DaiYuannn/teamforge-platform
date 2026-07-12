"""无障碍 / 可访问性报告路由（N61）"""
from django.urls import path

from .accessibility_views import AccessibilityReportView

urlpatterns = [
    path('report/', AccessibilityReportView.as_view(), name='accessibility-report'),
]
