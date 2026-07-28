"""
文件权限
三级权限校验:
- public: 同一根组织内的认证成员可下载
- internal: IsProjectMember（项目成员可下载）
- sensitive: 只能走敏感资料申请/审计下载端点
"""
from django.db.models import Q
from rest_framework.permissions import BasePermission, SAFE_METHODS
from common.project_access import (
    active_user_root_team_ids,
    has_active_project_membership,
    has_organization_project_access,
    is_exited_member,
    is_external_collaborator,
    project_can_manage,
)


def scope_file_organization_queryset(queryset, user):
    """先按根组织或显式项目关系收窄文件范围。

    文件尚未直接关联 Team，因此以所属项目关联的 Team 作为主要组织边界。
    项目负责人和有效项目成员仍可访问被显式邀请参与的跨组织项目。未建立
    Team 的旧部署继续沿用原范围；只有一个根组织时，也兼容尚未补录 Team
    关联的历史项目和无项目文件。多根组织部署不会展示归属不明确的文件。
    """
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return queryset.none()
    if getattr(user, 'global_role', '') == 'sys_admin':
        return queryset

    from apps.common.team_models import Team

    active_root_ids = list(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)[:2]
    )
    if not active_root_ids:
        return queryset

    direct_project_access = (
        Q(project__leader=user)
        | Q(
            project__members__user=user,
            project__members__status='active',
        )
    )
    user_root_ids = active_user_root_team_ids(user)
    if not user_root_ids:
        return queryset.filter(direct_project_access).distinct()

    same_root_project = (
        Q(project__teams__id__in=user_root_ids)
        | Q(project__teams__parent_id__in=user_root_ids)
    )
    legacy_single_root = Q(pk__in=[])
    if len(active_root_ids) == 1 and active_root_ids[0] in user_root_ids:
        legacy_single_root = Q(project__teams__isnull=True)

    return queryset.filter(
        direct_project_access | same_root_project | legacy_single_root
    ).distinct()


def user_can_manage_file_project(user, project):
    """校验文件写操作的项目边界；系统管理员保留平台级管理能力。"""
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return False
    if getattr(user, 'global_role', '') == 'sys_admin':
        return True

    direct_project_access = bool(
        project
        and (
            project.leader_id == user.id
            or has_active_project_membership(user, project)
        )
    )
    if not (
        direct_project_access
        or has_organization_project_access(user, project)
    ):
        return False
    if getattr(user, 'global_role', '') == 'teacher':
        return True
    return bool(project and project_can_manage(user, project))


def scope_file_queryset(queryset, user, *, include_sensitive=False):
    """Apply the same visibility rules used by file list and search APIs."""
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return queryset.none()
    visible = scope_file_organization_queryset(queryset, user)
    global_role = getattr(user, 'global_role', '')

    if global_role in ['sys_admin', 'teacher']:
        pass
    elif is_external_collaborator(user):
        visible = visible.filter(
            project__members__user=user,
            project__members__status='active',
        )
    else:
        visible = visible.filter(
            Q(level='public')
            | Q(
                level='internal',
                project__isnull=True,
            )
            | Q(
                level='internal',
                project__members__user=user,
                project__members__status='active',
            )
            | Q(level='internal', project__leader=user)
        )

    if not include_sensitive:
        visible = visible.exclude(level='sensitive')
    return visible.distinct()


def user_can_access_file(user, obj, *, allow_sensitive=False):
    """不依赖 HTTP 方法的文件读取权限判断，供下载与分享创建共用。"""
    if not user or not user.is_authenticated:
        return False
    if not getattr(user, 'is_active', False) or is_exited_member(user):
        return False
    if not scope_file_organization_queryset(
        type(obj).all_objects.filter(pk=obj.pk),
        user,
    ).exists():
        return False
    if obj.level == 'sensitive':
        return bool(
            allow_sensitive
            and user.global_role in ['sys_admin', 'teacher', 'sens_approver']
        )
    if user.global_role in ['sys_admin', 'teacher']:
        return True
    if is_external_collaborator(user):
        return bool(
            obj.project_id
            and has_active_project_membership(user, obj.project_id)
        )
    if obj.level == 'public':
        return True
    if obj.level == 'internal':
        if obj.project is None:
            return True
        if obj.project.leader_id == user.id:
            return True
        from apps.projects.models import ProjectMember
        return ProjectMember.objects.filter(
            project=obj.project,
            user=user,
            status=ProjectMember.Status.ACTIVE,
        ).exists()
    return False


class FileDownloadPermission(BasePermission):
    """
    文件下载权限校验
    根据文件的 level 字段进行不同级别的权限校验
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # 读取操作需要根据文件级别校验
        if request.method in SAFE_METHODS:
            # 敏感文件即使是管理员也必须经过显式审计端点。
            return user_can_access_file(request.user, obj, allow_sensitive=False)

        # 写操作需要项目负责人/老师/管理员权限
        return user_can_manage_file_project(request.user, obj.project)


class FileUploadPermission(BasePermission):
    """文件上传权限：项目负责人/老师/管理员"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # list 和 retrieve 对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        if request.user.global_role == 'sys_admin':
            return True
        # 上传版本、恢复版本等详情操作继续执行对象级校验。
        if getattr(view, 'detail', False):
            return True
        project_id = (
            request.data.get('project')
            if hasattr(request.data, 'get')
            else None
        )
        if project_id in (None, ''):
            return user_can_manage_file_project(request.user, None)
        from apps.projects.models import Project

        project = Project.objects.filter(pk=project_id).first()
        return bool(
            project
            and user_can_manage_file_project(request.user, project)
        )

    def has_object_permission(self, request, view, obj):
        if not user_can_manage_file_project(request.user, obj.project):
            return False
        if (
            request.method in ('PUT', 'PATCH')
            and hasattr(request.data, 'get')
            and 'project' in request.data
        ):
            project_id = request.data.get('project')
            if project_id in (None, ''):
                target_project = None
            else:
                from apps.projects.models import Project

                target_project = Project.objects.filter(pk=project_id).first()
                if target_project is None:
                    return False
            return user_can_manage_file_project(
                request.user,
                target_project,
            )
        return True
