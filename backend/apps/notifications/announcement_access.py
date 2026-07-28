"""Announcement audience and tenant-scope helpers.

Announcements are anchored to one root ``organization``.  Published content
is then narrowed to the selected squads or projects.  Drafts are never made
visible merely because somebody belongs to the same root organization.
"""
from django.db.models import Q, QuerySet

from common.permissions import user_has_custom_permission
from common.project_access import active_user_root_team_ids
from apps.common.team_models import Team, TeamMember
from apps.projects.models import ProjectMember

from .models import Announcement


VISIBLE_TEAM_STATUSES = [
    TeamMember.Status.ACTIVE,
    TeamMember.Status.ON_LEAVE,
]
ANNOUNCEMENT_MANAGER_ROLES = [
    TeamMember.Role.OWNER,
    TeamMember.Role.CO_LEAD,
    TeamMember.Role.ADMIN,
]


def can_manage_announcements(user):
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
        or getattr(user, 'membership_status', '') not in {'active', 'on_leave'}
    ):
        return False
    if getattr(user, 'global_role', '') in {'teacher', 'sys_admin'}:
        return True
    if user_has_custom_permission(user, 'announcement.manage'):
        return True
    return TeamMember.objects.filter(
        user=user,
        role__in=ANNOUNCEMENT_MANAGER_ROLES,
        status=TeamMember.Status.ACTIVE,
    ).exists()


def announcement_management_scope(user):
    """Return root/team ids where ``user`` may administer announcements."""
    empty = {
        'can_manage': False,
        'root_ids': set(),
        'team_ids': set(),
        'project_ids': set(),
        'legacy_global': False,
    }
    if not can_manage_announcements(user):
        return empty

    active_roots = set(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)
    )
    if not active_roots:
        return {**empty, 'can_manage': True, 'legacy_global': True}

    user_root_ids = active_user_root_team_ids(user) & active_roots
    broad_manager = (
        getattr(user, 'global_role', '') in {'teacher', 'sys_admin'}
        or user_has_custom_permission(user, 'announcement.manage')
    )
    managed_direct_ids = set(
        Team.objects.filter(
            Q(owner=user)
            | Q(
                teammember__user=user,
                teammember__role__in=ANNOUNCEMENT_MANAGER_ROLES,
                teammember__status=TeamMember.Status.ACTIVE,
            ),
            is_active=True,
        ).values_list('id', flat=True)
    )
    managed_root_ids = {
        team_id
        for team_id, parent_id in Team.objects.filter(
            id__in=managed_direct_ids,
        ).values_list('id', 'parent_id')
        if parent_id is None
    }
    if broad_manager:
        # A global role grants broad capabilities inside the user's own tenant,
        # not access to unrelated root organizations.
        managed_root_ids.update(user_root_ids)

    managed_team_ids = set(managed_direct_ids)
    managed_team_ids.update(managed_root_ids)
    managed_team_ids.update(
        Team.objects.filter(
            parent_id__in=managed_root_ids,
            is_active=True,
        ).values_list('id', flat=True)
    )
    project_ids = set(
        ProjectMember.objects.filter(
            user=user,
            role_in_project=ProjectMember.RoleInProject.LEADER,
            status=ProjectMember.Status.ACTIVE,
        ).values_list('project_id', flat=True)
    )
    from apps.projects.models import Project

    project_ids.update(
        Project.objects.filter(
            Q(leader=user) | Q(teams__id__in=managed_team_ids),
        ).values_list('id', flat=True)
    )
    return {
        'can_manage': True,
        'root_ids': managed_root_ids,
        'team_ids': managed_team_ids,
        'project_ids': project_ids,
        'legacy_global': False,
    }


def _legacy_organization_visibility_q(user):
    """Compatibility for announcements created before an organization anchor."""
    active_root_ids = list(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)
    )
    unanchored = Q(organization__isnull=True)
    if not active_root_ids:
        return unanchored

    user_root_ids = active_user_root_team_ids(user)
    if len(active_root_ids) == 1:
        return unanchored if active_root_ids[0] in user_root_ids else Q(pk__in=[])
    if not user_root_ids:
        return Q(pk__in=[])

    # In a multi-root upgraded deployment, only infer an old row from its
    # author's active tenant. Unattributable rows remain hidden.
    return unanchored & (
        Q(
            author__teammember__team_id__in=user_root_ids,
            author__teammember__status__in=VISIBLE_TEAM_STATUSES,
        )
        | Q(
            author__teammember__team__parent_id__in=user_root_ids,
            author__teammember__status__in=VISIBLE_TEAM_STATUSES,
        )
        | Q(author__owned_teams__id__in=user_root_ids)
        | Q(author__owned_teams__parent_id__in=user_root_ids)
    )


def published_announcement_visibility_q(user):
    if not user or not user.is_authenticated or not user.is_active:
        return Q(pk__in=[])

    # Internet-public announcements remain visible to every authenticated
    # account, including external project collaborators.
    visibility = Q(audience=Announcement.Audience.PUBLIC) | Q(is_public=True)
    if getattr(user, 'membership_status', '') not in {'active', 'on_leave'}:
        return visibility

    root_ids = active_user_root_team_ids(user)
    organization_visibility = Q(
        audience=Announcement.Audience.ORGANIZATION,
        organization_id__in=root_ids,
    )
    organization_visibility |= (
        Q(audience=Announcement.Audience.ORGANIZATION)
        & _legacy_organization_visibility_q(user)
    )

    team_visibility = Q(
        audience=Announcement.Audience.TEAMS,
        target_teams__teammember__user=user,
        target_teams__teammember__status__in=VISIBLE_TEAM_STATUSES,
    ) | Q(
        audience=Announcement.Audience.TEAMS,
        target_teams__owner=user,
    )
    project_visibility = (
        Q(
            audience=Announcement.Audience.PROJECTS,
            target_projects__leader=user,
        )
        | Q(
            audience=Announcement.Audience.PROJECTS,
            target_projects__members__user=user,
            target_projects__members__status__in=[
                ProjectMember.Status.ACTIVE,
                ProjectMember.Status.ON_LEAVE,
            ],
        )
    )
    return visibility | organization_visibility | team_visibility | project_visibility


def manageable_announcement_q(user):
    scope = announcement_management_scope(user)
    if scope['legacy_global']:
        return Q(pk__isnull=False)
    manageable = Q(author=user)
    if scope['root_ids']:
        manageable |= Q(
            audience__in=[
                Announcement.Audience.ORGANIZATION,
                Announcement.Audience.PUBLIC,
            ],
            organization_id__in=scope['root_ids'],
        )
    if scope['team_ids']:
        manageable |= Q(
            audience=Announcement.Audience.TEAMS,
            target_teams__id__in=scope['team_ids'],
        )
    if scope['project_ids']:
        manageable |= Q(
            audience=Announcement.Audience.PROJECTS,
            target_projects__id__in=scope['project_ids'],
        )
    return manageable


def scope_announcements_for_user(
    queryset: QuerySet,
    user,
    *,
    include_manageable=False,
):
    published = Q(status=Announcement.Status.PUBLISHED) & (
        published_announcement_visibility_q(user)
    )
    if include_manageable and can_manage_announcements(user):
        return queryset.filter(published | manageable_announcement_q(user)).distinct()
    return queryset.filter(published).distinct()


def can_manage_announcement(user, announcement):
    if not can_manage_announcements(user):
        return False
    return Announcement.objects.filter(
        pk=announcement.pk,
    ).filter(manageable_announcement_q(user)).exists()


def announcement_is_manageable_from_scope(announcement, user, scope):
    """Evaluate row management from one precomputed scope.

    List/detail querysets prefetch both target relations, so serializers can
    expose ``can_manage`` without issuing one permission query per row.
    """
    if not scope['can_manage']:
        return False
    if scope['legacy_global']:
        return True
    if announcement.author_id == user.id:
        return True
    if (
        announcement.audience in {
            Announcement.Audience.ORGANIZATION,
            Announcement.Audience.PUBLIC,
        }
        and announcement.organization_id in scope['root_ids']
    ):
        return True
    if announcement.audience == Announcement.Audience.TEAMS:
        return any(
            team.id in scope['team_ids']
            for team in announcement.target_teams.all()
        )
    if announcement.audience == Announcement.Audience.PROJECTS:
        return any(
            project.id in scope['project_ids']
            for project in announcement.target_projects.all()
        )
    return False
