"""
贡献度模块权限
所有权限必须后端真实校验
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


def _is_project_member(user, project):
    """
    判断用户是否为项目成员（含项目负责人、老师、管理员）
    """
    if user.global_role in ['sys_admin', 'teacher']:
        return True
    if project is None:
        return False
    # 项目负责人
    if project.leader_id == user.id:
        return True
    # 项目成员
    from apps.projects.models import ProjectMember
    return ProjectMember.objects.filter(
        project=project, user=user, status=ProjectMember.Status.ACTIVE
    ).exists()


def _is_project_leader_or_admin(user, project):
    """
    判断用户是否为项目负责人/老师/管理员
    """
    if user.global_role in ['sys_admin', 'teacher']:
        return True
    if project is None:
        return False
    return project.leader_id == user.id


class IsProjectMemberForContribution(BasePermission):
    """
    贡献记录项目成员权限
    - 读取：所有认证用户可查看
    - 创建：项目成员可创建
    - 修改/删除：填写人或项目负责人/老师/管理员
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 系统管理员/老师可操作所有
        if request.user.global_role in ['sys_admin', 'teacher']:
            return True
        # 读取对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        project = getattr(obj, 'project', None)
        # 项目负责人可修改/删除
        if project is not None and project.leader_id == request.user.id:
            return True
        # 填写人可修改/删除
        if getattr(obj, 'filled_by_id', None) == request.user.id:
            return True
        # 贡献本人可修改/删除
        if getattr(obj, 'user_id', None) == request.user.id:
            return True
        return False


class IsProjectLeaderOrTeacherOrAdminForContribution(BasePermission):
    """
    项目负责人 / 老师 / 管理员权限（贡献模块）
    用于审核、生成排名等操作
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.global_role in ['sys_admin', 'teacher']:
            return True
        project = getattr(obj, 'project', None)
        if project is not None and project.leader_id == request.user.id:
            return True
        return False
