"""intellectual_property 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import (
    IntellectualPropertyApplication,
    IPApplicationContributor,
    IPReturnRecord,
    IPMaterialVersion,
    IPObjection,
)


@admin.register(IntellectualPropertyApplication)
class IntellectualPropertyApplicationAdmin(admin.ModelAdmin):
    """知识产权申请管理后台"""
    list_display = (
        'id', 'title', 'application_code', 'ip_type', 'related_project',
        'status', 'main_writer', 'applicant_executor',
        'return_count', 'created_at', 'updated_at',
    )
    list_filter = ('ip_type', 'status')
    search_fields = ('title', 'application_code', 'intro')
    ordering = ('-created_at',)
    raw_id_fields = (
        'related_project', 'main_writer', 'applicant_executor',
        'material_manager', 'project_reviewer', 'teacher_confirmer',
        'final_certificate_file', 'created_by',
    )
    date_hierarchy = 'created_at'


@admin.register(IPApplicationContributor)
class IPApplicationContributorAdmin(admin.ModelAdmin):
    """责任分工管理后台"""
    list_display = (
        'id', 'application', 'user', 'role',
        'is_confirmed', 'confirmed_by', 'confirmed_at', 'created_at',
    )
    list_filter = ('role', 'is_confirmed')
    search_fields = ('application__title', 'user__name',
                     'contribution_description', 'responsibility_description')
    ordering = ('-created_at',)
    raw_id_fields = ('application', 'user', 'confirmed_by')


@admin.register(IPReturnRecord)
class IPReturnRecordAdmin(admin.ModelAdmin):
    """退回修改记录管理后台"""
    list_display = (
        'id', 'application', 'return_time', 'return_source',
        'responsibility_type', 'responsible_user', 'actual_modifier',
        'result', 'modify_deadline', 'created_at',
    )
    list_filter = ('return_source', 'responsibility_type', 'result')
    search_fields = ('application__title', 'return_reason', 'modify_description')
    ordering = ('-return_time',)
    raw_id_fields = ('application', 'responsible_user', 'assigned_by',
                     'actual_modifier', 'proof_file')
    date_hierarchy = 'return_time'


@admin.register(IPMaterialVersion)
class IPMaterialVersionAdmin(admin.ModelAdmin):
    """材料版本管理后台"""
    list_display = (
        'id', 'application', 'file_asset', 'material_type',
        'version', 'uploaded_by', 'is_final', 'created_at',
    )
    list_filter = ('material_type', 'is_final')
    search_fields = ('application__title', 'change_note')
    ordering = ('-created_at',)
    raw_id_fields = ('application', 'file_asset', 'uploaded_by', 'related_return_record')


@admin.register(IPObjection)
class IPObjectionAdmin(admin.ModelAdmin):
    """知识产权异议管理后台"""
    list_display = (
        'id', 'application', 'objector', 'objection_type', 'status',
        'leader_reviewer', 'leader_reviewed_at',
        'teacher_confirmer', 'teacher_confirmed_at',
        'created_at', 'updated_at',
    )
    list_filter = ('objection_type', 'status')
    search_fields = ('application__title', 'content', 'leader_opinion',
                     'teacher_opinion', 'final_result')
    ordering = ('-created_at',)
    raw_id_fields = ('application', 'objector', 'proof_file',
                     'leader_reviewer', 'teacher_confirmer')
    date_hierarchy = 'created_at'
