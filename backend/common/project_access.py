"""Shared project-scope checks for collaboration endpoints.

Internal active/on-leave members keep the team's transparent read access.
External collaborators are restricted to projects where they have an active
``ProjectMember`` row.  On-leave members retain internal reads but may only
write inside projects where their project membership remains active.
"""
from django.db.models import Q, QuerySet


INTERNAL_MEMBERSHIP_STATUSES = {'active', 'on_leave'}
PROJECT_ADMIN_ROLES = {'teacher', 'sys_admin'}


def is_external_collaborator(user):
    return getattr(user, 'membership_status', '') == 'external'


def is_exited_member(user):
    return getattr(user, 'membership_status', '') == 'exited'


def has_active_project_membership(user, project):
    if not user or not user.is_authenticated or project is None:
        return False
    from apps.projects.models import ProjectMember

    project_id = getattr(project, 'pk', project)
    return ProjectMember.objects.filter(
        project_id=project_id,
        user=user,
        status=ProjectMember.Status.ACTIVE,
    ).exists()


def has_active_project_leadership(user, project):
    """Return whether a user is an active project co-lead."""
    if not user or not user.is_authenticated or project is None:
        return False
    from apps.projects.models import ProjectMember

    project_id = getattr(project, 'pk', project)
    return ProjectMember.objects.filter(
        project_id=project_id,
        user=user,
        role_in_project=ProjectMember.RoleInProject.LEADER,
        status=ProjectMember.Status.ACTIVE,
    ).exists()


def has_active_linked_team_membership(user, project):
    """Return whether a user belongs to one of the project's linked teams."""
    if not user or not user.is_authenticated or project is None:
        return False
    from apps.common.team_models import TeamMember

    project_id = getattr(project, 'pk', project)
    return TeamMember.objects.filter(
        team__projects__id=project_id,
        user=user,
        status=TeamMember.Status.ACTIVE,
    ).exists()


def active_user_root_team_ids(user):
    """返回用户有效团队关系所属的根团队，作为组织级隔离边界。"""
    if not user or not user.is_authenticated:
        return set()
    from apps.common.team_models import Team, TeamMember

    memberships = Team.objects.filter(
        Q(
            teammember__user=user,
            teammember__status__in=[
                TeamMember.Status.ACTIVE,
                TeamMember.Status.ON_LEAVE,
            ],
        )
        | Q(owner=user)
    ).values_list('id', 'parent_id').distinct()
    root_ids = {
        parent_id or team_id
        for team_id, parent_id in memberships
    }
    return root_ids


def project_root_team_ids(project):
    """从项目关联团队推导所属根组织。"""
    if project is None:
        return set()
    return {
        parent_id or team_id
        for team_id, parent_id in project.teams.values_list('id', 'parent_id')
    }


def user_can_join_project(user, project, *, role='participant'):
    """校验拟加入成员是否属于项目组织；外部协作者只能显式以 external 加入。

    完全没有 Team 数据的旧部署继续沿用原有项目成员语义。建立 Team 后，
    普通成员必须与项目共享根团队，避免通过成员管理把另一租户的账号拉入项目。
    """
    if (
        not user
        or not project
        or not getattr(user, 'is_active', False)
    ):
        return False

    membership_status = getattr(user, 'membership_status', '')
    if membership_status == 'external':
        return role == 'external'
    if membership_status not in INTERNAL_MEMBERSHIP_STATUSES:
        return False
    if role == 'leader' and membership_status != 'active':
        return False

    user_root_ids = active_user_root_team_ids(user)
    project_root_ids = project_root_team_ids(project)
    if project_root_ids:
        return bool(user_root_ids & project_root_ids)

    from apps.common.team_models import Team

    active_roots = list(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)[:2]
    )
    if not active_roots:
        return True

    # 未关联团队的旧项目在单根部署中仍可继续使用；多根部署则以原牵头
    # 负责人的组织作为唯一可信锚点，不能把其他组织成员拉入。
    leader_root_ids = active_user_root_team_ids(project.leader)
    if len(active_roots) == 1:
        return active_roots[0] in user_root_ids
    return bool(leader_root_ids and user_root_ids & leader_root_ids)


def scope_organization_users(queryset: QuerySet, user):
    """按当前用户所属根团队过滤成员目录；无 Team 的旧部署保留兼容。"""
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return queryset.none()
    if getattr(user, 'global_role', '') in PROJECT_ADMIN_ROLES:
        return queryset

    from apps.common.team_models import Team, TeamMember

    root_ids = active_user_root_team_ids(user)
    if not root_ids:
        if not Team.objects.filter(parent__isnull=True, is_active=True).exists():
            return queryset
        return queryset.none()
    visible_statuses = [TeamMember.Status.ACTIVE, TeamMember.Status.ON_LEAVE]
    return queryset.filter(
        Q(
            teammember__team_id__in=root_ids,
            teammember__status__in=visible_statuses,
        )
        | Q(
            teammember__team__parent_id__in=root_ids,
            teammember__status__in=visible_statuses,
        )
        | Q(owned_teams__id__in=root_ids)
        | Q(owned_teams__parent_id__in=root_ids)
    ).distinct()


def has_organization_project_access(user, project):
    """组织可见只在同一根团队内生效；未关联旧项目仅兼容单根组织部署。"""
    user_root_ids = active_user_root_team_ids(user)
    project_root_ids = project_root_team_ids(project)
    if project_root_ids:
        return bool(user_root_ids & project_root_ids)

    from apps.common.team_models import Team

    active_roots = list(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)[:2]
    )
    if not active_roots:
        # 升级前的单团队数据可能尚未建立 Team；仅在完全没有根团队时
        # 保留旧的内部可见语义。
        return True
    return len(active_roots) == 1 and active_roots[0] in user_root_ids


def project_can_manage(user, project):
    """Central project-management check, including active co-leads."""
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
        or project is None
    ):
        return False
    if getattr(user, 'global_role', '') in PROJECT_ADMIN_ROLES:
        return True
    if getattr(project, 'leader_id', None) == user.id:
        return True
    prefetched_members = getattr(
        project,
        '_prefetched_objects_cache',
        {},
    ).get('members')
    if prefetched_members is not None:
        from apps.projects.models import ProjectMember

        return any(
            member.user_id == user.id
            and member.role_in_project == ProjectMember.RoleInProject.LEADER
            and member.status == ProjectMember.Status.ACTIVE
            for member in prefetched_members
        )
    return has_active_project_leadership(user, project)


def user_can_access_project(user, project, *, write=False):
    """Return whether ``user`` may read or mutate project-scoped data."""
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return False
    if getattr(user, 'global_role', '') in PROJECT_ADMIN_ROLES:
        return True
    if project is None:
        status = getattr(user, 'membership_status', '')
        if is_external_collaborator(user):
            return False
        allowed_status = (
            status == 'active'
            if write
            else status in INTERNAL_MEMBERSHIP_STATUSES
        )
        # A null project represents legacy/global organization content.  It is
        # safe to keep the old internal-team behaviour when no Team hierarchy
        # exists, and in a single-root deployment where the user's tenant is
        # unambiguous.  Multiple roots must not share unscoped records.
        return allowed_status and has_organization_project_access(user, None)

    if project_can_manage(user, project):
        return True

    active_membership = has_active_project_membership(user, project)
    if is_external_collaborator(user):
        return active_membership

    status = getattr(user, 'membership_status', '')
    if active_membership:
        return True
    if write and status == 'on_leave':
        return False

    visibility = getattr(project, 'visibility', 'organization')
    if visibility == 'project':
        return False
    if visibility == 'teams':
        return has_active_linked_team_membership(user, project)
    if visibility == 'organization':
        allowed_status = (
            status == 'active'
            if write
            else status in INTERNAL_MEMBERSHIP_STATUSES
        )
        return allowed_status and has_organization_project_access(user, project)
    return False


def scope_project_queryset(
    queryset: QuerySet,
    user,
    *,
    project_lookup='project',
    write=False,
    include_unscoped=False,
):
    """Apply the same project boundary to list querysets used by child APIs.

    ``include_unscoped`` is for models whose nullable project explicitly means
    organization-global content (for example ``KnowledgeArticle``).  Such rows
    retain compatibility in deployments with no Team records, remain visible
    to the sole root organization, and are hidden from ordinary users when
    multiple root organizations exist.
    """
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return queryset.none()

    if getattr(user, 'global_role', '') in PROJECT_ADMIN_ROLES:
        return queryset

    prefix = f'{project_lookup}__' if project_lookup else ''
    active_project_member = Q(**{
        f'{prefix}members__user': user,
        f'{prefix}members__status': 'active',
    })
    primary_leader = Q(**{f'{prefix}leader': user})
    if is_external_collaborator(user):
        return queryset.filter(primary_leader | active_project_member).distinct()

    membership_status = getattr(user, 'membership_status', '')
    if membership_status not in INTERNAL_MEMBERSHIP_STATUSES:
        return queryset.none()
    if write and membership_status == 'on_leave':
        return queryset.filter(primary_leader | active_project_member).distinct()

    linked_team_member = Q(**{
        f'{prefix}visibility': 'teams',
        f'{prefix}teams__teammember__user': user,
        f'{prefix}teams__teammember__status': 'active',
    })
    user_root_ids = active_user_root_team_ids(user)
    organization_visible = Q(pk__in=[])
    unscoped_visible = Q(pk__in=[])
    from apps.common.team_models import Team

    active_roots = list(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)[:2]
    )
    if (
        include_unscoped
        and project_lookup
        and has_organization_project_access(user, None)
    ):
        unscoped_visible = Q(**{f'{project_lookup}__isnull': True})
    if not active_roots:
        organization_visible = Q(**{
            f'{prefix}visibility': 'organization',
            f'{prefix}teams__isnull': True,
        })
    elif user_root_ids:
        organization_visible = (
            Q(**{
                f'{prefix}visibility': 'organization',
                f'{prefix}teams__id__in': user_root_ids,
            })
            | Q(**{
                f'{prefix}visibility': 'organization',
                f'{prefix}teams__parent_id__in': user_root_ids,
            })
        )
        if len(active_roots) == 1 and active_roots[0] in user_root_ids:
            organization_visible |= Q(**{
                f'{prefix}visibility': 'organization',
                f'{prefix}teams__isnull': True,
            })
    return queryset.filter(
        primary_leader
        | active_project_member
        | linked_team_member
        | organization_visible
        | unscoped_visible
    ).distinct()
