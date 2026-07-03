"""
文件路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FileAssetViewSet

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'', FileAssetViewSet, basename='file')

urlpatterns = [
    path('', include(router.urls)),
]
