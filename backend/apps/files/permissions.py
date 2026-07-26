"""
文件权限
三级权限校验:
- public: IsAuthenticated（所有认证用户可下载）
- internal: IsProjectMember（项目成员可下载）
- sensitive: 只能走敏感资料申请/审计下载端点
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from common.project_access import (
    has_active_project_membership,
    is_exited_member,
    is_external_collaborator,
)


def user_can_access_file(user, obj, *, allow_sensitive=False):
    """不依赖 HTTP 方法的文件读取权限判断，供下载与分享创建共用。"""
    if not user or not user.is_authenticated:
        return False
    if not getattr(user, 'is_active', False) or is_exited_member(user):
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
        return request.user.global_role in ['sys_admin', 'teacher'] or (
            obj.project and obj.project.leader_id == request.user.id
        )


class FileUploadPermission(BasePermission):
    """文件上传权限：项目负责人/老师/管理员"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # list 和 retrieve 对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        if request.user.global_role in ['teacher', 'sys_admin']:
            return True
        project_id = request.data.get('project') if hasattr(request.data, 'get') else None
        if project_id:
            from apps.projects.models import Project
            return Project.objects.filter(pk=project_id, leader=request.user).exists()
        # 上传版本、恢复版本等详情操作继续执行对象级校验。
        return bool(getattr(view, 'detail', False))

    def has_object_permission(self, request, view, obj):
        if request.user.global_role in ['teacher', 'sys_admin']:
            return True
        return bool(obj.project_id and obj.project.leader_id == request.user.id)
