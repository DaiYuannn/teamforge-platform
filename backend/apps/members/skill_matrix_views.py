"""Read-only team skill matrix and competition-entry recommendations.

``apps.members.SkillTag`` and ``apps.members.MemberSkill`` are the only skill
data source used here.  The similarly named legacy models under ``apps.users``
must not be mixed into this feature.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from django.db.models import Prefetch, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.team_models import Team, TeamMember
from apps.competitions.member_search import (
    member_matches_search,
    normalize_search_text,
)
from apps.competitions.models import (
    Competition,
    CompetitionParticipant,
)
from apps.users.models import User
from common.project_access import (
    active_user_root_team_ids,
    is_external_collaborator,
    scope_organization_users,
    user_can_access_project,
)
from common.response import error_response, success_response

from .models import MemberSkill, SkillTag


CURRENT_TEAM_STATUSES = (
    TeamMember.Status.ACTIVE,
    TeamMember.Status.ON_LEAVE,
)
VISIBLE_COMPETITION_STATUSES = (
    CompetitionParticipant.ParticipationStatus.PLANNED,
    CompetitionParticipant.ParticipationStatus.CONFIRMED,
)
TEAM_ROLE_PRIORITY = {
    TeamMember.Role.TEACHER: 0,
    TeamMember.Role.OWNER: 1,
    TeamMember.Role.CO_LEAD: 2,
    TeamMember.Role.ADMIN: 3,
    TeamMember.Role.ADVISOR: 4,
    TeamMember.Role.MEMBER: 5,
    TeamMember.Role.EXTERNAL: 6,
}
PARTICIPANT_ROLE_PRIORITY = {
    CompetitionParticipant.Role.LEADER: 0,
    CompetitionParticipant.Role.MEMBER: 1,
    CompetitionParticipant.Role.ADVISOR: 2,
}
TOKEN_SPLIT_PATTERN = re.compile(r"[,，;\n]+")


def _normalized_param(request, *names: str) -> str:
    for name in names:
        value = normalize_search_text(request.query_params.get(name, ''))
        if value:
            return value
    return ''


def _integer_param(
    request,
    *names: str,
    minimum: int | None = None,
    maximum: int | None = None,
):
    raw_value = next(
        (
            request.query_params.get(name)
            for name in names
            if request.query_params.get(name) not in (None, '')
        ),
        None,
    )
    if raw_value is None:
        return None, None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, f'{names[0]} 必须为整数'
    if minimum is not None and value < minimum:
        return None, f'{names[0]} 不能小于 {minimum}'
    if maximum is not None and value > maximum:
        return None, f'{names[0]} 不能大于 {maximum}'
    return value, None


def _root_team_filter(user):
    """Limit serialized team memberships to roots visible to the viewer."""
    if getattr(user, 'global_role', '') in {
        User.GlobalRole.TEACHER,
        User.GlobalRole.SYS_ADMIN,
    }:
        return Q()
    root_ids = active_user_root_team_ids(user)
    if not root_ids:
        return Q(pk__in=[])
    return Q(team_id__in=root_ids) | Q(team__parent_id__in=root_ids)


def _member_queryset(viewer):
    skill_queryset = MemberSkill.objects.select_related('skill').order_by(
        'skill__name',
        'id',
    )
    membership_queryset = TeamMember.objects.filter(
        status__in=CURRENT_TEAM_STATUSES,
    ).filter(
        _root_team_filter(viewer),
    ).select_related(
        'team',
        'team__parent',
    ).order_by(
        'team__name',
        'id',
    )
    return User.objects.filter(
        is_active=True,
    ).exclude(
        membership_status=User.MembershipStatus.EXITED,
    ).prefetch_related(
        Prefetch(
            'skills',
            queryset=skill_queryset,
            to_attr='matrix_skills',
        ),
        Prefetch(
            'teammember_set',
            queryset=membership_queryset,
            to_attr='matrix_team_memberships',
        ),
    )


def _resolve_competition_scope(request, *, required: bool):
    event_id, event_error = _integer_param(
        request,
        'competition_event',
        'competition_event_id',
        'event',
        'event_id',
        minimum=1,
    )
    if event_error:
        return None, error_response(
            message=event_error,
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    entry_id, entry_error = _integer_param(
        request,
        'competition_entry',
        'competition_entry_id',
        'entry',
        'entry_id',
        minimum=1,
    )
    if entry_error:
        return None, error_response(
            message=entry_error,
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    if required and (event_id is None or entry_id is None):
        return None, error_response(
            message='必须同时选择比赛届次和参赛条目',
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    if (event_id is None) != (entry_id is None):
        return None, error_response(
            message='比赛届次和参赛条目必须同时提供',
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    if event_id is None:
        return None, None

    try:
        competition = Competition.objects.select_related(
            'event',
            'project',
        ).get(
            pk=entry_id,
            event_id=event_id,
        )
    except Competition.DoesNotExist:
        return None, error_response(
            message='参赛条目不存在或不属于所选比赛届次',
            code=1004,
            http_status=status.HTTP_404_NOT_FOUND,
        )

    if is_external_collaborator(request.user):
        participates = CompetitionParticipant.objects.filter(
            competition=competition,
            user=request.user,
            participation_status__in=VISIBLE_COMPETITION_STATUSES,
        ).exists()
        if not participates:
            return None, error_response(
                message='外部协作者只能查看自己参与的参赛条目',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
    elif not user_can_access_project(request.user, competition.project):
        return None, error_response(
            message='无权查看该参赛条目的技能信息',
            code=1003,
            http_status=status.HTTP_403_FORBIDDEN,
        )
    return competition, None


def _competition_participants(competition):
    return CompetitionParticipant.objects.filter(
        competition=competition,
        participation_status__in=VISIBLE_COMPETITION_STATUSES,
        user__is_active=True,
    ).exclude(
        user__membership_status=User.MembershipStatus.EXITED,
    ).select_related(
        'user',
    ).order_by(
        'id',
    )


def _competition_metadata(competition):
    if competition is None:
        return None
    event = competition.event
    return {
        'event_id': event.id,
        'event_name': event.name,
        'event_edition': event.edition,
        'entry_id': competition.id,
        'entry_name': competition.entry_name or competition.name,
        'project_id': competition.project_id,
        'project_name': competition.project.name,
    }


def _team_membership_payload(member):
    return [
        {
            'team_id': membership.team_id,
            'team_name': membership.team.name,
            'parent_id': membership.team.parent_id,
            'parent_name': (
                membership.team.parent.name
                if membership.team.parent
                else ''
            ),
            'role': membership.role,
            'role_display': membership.get_role_display(),
            'status': membership.status,
            'status_display': membership.get_status_display(),
        }
        for membership in getattr(member, 'matrix_team_memberships', [])
    ]


def _skill_payload(member):
    return [
        {
            'id': member_skill.id,
            'skill_id': member_skill.skill_id,
            'name': member_skill.skill.name,
            'proficiency': member_skill.proficiency,
        }
        for member_skill in getattr(member, 'matrix_skills', [])
    ]


def _member_payload(member, participant=None):
    payload = {
        'user_id': member.id,
        'name': member.name,
        'username': member.username,
        'avatar': member.avatar.url if member.avatar else '',
        'school': member.school,
        'major': member.major,
        'grade': member.grade,
        'global_role': member.global_role,
        'global_role_display': member.get_global_role_display(),
        'membership_status': member.membership_status,
        'membership_status_display': member.get_membership_status_display(),
        'team_memberships': _team_membership_payload(member),
        'skills': _skill_payload(member),
    }
    if participant is not None:
        payload['entry_participation'] = {
            'participant_id': participant.id,
            'role': participant.role,
            'role_display': participant.get_role_display(),
            'participation_status': participant.participation_status,
            'participation_status_display': (
                participant.get_participation_status_display()
            ),
            'responsibility': participant.responsibility,
        }
    else:
        payload['entry_participation'] = None
    return payload


def _member_importance(member, participant=None):
    memberships = getattr(member, 'matrix_team_memberships', [])
    role_rank = min(
        (
            TEAM_ROLE_PRIORITY.get(
                membership.role,
                len(TEAM_ROLE_PRIORITY) + 1,
            )
            for membership in memberships
        ),
        default=len(TEAM_ROLE_PRIORITY) + 1,
    )
    if member.global_role == User.GlobalRole.TEACHER:
        role_rank = -1
    participant_rank = (
        PARTICIPANT_ROLE_PRIORITY.get(participant.role, 9)
        if participant is not None
        else 9
    )
    return (
        role_rank,
        participant_rank,
        normalize_search_text(member.name),
        member.id,
    )


def _partial_value_matches(query: str, values: Iterable[str]) -> bool:
    if not query:
        return True
    return any(
        query in normalize_search_text(value)
        for value in values
        if value
    )


def _member_matches_matrix_filters(member, request) -> bool:
    query = _normalized_param(request, 'search', 'q', 'name')
    if query and not member_matches_search(
        query=query,
        values=[member.name, member.username],
        name=member.name,
    ):
        return False

    team_role = _normalized_param(request, 'team_role', 'role')
    if team_role and not _partial_value_matches(
        team_role,
        [
            value
            for membership in getattr(member, 'matrix_team_memberships', [])
            for value in (membership.role, membership.get_role_display())
        ],
    ):
        return False

    member_status = _normalized_param(
        request,
        'member_status',
        'membership_status',
        'status',
    )
    if member_status and not _partial_value_matches(
        member_status,
        [
            member.membership_status,
            member.get_membership_status_display(),
            *[
                value
                for membership in getattr(
                    member,
                    'matrix_team_memberships',
                    [],
                )
                for value in (
                    membership.status,
                    membership.get_status_display(),
                )
            ],
        ],
    ):
        return False

    team_id, team_error = _integer_param(
        request,
        'team',
        'team_id',
        minimum=1,
    )
    if team_error:
        return False
    if team_id is not None and not any(
        membership.team_id == team_id
        for membership in getattr(member, 'matrix_team_memberships', [])
    ):
        return False

    skill_fragment = _normalized_param(
        request,
        'skill',
        'skill_name',
    )
    skill_id, skill_id_error = _integer_param(
        request,
        'skill_id',
        minimum=1,
    )
    if skill_id_error:
        return False
    minimum_proficiency, minimum_error = _integer_param(
        request,
        'min_proficiency',
        minimum=1,
        maximum=5,
    )
    if minimum_error:
        return False

    if any((skill_fragment, skill_id is not None, minimum_proficiency is not None)):
        matched_skill = False
        for member_skill in getattr(member, 'matrix_skills', []):
            if (
                skill_fragment
                and skill_fragment
                not in normalize_search_text(member_skill.skill.name)
            ):
                continue
            if skill_id is not None and member_skill.skill_id != skill_id:
                continue
            if (
                minimum_proficiency is not None
                and member_skill.proficiency < minimum_proficiency
            ):
                continue
            matched_skill = True
            break
        if not matched_skill:
            return False
    return True


def _matrix_query_error(request):
    for names, minimum, maximum in (
        (('team', 'team_id'), 1, None),
        (('skill_id',), 1, None),
        (('min_proficiency',), 1, 5),
    ):
        _, query_error = _integer_param(
            request,
            *names,
            minimum=minimum,
            maximum=maximum,
        )
        if query_error:
            return error_response(
                message=query_error,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    return None


class TeamSkillMatrixView(APIView):
    """Return a read-only, filterable skill matrix for the visible team."""

    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'head', 'options']

    def get(self, request):
        query_error = _matrix_query_error(request)
        if query_error:
            return query_error

        competition, scope_error = _resolve_competition_scope(
            request,
            required=False,
        )
        if scope_error:
            return scope_error

        base_queryset = _member_queryset(request.user)
        participant_by_user = {}
        if competition is not None:
            participants = list(_competition_participants(competition))
            participant_by_user = {
                participant.user_id: participant
                for participant in participants
            }
            base_queryset = base_queryset.filter(
                id__in=participant_by_user,
            )
        elif is_external_collaborator(request.user):
            base_queryset = base_queryset.filter(pk=request.user.pk)
        else:
            base_queryset = scope_organization_users(
                base_queryset,
                request.user,
            )

        school = _normalized_param(request, 'school', 'school_search')
        major = _normalized_param(request, 'major', 'major_search')
        if school:
            base_queryset = base_queryset.filter(school__icontains=school)
        if major:
            base_queryset = base_queryset.filter(major__icontains=major)

        members = [
            member
            for member in base_queryset
            if _member_matches_matrix_filters(member, request)
        ]
        members.sort(
            key=lambda member: _member_importance(
                member,
                participant_by_user.get(member.id),
            ),
        )
        payload_members = [
            _member_payload(
                member,
                participant_by_user.get(member.id),
            )
            for member in members
        ]
        skill_columns = sorted(
            {
                (skill['skill_id'], skill['name'])
                for member in payload_members
                for skill in member['skills']
            },
            key=lambda item: normalize_search_text(item[1]),
        )
        return success_response({
            'scope': {
                'type': (
                    'competition_entry'
                    if competition is not None
                    else (
                        'self'
                        if is_external_collaborator(request.user)
                        else 'organization'
                    )
                ),
                'competition': _competition_metadata(competition),
            },
            'count': len(payload_members),
            'skill_columns': [
                {'id': skill_id, 'name': name}
                for skill_id, name in skill_columns
            ],
            'members': payload_members,
        })


def _query_tokens(request, *names: str):
    values = []
    for name in names:
        for raw_value in request.query_params.getlist(name):
            values.extend(TOKEN_SPLIT_PATTERN.split(str(raw_value)))
    return [
        value.strip()
        for value in values
        if value and value.strip()
    ]


def _resolve_required_skills(request):
    raw_ids = _query_tokens(
        request,
        'required_skill_ids',
        'required_skill_id',
    )
    raw_names = _query_tokens(
        request,
        'required_skills',
        'required_skill_names',
        'required_skill',
    )
    if not raw_ids and not raw_names:
        return None, error_response(
            message='请至少选择一项所需技能',
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    skill_ids = []
    for raw_id in raw_ids:
        try:
            skill_id = int(raw_id)
        except (TypeError, ValueError):
            return None, error_response(
                message=f'无效的技能 ID：{raw_id}',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if skill_id <= 0:
            return None, error_response(
                message=f'无效的技能 ID：{raw_id}',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if skill_id not in skill_ids:
            skill_ids.append(skill_id)

    skills_by_id = {
        skill.id: skill
        for skill in SkillTag.objects.filter(id__in=skill_ids)
    }
    missing_ids = [
        skill_id for skill_id in skill_ids if skill_id not in skills_by_id
    ]
    if missing_ids:
        return None, error_response(
            message=f'技能 ID 不存在：{", ".join(map(str, missing_ids))}',
            code=1004,
            http_status=status.HTTP_404_NOT_FOUND,
        )

    required = [
        {
            'skill_id': skill.id,
            'name': skill.name,
        }
        for skill_id in skill_ids
        for skill in [skills_by_id[skill_id]]
    ]
    normalized_existing_names = {
        normalize_search_text(item['name'])
        for item in required
    }
    for raw_name in raw_names:
        normalized_name = normalize_search_text(raw_name)
        if normalized_name in normalized_existing_names:
            continue
        skill = SkillTag.objects.filter(name__iexact=raw_name.strip()).first()
        if skill is None:
            return None, error_response(
                message=f'技能名称不存在：{raw_name.strip()}',
                code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        required.append({
            'skill_id': skill.id,
            'name': skill.name,
        })
        normalized_existing_names.add(normalize_search_text(skill.name))
    return required, None


def _recommendation_payload(member, participant, required, minimum):
    user_skills = {
        member_skill.skill_id: member_skill
        for member_skill in getattr(member, 'matrix_skills', [])
    }
    matched = []
    missing = []
    total_proficiency = 0
    for requirement in required:
        member_skill = user_skills.get(requirement['skill_id'])
        if member_skill and member_skill.proficiency >= minimum:
            matched.append({
                **requirement,
                'proficiency': member_skill.proficiency,
                'required_proficiency': minimum,
            })
            total_proficiency += min(max(member_skill.proficiency, 0), 5)
            continue
        missing.append({
            **requirement,
            'current_proficiency': (
                member_skill.proficiency
                if member_skill is not None
                else None
            ),
            'required_proficiency': minimum,
            'reason': (
                '熟练度低于要求'
                if member_skill is not None
                else '未登记该技能'
            ),
        })

    required_count = len(required)
    coverage_ratio = len(matched) / required_count
    proficiency_ratio = total_proficiency / (required_count * 5)
    score = round(coverage_ratio * 70 + proficiency_ratio * 30, 1)
    member_payload = _member_payload(member, participant)
    member_payload.update({
        'score': score,
        'matched_count': len(matched),
        'required_count': required_count,
        'coverage_ratio': round(coverage_ratio, 4),
        'matched_skills': matched,
        'missing_skills': missing,
        'explanations': [
            (
                f'匹配 {len(matched)}/{required_count} 项所需技能，'
                f'覆盖率 {round(coverage_ratio * 100)}%'
            ),
            (
                '匹配技能：'
                + '、'.join(
                    f"{item['name']}({item['proficiency']}/5)"
                    for item in matched
                )
                if matched
                else '匹配技能：暂无'
            ),
            (
                '缺失或未达标：'
                + '、'.join(item['name'] for item in missing)
                if missing
                else '缺失或未达标：无'
            ),
            (
                '排序口径：技能覆盖占 70%，已匹配技能熟练度占 30%'
            ),
        ],
        '_matched_proficiency': total_proficiency,
    })
    return member_payload


class CompetitionSkillRecommendationView(APIView):
    """Rank only active candidates from one exact competition entry."""

    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'head', 'options']

    def get(self, request):
        competition, scope_error = _resolve_competition_scope(
            request,
            required=True,
        )
        if scope_error:
            return scope_error

        required, requirement_error = _resolve_required_skills(request)
        if requirement_error:
            return requirement_error
        minimum, minimum_error = _integer_param(
            request,
            'min_proficiency',
            minimum=1,
            maximum=5,
        )
        if minimum_error:
            return error_response(
                message=minimum_error,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        minimum = minimum or 1

        participants = list(_competition_participants(competition))
        participant_by_user = {
            participant.user_id: participant
            for participant in participants
        }
        members = list(
            _member_queryset(request.user).filter(
                id__in=participant_by_user,
            )
        )
        recommendations = [
            _recommendation_payload(
                member,
                participant_by_user[member.id],
                required,
                minimum,
            )
            for member in members
        ]
        recommendations.sort(
            key=lambda item: (
                -item['score'],
                -item['matched_count'],
                -item['_matched_proficiency'],
                PARTICIPANT_ROLE_PRIORITY.get(
                    item['entry_participation']['role'],
                    9,
                ),
                normalize_search_text(item['name']),
                item['user_id'],
            ),
        )
        for rank, recommendation in enumerate(recommendations, start=1):
            recommendation.pop('_matched_proficiency', None)
            recommendation['rank'] = rank

        return success_response({
            'competition': _competition_metadata(competition),
            'minimum_proficiency': minimum,
            'required_skills': [
                {
                    **requirement,
                    'required_proficiency': minimum,
                }
                for requirement in required
            ],
            'candidate_count': len(recommendations),
            'ranking_formula': (
                '技能覆盖率 × 70% + 已匹配技能熟练度比例 × 30%'
            ),
            'recommendations': recommendations,
        })
