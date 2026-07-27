"""Shared project-scope checks for collaboration endpoints.

Internal active/on-leave members keep the team's transparent read access.
External collaborators are restricted to projects where they have an active
``ProjectMember`` row.  On-leave members retain internal reads but may only
write inside projects where their project membership remains active.
"""
from django.db.models import QuerySet


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
        return status == 'active' if write else status in INTERNAL_MEMBERSHIP_STATUSES

    active_membership = has_active_project_membership(user, project)
    if is_external_collaborator(user):
        return active_membership
    status = getattr(user, 'membership_status', '')
    if write and status == 'on_leave':
        return active_membership
    return status in INTERNAL_MEMBERSHIP_STATUSES


def scope_project_queryset(
    queryset: QuerySet,
    user,
    *,
    project_lookup='project',
    write=False,
):
    """Apply the same project boundary to list querysets used by child APIs."""
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return queryset.none()

    if getattr(user, 'global_role', '') in PROJECT_ADMIN_ROLES:
        return queryset
    if not is_external_collaborator(user):
        if getattr(user, 'membership_status', '') in INTERNAL_MEMBERSHIP_STATUSES:
            if not write or getattr(user, 'membership_status', '') == 'active':
                return queryset

    prefix = f'{project_lookup}__' if project_lookup else ''
    filters = {
        f'{prefix}members__user': user,
        f'{prefix}members__status': 'active',
    }
    return queryset.filter(**filters).distinct()
