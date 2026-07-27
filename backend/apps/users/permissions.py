"""
用户管理权限
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from common.permissions import RolePermission, user_has_custom_permission


class IsUserManager(RolePermission):
    """用户管理权限：仅系统管理员可增删改查用户"""

    required_roles = ['sys_admin']

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # list / retrieve 允许老师和管理员查看用户列表
        if request.method in SAFE_METHODS:
            return (
                request.user.global_role in ['sys_admin', 'teacher']
                or user_has_custom_permission(request.user, 'member.view')
                or user_has_custom_permission(request.user, 'member.manage')
            )
        # 写操作仅限系统管理员
        return (
            request.user.global_role == 'sys_admin'
            or user_has_custom_permission(request.user, 'member.manage')
        )


class IsSelfOrAdmin(BasePermission):
    """本人或管理员可操作（用于个人信息修改）"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 管理员可操作
        if request.user.global_role == 'sys_admin':
            return True
        # 本人可操作
        return obj.id == request.user.id
