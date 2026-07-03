"""contributions 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import Contribution, MemberRanking, RankingObjection


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    """贡献记录管理后台"""
    list_display = (
        'id', 'project', 'user', 'contribution_type',
        'status', 'weight', 'filled_by', 'reviewer', 'reviewed_at',
        'period', 'created_at',
    )
    list_filter = ('contribution_type', 'status', 'period')
    search_fields = ('project__name', 'user__name', 'content', 'description')
    ordering = ('-created_at',)
    raw_id_fields = ('project', 'user', 'proof_file', 'filled_by', 'reviewer')


@admin.register(MemberRanking)
class MemberRankingAdmin(admin.ModelAdmin):
    """成员排名管理后台"""
    list_display = (
        'id', 'project', 'user', 'period', 'status', 'rank', 'total_score',
        'is_public', 'created_at',
    )
    list_filter = ('status', 'is_public', 'period')
    search_fields = ('project__name', 'user__name', 'period')
    ordering = ('period', 'rank')
    raw_id_fields = ('project', 'user')


@admin.register(RankingObjection)
class RankingObjectionAdmin(admin.ModelAdmin):
    """排名异议管理后台"""
    list_display = (
        'id', 'ranking', 'objector', 'status',
        'leader_reviewer', 'leader_reviewed_at',
        'teacher_confirmer', 'teacher_confirmed_at',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('ranking__user__name', 'objector__name', 'content')
    ordering = ('-created_at',)
    raw_id_fields = ('ranking', 'objector', 'leader_reviewer', 'teacher_confirmer', 'handler')
