"""
Git 集成路由
- /api/v1/integrations/git-repositories/   Git 仓库 CRUD
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .git_views import GitRepositoryViewSet

git_router = DefaultRouter()
git_router.register(r'', GitRepositoryViewSet, basename='git-repository')

urlpatterns = [
    path('', include(git_router.urls)),
]
