"""
多团队路由
- /api/v1/teams/                团队 CRUD + 成员管理（members action）
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .team_views import TeamViewSet

router = DefaultRouter()
router.register(r'', TeamViewSet, basename='team')

urlpatterns = [
    path('', include(router.urls)),
]
