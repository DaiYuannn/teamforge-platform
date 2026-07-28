"""competitions 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import Competition, CompetitionParticipant


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    """比赛管理后台"""
    list_display = (
        'id', 'name', 'project', 'level', 'status',
        'is_promoted', 'is_awarded', 'award_level', 'created_at',
    )
    list_filter = ('level', 'status', 'is_promoted', 'is_awarded')
    search_fields = ('name', 'project__name', 'organizer')
    ordering = ('-created_at',)
    raw_id_fields = ('project',)


@admin.register(CompetitionParticipant)
class CompetitionParticipantAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'competition', 'user', 'role', 'participation_status', 'joined_at',
    )
    list_filter = ('role', 'participation_status')
    search_fields = ('competition__name', 'user__name', 'user__email')
    raw_id_fields = ('competition', 'user')
