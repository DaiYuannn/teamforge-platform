"""
任务路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TaskViewSet

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]
