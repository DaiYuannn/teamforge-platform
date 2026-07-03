"""
比赛路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CompetitionViewSet

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'', CompetitionViewSet, basename='competition')

urlpatterns = [
    path('', include(router.urls)),
]
