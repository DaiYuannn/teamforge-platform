"""tasks 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import Task, TaskLog


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """任务管理后台"""
    list_display = (
        'id', 'title', 'project', 'assignee', 'creator',
        'status', 'deadline', 'is_overdue', 'completed_at', 'created_at',
    )
    list_filter = ('status',)
    search_fields = ('title', 'description', 'project__name')
    ordering = ('-created_at',)
    raw_id_fields = ('project', 'assignee', 'creator', 'reviewer', 'collaborators')


@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    """任务日志管理后台"""
    list_display = ('id', 'task', 'from_status', 'to_status', 'operator', 'created_at')
    list_filter = ('to_status',)
    search_fields = ('task__title',)
    raw_id_fields = ('task', 'operator')
