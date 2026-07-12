"""
统一待办路由
- GET /api/v1/todo/  获取当前用户的统一待办列表
"""
from django.urls import path

from .todo_views import UnifiedTodoView

urlpatterns = [
    path('', UnifiedTodoView.as_view(), name='unified-todo'),
]
