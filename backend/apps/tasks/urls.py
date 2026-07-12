"""
任务路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TaskViewSet
from .subtask_views import SubTaskViewSet
from .dependency_views import TaskDependencyViewSet
from .comment_views import TaskCommentViewSet

# 创建路由器并注册 ViewSet
# 注意：带前缀的路由（subtasks/dependencies/comments）必须先注册，
# 否则空前缀 TaskViewSet 的详情路由 (?P<pk>[^/.]+)/ 会先匹配到它们
router = DefaultRouter()
router.register(r'subtasks', SubTaskViewSet, basename='subtask')
router.register(r'dependencies', TaskDependencyViewSet, basename='task-dependency')
router.register(r'comments', TaskCommentViewSet, basename='task-comment')
router.register(r'', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]
