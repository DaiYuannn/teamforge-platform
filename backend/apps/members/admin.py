"""members 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import SkillTag, MemberSkill, FlexibleWorkSchedule


@admin.register(SkillTag)
class SkillTagAdmin(admin.ModelAdmin):
    """技能标签管理后台"""
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)


@admin.register(MemberSkill)
class MemberSkillAdmin(admin.ModelAdmin):
    """成员技能管理后台"""
    list_display = ('id', 'user', 'skill', 'proficiency', 'created_at')
    list_filter = ('proficiency',)
    search_fields = ('user__name', 'skill__name')
    raw_id_fields = ('user', 'skill')


@admin.register(FlexibleWorkSchedule)
class FlexibleWorkScheduleAdmin(admin.ModelAdmin):
    """灵活工时管理后台"""
    list_display = (
        'id', 'user', 'period_start', 'period_end',
        'work_hours', 'can_offline', 'can_urgent', 'is_saturated', 'filled_at',
    )
    list_filter = ('can_offline', 'can_urgent', 'is_saturated')
    search_fields = ('user__name',)
    raw_id_fields = ('user',)
