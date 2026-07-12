"""性能监控路由（N59）"""
from django.urls import path

from .performance_views import PerformanceMetricsView, SlowQueryLogView

urlpatterns = [
    path('metrics/', PerformanceMetricsView.as_view(), name='performance-metrics'),
    path('slow-queries/', SlowQueryLogView.as_view(), name='slow-query-log'),
]
