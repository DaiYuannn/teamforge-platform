"""Competition-specific authorization helpers shared by views and serializers."""

from common.project_access import project_can_manage
from apps.projects.models import ProjectMember

from .models import CompetitionParticipant


def can_manage_competition(user, competition):
    """Return whether the user may maintain a competition and its roster."""
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
        or getattr(user, 'membership_status', '') not in {'active', 'on_leave'}
    ):
        return False
    # 小团队版唯一 global_role=teacher 是全局操作老师；团队级
    # TeamMember.role=teacher 不会命中这里，仍保持只读。
    if getattr(user, 'global_role', '') in {'teacher', 'sys_admin'}:
        return True
    if project_can_manage(user, competition.project):
        return True
    project_membership = ProjectMember.objects.filter(
        project=competition.project,
        user=user,
    ).first()
    if (
        project_membership is not None
        and project_membership.status != ProjectMember.Status.ACTIVE
    ):
        return False
    return CompetitionParticipant.objects.filter(
        competition=competition,
        user=user,
        role=CompetitionParticipant.Role.LEADER,
    ).exclude(
        participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
    ).exists()
