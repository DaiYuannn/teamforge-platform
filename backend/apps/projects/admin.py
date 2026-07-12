"""projects 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import Project, ProjectMember, ProjectStageLog
from .milestone_models import Milestone
from .risk_models import ProjectRisk
from .template_models import ProjectTemplate


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


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    """项目里程碑管理后台"""
    list_display = ('id', 'project', 'title', 'due_date', 'is_completed', 'sort_order', 'created_at')
    list_filter = ('is_completed',)
    search_fields = ('title', 'project__name')
    raw_id_fields = ('project',)


@admin.register(ProjectRisk)
class ProjectRiskAdmin(admin.ModelAdmin):
    """项目风险管理后台"""
    list_display = ('id', 'project', 'title', 'level', 'status', 'identified_by', 'identified_at', 'resolved_at')
    list_filter = ('level', 'status')
    search_fields = ('title', 'project__name')
    raw_id_fields = ('project', 'identified_by')


@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(admin.ModelAdmin):
    """项目模板管理后台"""
    list_display = ('id', 'name', 'category', 'created_by', 'is_active', 'created_at')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'description', 'category')
    raw_id_fields = ('created_by',)
