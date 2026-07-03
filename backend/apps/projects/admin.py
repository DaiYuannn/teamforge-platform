"""projects 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import Project, ProjectMember, ProjectStageLog


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """项目管理后台"""
    list_display = ('id', 'name', 'code', 'leader', 'current_stage', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'current_stage')
    search_fields = ('name', 'code', 'intro')
    ordering = ('-created_at',)
    raw_id_fields = ('leader',)


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    """项目成员管理后台"""
    list_display = ('id', 'project', 'user', 'role_in_project', 'joined_at')
    list_filter = ('role_in_project',)
    search_fields = ('project__name', 'user__name', 'user__email')
    raw_id_fields = ('project', 'user')


@admin.register(ProjectStageLog)
class ProjectStageLogAdmin(admin.ModelAdmin):
    """项目阶段日志管理后台"""
    list_display = ('id', 'project', 'from_stage', 'to_stage', 'operator', 'created_at')
    list_filter = ('to_stage',)
    search_fields = ('project__name', 'note')
    raw_id_fields = ('project', 'operator')
