"""
项目权限
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from common.project_access import user_can_access_project
from common.permissions import user_has_custom_permission


class IsProjectLeaderOrTeacherOrAdmin(BasePermission):
    """
    项目负责人 / 老师 / 管理员权限
    - 读取（list/retrieve）：所有认证用户
    - 写操作（create/update/destroy）：老师/管理员
    - 对象级操作：项目负责人/老师/管理员
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 安全方法（GET/HEAD/OPTIONS）对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        if request.user.global_role in ['teacher', 'sys_admin']:
            return True
        action = 'create' if getattr(view, 'action', '') == 'create' else 'manage'
        project_id = request.data.get('project') if hasattr(request.data, 'get') else None
        try:
            project_id = int(project_id) if project_id not in (None, '') else None
        except (TypeError, ValueError):
            project_id = None
        return user_has_custom_permission(
            request.user,
            f'project.{action}',
            project_id=project_id,
            allow_project_scoped=action == 'manage' and project_id is None,
        )

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 内部成员保持透明读取；外部协作者只能读取获授权项目。
        if request.method in SAFE_METHODS:
            project = obj if hasattr(obj, 'members') else getattr(obj, 'project', None)
            return user_can_access_project(request.user, project)
        # 系统管理员
        if request.user.global_role == 'sys_admin':
            return True
        # 老师
        if request.user.global_role == 'teacher':
            return True
        project = obj if hasattr(obj, 'leader_id') else getattr(obj, 'project', None)
        if user_has_custom_permission(
            request.user,
            'project.manage',
            project_id=getattr(project, 'pk', None),
        ):
            return True
        # 项目负责人
        if hasattr(obj, 'leader'):
            return obj.leader_id == request.user.id
        # 如果是成员对象，检查关联项目
        if hasattr(obj, 'project') and hasattr(obj.project, 'leader'):
            return obj.project.leader_id == request.user.id
        return False


class IsProjectLeader(BasePermission):
    """项目负责人权限（用于 stage/leader_update 等操作）"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 管理员和老师也可以操作
        if request.user.global_role in ['sys_admin', 'teacher']:
            return True
        return True  # 对象级权限会进一步校验

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 管理员和老师
        if request.user.global_role in ['sys_admin', 'teacher']:
            return True
        project = obj if hasattr(obj, 'leader_id') else getattr(obj, 'project', None)
        if user_has_custom_permission(
            request.user,
            'project.manage',
            project_id=getattr(project, 'pk', None),
        ):
            return True
        # 项目负责人
        if hasattr(obj, 'leader'):
            return obj.leader_id == request.user.id
        if hasattr(obj, 'project') and hasattr(obj.project, 'leader'):
            return obj.project.leader_id == request.user.id
        return False
