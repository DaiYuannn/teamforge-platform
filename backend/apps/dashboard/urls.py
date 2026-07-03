"""
驾驶舱路由
"""
from django.urls import path

from .views import DashboardView

urlpatterns = [
    # 驾驶舱聚合数据
    path('', DashboardView.as_view(), name='dashboard'),
]
