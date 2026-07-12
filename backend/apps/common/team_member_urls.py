"""
团队成员路由（独立 CRUD）
- /api/v1/team-members/         团队成员 CRUD
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .team_views import TeamMemberViewSet

member_router = DefaultRouter()
member_router.register(r'', TeamMemberViewSet, basename='team-member')

urlpatterns = [
    path('', include(member_router.urls)),
]
