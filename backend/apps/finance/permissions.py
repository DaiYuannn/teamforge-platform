"""Finance-specific authorization and conflict-of-interest checks."""

from common.permissions import user_has_custom_permission
from common.project_access import project_can_manage, user_can_access_project


OPERATING_TEACHER_ROLES = {'teacher', 'sys_admin'}


def can_read_finance(user, project):
    return user_can_access_project(user, project)


def can_manage_finance(user, project):
    """Business managers may edit ledgers and review claims.

    TeamMember.role=teacher is intentionally not considered here.  Only the
    single global operating teacher (global_role=teacher), sysadmin, project
    leaders/co-leaders, or an explicit project-scoped finance role may write.
    """
    if not user or not user.is_authenticated or project is None:
        return False
    if getattr(user, 'global_role', '') in OPERATING_TEACHER_ROLES:
        return True
    return bool(
        project_can_manage(user, project)
        or user_has_custom_permission(
            user,
            'finance.manage',
            project_id=project.id,
        )
    )


def can_pay_finance(user, project):
    if not user or not user.is_authenticated or project is None:
        return False
    if getattr(user, 'global_role', '') in OPERATING_TEACHER_ROLES:
        return True
    return user_has_custom_permission(
        user,
        'finance.manage',
        project_id=project.id,
    )


def finance_review_conflicts(user, expense):
    """Applicants, out-of-pocket spenders and payees may not self-review."""
    return bool(
        user
        and user.id
        and user.id in {
            expense.applied_by_id,
            expense.spender_id,
            expense.payee_id,
        }
    )


def can_review_expense(user, expense):
    return (
        can_manage_finance(user, expense.project)
        and not finance_review_conflicts(user, expense)
    )
