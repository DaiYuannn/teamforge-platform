"""
数据导入路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ImportTaskViewSet

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'tasks', ImportTaskViewSet, basename='import-task')

urlpatterns = [
    path('', include(router.urls)),
]
