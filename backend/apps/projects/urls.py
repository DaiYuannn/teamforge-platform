"""
项目路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProjectViewSet, ProjectMemberViewSet

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'', ProjectViewSet, basename='project')
router.register(r'members', ProjectMemberViewSet, basename='project-member')

urlpatterns = [
    path('', include(router.urls)),
]
