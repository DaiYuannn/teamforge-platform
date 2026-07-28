"""
项目权限
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from common.project_access import project_can_manage, user_can_access_project
from common.permissions import user_has_custom_permission


def _can_create_for_requested_teams(request):
    user = request.user
    if (
        not user.is_active
        or getattr(user, 'membership_status', '') not in {'active', 'on_leave'}
    ):
        return False
    data = getattr(request, 'data', None)
    if not hasattr(data, 'get'):
        return False
    raw_team_ids = data.get('teams')
    if hasattr(data, 'getlist'):
        listed_team_ids = data.getlist('teams')
        if listed_team_ids:
            raw_team_ids = listed_team_ids
    if raw_team_ids in (None, '', []):
        return False
    if not isinstance(raw_team_ids, (list, tuple, set)):
        raw_team_ids = [raw_team_ids]
    try:
        team_ids = {int(team_id) for team_id in raw_team_ids}
    except (TypeError, ValueError):
        return False

    from apps.common.team_models import Team, TeamMember

    teams = list(Team.objects.filter(pk__in=team_ids, is_active=True))
    if len(teams) != len(team_ids):
        return False
    manager_roles = [
        TeamMember.Role.OWNER,
        TeamMember.Role.CO_LEAD,
        TeamMember.Role.ADMIN,
    ]
    for team in teams:
        direct_manager = (
            team.owner_id == user.id
            or TeamMember.objects.filter(
                team=team,
                user=user,
                role__in=manager_roles,
                status=TeamMember.Status.ACTIVE,
            ).exists()
        )
        parent = team.parent
        parent_manager = bool(
            parent
            and (
                parent.owner_id == user.id
                or TeamMember.objects.filter(
                    team=parent,
                    user=user,
                    role__in=manager_roles,
                    status=TeamMember.Status.ACTIVE,
                ).exists()
            )
        )
        if not (direct_manager or parent_manager):
            return False
    return True


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
        if getattr(view, 'action', '') != 'create':
            # 更新、删除和详情动作由对象级权限核对牵头/共同负责人。
            return True
        return (
            user_has_custom_permission(request.user, 'project.create')
            or _can_create_for_requested_teams(request)
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
        return project_can_manage(request.user, project)


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
        return project_can_manage(request.user, project)
