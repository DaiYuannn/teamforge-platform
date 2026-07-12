"""
RBAC 权限基类模块
基于角色的访问控制，所有权限必须真实校验
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class RolePermission(BasePermission):
    """
    RBAC 权限基类
    子类需设置 required_roles 属性来限定允许访问的角色
    """

    # 允许访问的角色列表，子类覆盖
    required_roles = []

    def has_permission(self, request, view):
        # 未登录直接拒绝
        if not request.user or not request.user.is_authenticated:
            return False

        # 如果未设置 required_roles，则只需认证即可
        if not self.required_roles:
            return True

        # 检查用户全局角色是否在允许列表中
        return request.user.global_role in self.required_roles

    def has_object_permission(self, request, view, obj):
        # 默认调用 has_permission
        return self.has_permission(request, view)


class IsSysAdmin(RolePermission):
    """系统管理员权限"""
    required_roles = ['sys_admin']


class IsSysAdminOrReadOnly(BasePermission):
    """系统管理员可写，其他认证用户只读"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.global_role == 'sys_admin'

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsTeacher(RolePermission):
    """老师权限"""
    required_roles = ['teacher']


class IsTeacherOrAdmin(RolePermission):
    """老师或管理员权限"""
    required_roles = ['teacher', 'sys_admin']


class IsSensitiveApprover(RolePermission):
    """敏感资料审批人权限"""
    required_roles = ['sens_approver', 'sys_admin']


class IsProjectLeaderOrTeacherOrAdmin(BasePermission):
    """
    项目负责人 / 老师 / 管理员权限
    对象级权限：检查当前用户是否为该项目的负责人，或全局角色为老师/管理员
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # list / retrieve 等安全方法对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        # 写操作需老师或管理员
        return request.user.global_role in ['teacher', 'sys_admin']

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 读取对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        # 系统管理员可以操作任何项目
        if request.user.global_role == 'sys_admin':
            return True
        # 老师可以操作任何项目
        if request.user.global_role == 'teacher':
            return True
        # 项目负责人可以操作自己的项目
        if hasattr(obj, 'leader'):
            return obj.leader_id == request.user.id
        # 如果是项目成员对象，检查其关联项目
        if hasattr(obj, 'project') and hasattr(obj.project, 'leader'):
            return obj.project.leader_id == request.user.id
        return False


class IsOwnerOrAdmin(BasePermission):
    """数据拥有者或管理员权限"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 管理员可访问
        if request.user.global_role == 'sys_admin':
            return True
        # 数据拥有者可访问
        if hasattr(obj, 'user'):
            return obj.user_id == request.user.id
        if hasattr(obj, 'creator'):
            return obj.creator_id == request.user.id
        if hasattr(obj, 'uploader'):
            return obj.uploader_id == request.user.id
        return False


class IsProjectMember(BasePermission):
    """项目成员权限（用于文件等资源访问）"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 管理员可访问
        if request.user.global_role == 'sys_admin':
            return True
        # 老师可访问
        if request.user.global_role == 'teacher':
            return True
        # 获取关联的项目
        project = getattr(obj, 'project', None)
        if project is None:
            return False
        # 项目负责人
        if project.leader_id == request.user.id:
            return True
        # 项目成员
        from apps.projects.models import ProjectMember
        return ProjectMember.objects.filter(
            project=project, user=request.user
        ).exists()
