"""
动态流（Activity Feed）路由
- GET /api/v1/activities/                      全局动态流（分页，可按 project/type/actor 过滤）
- GET /api/v1/activities/project/<project_id>/ 指定项目的动态流（分页）
"""
from django.urls import path

from .activity_views import ActivityFeedView, ProjectActivityView

urlpatterns = [
    path('', ActivityFeedView.as_view(), name='activity-feed'),
    path('project/<int:project_id>/', ProjectActivityView.as_view(), name='project-activity'),
]
