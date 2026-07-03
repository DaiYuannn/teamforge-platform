"""
敏感资料模块权限
- IsSensitiveDataOwner: 只能查看自己的敏感资料（脱敏）
- IsSensitiveApproverOrAdmin: 审批权限
- HasValidAccessApproval: 有有效审批才能查看明文
所有权限必须后端真实校验
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSensitiveDataOwner(BasePermission):
    """
    敏感资料拥有者权限
    - 普通成员只能查看自己上传的敏感资料（脱敏）
    - 管理员/敏感审批人可查看所有
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 系统管理员/敏感审批人可访问所有
        if request.user.global_role in ['sys_admin', 'sens_approver']:
            return True
        # 老师可访问所有
        if request.user.global_role == 'teacher':
            return True
        # 数据拥有者（上传人）可访问
        if getattr(obj, 'uploader_id', None) == request.user.id:
            return True
        return False


class IsSensitiveApproverOrAdmin(BasePermission):
    """
    敏感资料审批人/管理员权限
    用于审批操作（approve/reject）
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.global_role in ['sens_approver', 'sys_admin', 'teacher']

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.global_role in ['sens_approver', 'sys_admin', 'teacher']


class IsSensitiveDataCreator(BasePermission):
    """
    敏感资料创建权限
    - 管理员/敏感审批人/老师可创建敏感资料
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.global_role in ['sens_approver', 'sys_admin', 'teacher']


class HasValidAccessApproval(BasePermission):
    """
    有效审批权限
    - 查看明文时校验：申请人本人 + 状态为已通过 + 未过期
    - 实际的申请ID校验在视图中完成，此处仅做基础认证
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True
