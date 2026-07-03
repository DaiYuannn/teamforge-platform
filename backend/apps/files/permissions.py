"""
文件权限
三级权限校验:
- public: IsAuthenticated（所有认证用户可下载）
- internal: IsProjectMember（项目成员可下载）
- sensitive: 走审批流程（第三期实现，暂不允许下载明文）
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


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
            # 管理员可访问所有文件
            if request.user.global_role == 'sys_admin':
                return True
            # 老师可访问所有文件
            if request.user.global_role == 'teacher':
                return True

            # 根据文件级别校验
            if obj.level == 'public':
                # 公开文件：所有认证用户可访问
                return True
            elif obj.level == 'internal':
                # 内部文件：项目成员可访问
                if obj.project is None:
                    return True  # 无关联项目的内部文件，认证用户可访问
                # 检查是否为项目成员
                if obj.project.leader_id == request.user.id:
                    return True
                from apps.projects.models import ProjectMember
                return ProjectMember.objects.filter(
                    project=obj.project, user=request.user
                ).exists()
            elif obj.level == 'sensitive':
                # 敏感文件：走审批流程（第三期实现）
                # 当前暂不开放明文查看，仅管理员和敏感审批人可访问
                return request.user.global_role in ['sys_admin', 'sens_approver']
            return False

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
        # 写操作需要老师或管理员
        return request.user.global_role in ['teacher', 'sys_admin']
