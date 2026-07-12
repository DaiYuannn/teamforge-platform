"""tasks 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import Task, TaskLog
from .subtask_models import SubTask
from .dependency_models import TaskDependency
from .comment_models import TaskComment


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


@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    """子任务管理后台"""
    list_display = ('id', 'parent', 'title', 'assignee', 'is_completed', 'sort_order', 'created_at')
    list_filter = ('is_completed',)
    search_fields = ('title', 'parent__title')
    raw_id_fields = ('parent', 'assignee')


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    """任务依赖关系管理后台"""
    list_display = ('id', 'task', 'depends_on', 'created_at')
    search_fields = ('task__title', 'depends_on__title')
    raw_id_fields = ('task', 'depends_on')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """任务评论管理后台"""
    list_display = ('id', 'task', 'author', 'parent', 'created_at', 'updated_at')
    search_fields = ('content', 'task__title', 'author__name')
    raw_id_fields = ('task', 'author', 'parent')
