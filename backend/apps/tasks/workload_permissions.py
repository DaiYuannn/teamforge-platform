"""Exact competition-entry permission helpers."""

from apps.competitions.models import CompetitionParticipant
from apps.competitions.permissions import can_manage_competition
from apps.users.models import User


ACTIVE_MEMBERSHIP_STATUSES = {
    User.MembershipStatus.ACTIVE,
    User.MembershipStatus.ON_LEAVE,
}


def is_active_competition_participant(user, competition):
    """Return whether ``user`` currently belongs to this exact entry."""
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
        or user.membership_status not in ACTIVE_MEMBERSHIP_STATUSES
    ):
        return False
    return CompetitionParticipant.objects.filter(
        competition=competition,
        user=user,
    ).exclude(
        participation_status=(
            CompetitionParticipant.ParticipationStatus.WITHDRAWN
        ),
    ).exists()


def can_view_competition_entry(user, competition):
    """Exact participants may read; scoped competition managers may manage."""
    return (
        is_active_competition_participant(user, competition)
        or can_manage_competition(user, competition)
    )


def eligible_allocation_participants(competition):
    """Return the active leader/member roster required at publication."""
    return (
        CompetitionParticipant.objects
        .filter(
            competition=competition,
            role__in=[
                CompetitionParticipant.Role.LEADER,
                CompetitionParticipant.Role.MEMBER,
            ],
            user__is_active=True,
            user__membership_status__in=ACTIVE_MEMBERSHIP_STATUSES,
        )
        .exclude(
            participation_status=(
                CompetitionParticipant.ParticipationStatus.WITHDRAWN
            ),
        )
        .select_related('user')
        .order_by('role', 'joined_at', 'id')
    )
