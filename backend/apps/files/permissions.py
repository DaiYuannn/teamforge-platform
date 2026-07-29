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


GLOBAL_FILE_MANAGER_ROLES = {'sys_admin', 'teacher'}


def user_can_manage_team_file_scope(user, team):
    """Only global teachers or explicit owner/co-lead/admin roles may write."""
    if not user or not user.is_authenticated or not user.is_active or team is None:
        return False
    if getattr(user, 'global_role', '') in GLOBAL_FILE_MANAGER_ROLES:
        return True
    from apps.common.team_models import TeamMember

    if team.owner_id == user.id:
        return True
    manager_roles = [
        TeamMember.Role.OWNER,
        TeamMember.Role.CO_LEAD,
        TeamMember.Role.ADMIN,
    ]
    if TeamMember.objects.filter(
        team=team,
        user=user,
        role__in=manager_roles,
        status=TeamMember.Status.ACTIVE,
    ).exists():
        return True
    parent = getattr(team, 'parent', None)
    if not parent:
        return False
    return bool(
        parent.owner_id == user.id
        or TeamMember.objects.filter(
            team=parent,
            user=user,
            role__in=manager_roles,
            status=TeamMember.Status.ACTIVE,
        ).exists()
    )


def user_can_access_team_file_scope(user, team):
    if user_can_manage_team_file_scope(user, team):
        return True
    if not user or not user.is_authenticated or team is None:
        return False
    from apps.common.team_models import TeamMember

    return TeamMember.objects.filter(
        team=team,
        user=user,
        status__in=[TeamMember.Status.ACTIVE, TeamMember.Status.ON_LEAVE],
    ).exists()


def user_can_manage_competition_file_scope(user, competition):
    if competition is None:
        return False
    if getattr(user, 'global_role', '') in GLOBAL_FILE_MANAGER_ROLES:
        return bool(user and user.is_authenticated and user.is_active)
    from apps.competitions.permissions import can_manage_competition

    return can_manage_competition(user, competition)


def user_can_access_competition_file_scope(user, competition):
    if user_can_manage_competition_file_scope(user, competition):
        return True
    if not user or not user.is_authenticated or competition is None:
        return False
    from apps.competitions.models import CompetitionParticipant

    return CompetitionParticipant.objects.filter(
        competition=competition,
        user=user,
    ).exclude(
        participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
    ).exists()


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
    if getattr(user, 'global_role', '') in GLOBAL_FILE_MANAGER_ROLES:
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
    from apps.competitions.models import CompetitionParticipant

    direct_competition_access = Q(
        competition_entry_id__in=CompetitionParticipant.objects.filter(
            user=user,
        ).exclude(
            participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
        ).values('competition_id')
    )
    user_root_ids = active_user_root_team_ids(user)
    if not user_root_ids:
        return queryset.filter(
            direct_project_access | direct_competition_access
        ).distinct()

    same_root_project = (
        Q(project__teams__id__in=user_root_ids)
        | Q(project__teams__parent_id__in=user_root_ids)
    )
    same_root_team = (
        Q(team_id__in=user_root_ids)
        | Q(team__parent_id__in=user_root_ids)
    )
    legacy_single_root = Q(pk__in=[])
    if len(active_root_ids) == 1 and active_root_ids[0] in user_root_ids:
        legacy_single_root = Q(project__teams__isnull=True)

    return queryset.filter(
        direct_project_access
        | direct_competition_access
        | same_root_project
        | same_root_team
        | legacy_single_root
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
    if getattr(user, 'global_role', '') in GLOBAL_FILE_MANAGER_ROLES:
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


def user_can_manage_file_scope(user, *, project=None, team=None, competition_entry=None):
    if team is not None and competition_entry is not None:
        return False
    if competition_entry is not None:
        if project and competition_entry.project_id != getattr(project, 'id', project):
            return False
        return user_can_manage_competition_file_scope(user, competition_entry)
    if team is not None:
        return user_can_manage_team_file_scope(user, team)
    return user_can_manage_file_project(user, project)


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

    if global_role in GLOBAL_FILE_MANAGER_ROLES:
        pass
    else:
        from apps.common.team_models import TeamMember
        from apps.competitions.models import CompetitionParticipant
        from apps.projects.models import ProjectMember

        team_manager_roles = [
            TeamMember.Role.OWNER,
            TeamMember.Role.CO_LEAD,
            TeamMember.Role.ADMIN,
        ]
        team_scope = (
            Q(
                level='internal',
                team__isnull=False,
                team__teammember__user=user,
                team__teammember__status__in=[
                    TeamMember.Status.ACTIVE,
                    TeamMember.Status.ON_LEAVE,
                ],
            )
            | Q(level='internal', team__owner=user)
            | Q(
                level='internal',
                team__parent__teammember__user=user,
                team__parent__teammember__role__in=team_manager_roles,
                team__parent__teammember__status=TeamMember.Status.ACTIVE,
            )
            | Q(level='internal', team__parent__owner=user)
        )
        active_competition_ids = CompetitionParticipant.objects.filter(
            user=user,
        ).exclude(
            participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
        ).values('competition_id')
        competition_scope = Q(
            level='internal',
            competition_entry_id__in=active_competition_ids,
        ) | Q(level='internal', competition_entry__project__leader=user) | Q(
            level='internal',
            competition_entry__project__members__user=user,
            competition_entry__project__members__status=ProjectMember.Status.ACTIVE,
            competition_entry__project__members__role_in_project=(
                ProjectMember.RoleInProject.LEADER
            ),
        )
        project_scope = (
            Q(level='internal', team__isnull=True, competition_entry__isnull=True)
            & (
                Q(project__isnull=True)
                | Q(project__leader=user)
                | Q(
                    project__members__user=user,
                    project__members__status=ProjectMember.Status.ACTIVE,
                )
            )
        )
        visible = visible.filter(
            Q(level='public')
            | team_scope
            | competition_scope
            | project_scope
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
    if obj.level == 'public':
        if is_external_collaborator(user):
            return bool(
                obj.project_id
                and has_active_project_membership(user, obj.project_id)
            )
        return True
    if obj.level == 'internal':
        if obj.competition_entry_id:
            return user_can_access_competition_file_scope(
                user,
                obj.competition_entry,
            )
        if obj.team_id:
            return user_can_access_team_file_scope(user, obj.team)
        if is_external_collaborator(user):
            return bool(
                obj.project_id
                and has_active_project_membership(user, obj.project_id)
            )
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
        return user_can_manage_file_scope(
            request.user,
            project=obj.project,
            team=obj.team,
            competition_entry=obj.competition_entry,
        )


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
        team_id = request.data.get('team') if hasattr(request.data, 'get') else None
        competition_id = (
            request.data.get('competition_entry')
            if hasattr(request.data, 'get')
            else None
        )
        if team_id and competition_id:
            return False
        from apps.projects.models import Project
        from apps.common.team_models import Team
        from apps.competitions.models import Competition

        project = Project.objects.filter(pk=project_id).first()
        team = Team.objects.filter(pk=team_id).first() if team_id else None
        competition = (
            Competition.objects.filter(pk=competition_id).first()
            if competition_id
            else None
        )
        if project_id not in (None, '') and project is None:
            return False
        if team_id and team is None:
            return False
        if competition_id and competition is None:
            return False
        return user_can_manage_file_scope(
            request.user,
            project=project,
            team=team,
            competition_entry=competition,
        )

    def has_object_permission(self, request, view, obj):
        if not user_can_manage_file_scope(
            request.user,
            project=obj.project,
            team=getattr(obj, 'team', None),
            competition_entry=getattr(obj, 'competition_entry', None),
        ):
            return False
        if request.method in ('PUT', 'PATCH') and hasattr(request.data, 'get'):
            from apps.projects.models import Project
            from apps.common.team_models import Team
            from apps.competitions.models import Competition

            def resolve(field, model, current):
                if field not in request.data:
                    return current, True
                value = request.data.get(field)
                if value in (None, ''):
                    return None, True
                resolved = model.objects.filter(pk=value).first()
                return resolved, resolved is not None

            target_project, project_valid = resolve('project', Project, obj.project)
            target_team, team_valid = resolve(
                'team', Team, getattr(obj, 'team', None),
            )
            target_competition, competition_valid = resolve(
                'competition_entry',
                Competition,
                getattr(obj, 'competition_entry', None),
            )
            if not (project_valid and team_valid and competition_valid):
                return False
            return user_can_manage_file_scope(
                request.user,
                project=target_project,
                team=target_team,
                competition_entry=target_competition,
            )
        return True
