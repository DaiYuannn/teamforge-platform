"""Competition-specific authorization helpers shared by views and serializers."""

from common.project_access import (
    has_active_project_membership,
    project_can_manage,
)

from .models import CompetitionParticipant


def can_manage_competition(user, competition):
    """Return whether the user may maintain a competition and its roster."""
    if project_can_manage(user, competition.project):
        return True
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
        or getattr(user, 'membership_status', '') not in {'active', 'on_leave'}
        or not has_active_project_membership(user, competition.project)
    ):
        return False
    return CompetitionParticipant.objects.filter(
        competition=competition,
        user=user,
        role=CompetitionParticipant.Role.LEADER,
    ).exclude(
        participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
    ).exists()
