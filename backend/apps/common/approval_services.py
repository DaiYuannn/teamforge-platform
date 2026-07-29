from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers


FLOW_TYPES = {'leave', 'expense', 'sensitive', 'project', 'team_membership'}
TEAM_MEMBERSHIP_ACTIONS = {'join', 'transfer', 'role_change'}


def _as_string_set(value):
    if value in (None, ''):
        return set()
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return {str(item) for item in values if item not in (None, '')}


def approval_step(approval_request):
    """Return the current, backwards-compatible approval step."""
    steps = approval_request.flow.steps or []
    index = approval_request.current_step
    if 0 <= index < len(steps) and isinstance(steps[index], dict):
        return steps[index]
    return {}


def approval_reviewer_spec(approval_request):
    """Resolve reviewer IDs and roles declared on the current step."""
    step = approval_step(approval_request)
    reviewer_ids = set()
    reviewer_roles = set()
    for key in (
        'reviewer_id', 'reviewer_ids', 'approver_id', 'approver_ids',
        'user_id', 'user_ids',
    ):
        reviewer_ids.update(_as_string_set(step.get(key)))
    for key in (
        'reviewer_role', 'reviewer_roles', 'approver_role',
        'approver_roles', 'required_role', 'required_roles',
        'role', 'roles',
    ):
        reviewer_roles.update(_as_string_set(step.get(key)))

    reviewer = step.get('reviewer')
    if isinstance(reviewer, dict):
        reviewer_ids.update(_as_string_set(reviewer.get('id')))
        reviewer_ids.update(_as_string_set(reviewer.get('ids')))
        reviewer_roles.update(_as_string_set(reviewer.get('role')))
        reviewer_roles.update(_as_string_set(reviewer.get('roles')))
    elif reviewer not in (None, ''):
        reviewer_ids.update(_as_string_set(reviewer))
    return reviewer_ids, reviewer_roles


def _team_manager_user_ids(
    approval_request,
    *,
    include_operating_teacher=True,
):
    """Resolve active managers for the target team without including read-only teachers."""
    from .team_models import Team, TeamMember

    metadata = approval_request.metadata or {}
    team = Team.objects.select_related('parent').filter(
        pk=metadata.get('target_team_id'),
    ).first()
    if not team:
        return set()

    teams = [team]
    if team.parent_id:
        teams.append(team.parent)

    # A co-lead elevation must be approved by the current owner or an upstream
    # owner, not merely by another administrator/co-lead.
    requested_role = metadata.get('requested_role')
    if requested_role == TeamMember.Role.CO_LEAD:
        manager_roles = [TeamMember.Role.OWNER]
    else:
        manager_roles = [
            TeamMember.Role.OWNER,
            TeamMember.Role.CO_LEAD,
            TeamMember.Role.ADMIN,
        ]

    manager_ids = {candidate.owner_id for candidate in teams}
    manager_ids.update(
        TeamMember.objects.filter(
            team__in=teams,
            role__in=manager_roles,
            status=TeamMember.Status.ACTIVE,
        ).values_list('user_id', flat=True)
    )
    from apps.users.models import User

    # The single global operating teacher is the small-team fallback operator.
    # TeamMember.role=teacher is not included because it is read-only.
    if include_operating_teacher:
        manager_ids.update(
            User.objects.filter(
                global_role=User.GlobalRole.TEACHER,
                is_active=True,
            ).values_list('id', flat=True)
        )
    return {str(user_id) for user_id in manager_ids if user_id}


def approval_reviewer_details(approval_request):
    """Return effective reviewer information used by API and unified todo."""
    from apps.users.models import User

    reviewer_ids, reviewer_roles = approval_reviewer_spec(approval_request)
    effective_ids = set(reviewer_ids)
    if 'team_manager' in reviewer_roles:
        effective_ids.update(_team_manager_user_ids(
            approval_request,
            include_operating_teacher=False,
        ))
    if 'teacher' in reviewer_roles:
        effective_ids.update(
            str(user_id)
            for user_id in User.objects.filter(
                global_role=User.GlobalRole.TEACHER,
                is_active=True,
            ).exclude(
                id=approval_request.applicant_id,
            ).values_list('id', flat=True)
        )
    effective_ids.discard(str(approval_request.applicant_id))

    users = User.objects.filter(id__in=[
        int(user_id) for user_id in effective_ids if str(user_id).isdigit()
    ]).order_by('name', 'id')
    return {
        'reviewer_ids': sorted(
            [int(user_id) for user_id in effective_ids if str(user_id).isdigit()]
        ),
        'reviewer_roles': sorted(reviewer_roles),
        'reviewer_names': [user.name or user.email for user in users],
    }


def is_authorized_reviewer(user, approval_request):
    """Return whether *user* is the explicitly assigned current reviewer."""
    if (
        not user
        or not user.is_authenticated
        or approval_request.applicant_id == user.id
        or approval_request.status != approval_request.Status.PENDING
    ):
        return False

    if approval_request.flow.flow_type == 'expense':
        from apps.finance.models import FinanceExpense
        from apps.finance.permissions import finance_review_conflicts

        expense = FinanceExpense.objects.filter(
            pk=(approval_request.metadata or {}).get('expense_id'),
        ).first()
        if not expense or finance_review_conflicts(user, expense):
            return False

    # The latest small-team rule has one global operating teacher who may
    # handle every workflow as a fallback. TeamMember.role=teacher does not
    # affect global_role and therefore remains read-only.
    if user.global_role == 'teacher':
        return True

    # Sensitive-data approvals retain their existing record-level permission
    # contract. That contract is scoped and does not broadcast to all teachers.
    if approval_request.flow.flow_type == 'sensitive':
        from apps.sensitive.models import SensitiveAccessRequest
        from apps.sensitive.permissions import can_review_sensitive_request

        access_request = SensitiveAccessRequest.objects.select_related(
            'sensitive_data',
            'sensitive_data__team',
        ).filter(
            pk=(approval_request.metadata or {}).get('access_request_id'),
        ).first()
        return bool(
            access_request
            and can_review_sensitive_request(user, access_request)
        )

    reviewer_ids, reviewer_roles = approval_reviewer_spec(approval_request)
    if str(user.id) in reviewer_ids:
        return True

    # Team-level teachers are represented by TeamMember.role=teacher and have a
    # normal global member role, so they never enter this manager resolution.
    if 'team_manager' in reviewer_roles:
        if str(user.id) in _team_manager_user_ids(approval_request):
            return True

    concrete_roles = reviewer_roles - {'team_manager'}
    if str(user.global_role) in concrete_roles:
        return True

    if reviewer_ids or reviewer_roles:
        return False

    # Historical flows sometimes had only a display name or no steps. The
    # operating teacher was handled above; retain system-admin compatibility.
    return user.global_role == 'sys_admin'


def should_receive_approval_todo(user, approval_request):
    """Prefer exact reviewers; only notify the operating teacher as a fallback."""
    if not is_authorized_reviewer(user, approval_request):
        return False
    if user.global_role != 'teacher':
        return True

    reviewer_ids, reviewer_roles = approval_reviewer_spec(approval_request)
    if str(user.id) in reviewer_ids or 'teacher' in reviewer_roles:
        return True
    if not reviewer_ids and not reviewer_roles:
        return True
    if 'team_manager' in reviewer_roles:
        primary_manager_ids = _team_manager_user_ids(
            approval_request,
            include_operating_teacher=False,
        )
        return not primary_manager_ids
    # A concrete member/admin/custom-role reviewer is already assigned. The
    # operating teacher can still open and process the request, but does not
    # receive a noisy duplicate todo card.
    return False


def _team_root_id(team):
    return team.parent_id or team.id


def _active_user_root_ids(user):
    from .team_models import Team, TeamMember

    memberships = TeamMember.objects.filter(
        user=user,
        status__in=[TeamMember.Status.ACTIVE, TeamMember.Status.ON_LEAVE],
    ).select_related('team')
    roots = {_team_root_id(membership.team) for membership in memberships}
    roots.update(
        _team_root_id(team)
        for team in Team.objects.filter(owner=user).select_related('parent')
    )
    return roots


def _validate_team_membership_metadata(metadata, applicant, flow=None):
    from apps.users.models import User
    from .team_models import Team, TeamMember

    action = str(metadata.get('action', '')).strip()
    if action not in TEAM_MEMBERSHIP_ACTIONS:
        raise serializers.ValidationError({
            'metadata': 'action must be join, transfer, or role_change',
        })

    target_team = Team.objects.select_related('parent').filter(
        pk=metadata.get('target_team_id'),
        is_active=True,
    ).first()
    if not target_team:
        raise serializers.ValidationError({'metadata': 'Target team does not exist'})

    requested_role = str(metadata.get('requested_role', '')).strip()
    if requested_role not in TeamMember.Role.values:
        raise serializers.ValidationError({'metadata': 'requested_role is invalid'})
    if requested_role == TeamMember.Role.OWNER:
        raise serializers.ValidationError({
            'metadata': 'Owner can only be changed through owner transfer',
        })

    is_external = applicant.membership_status == User.MembershipStatus.EXTERNAL
    if is_external and requested_role != TeamMember.Role.EXTERNAL:
        raise serializers.ValidationError({
            'metadata': 'External users can only request the external role',
        })
    if not is_external and requested_role == TeamMember.Role.EXTERNAL:
        raise serializers.ValidationError({
            'metadata': 'Only external users can request the external role',
        })
    if applicant.membership_status not in {
        User.MembershipStatus.ACTIVE,
        User.MembershipStatus.ON_LEAVE,
        User.MembershipStatus.EXTERNAL,
    }:
        raise serializers.ValidationError({
            'metadata': 'Exited users cannot request team membership changes',
        })

    target_root_id = _team_root_id(target_team)
    applicant_root_ids = _active_user_root_ids(applicant)
    if applicant_root_ids and target_root_id not in applicant_root_ids:
        raise serializers.ValidationError({
            'metadata': 'The target team must be in the applicant organization',
        })
    if not applicant_root_ids:
        active_roots = list(
            Team.objects.filter(
                parent__isnull=True,
                is_active=True,
            ).values_list('id', flat=True)[:2]
        )
        if len(active_roots) != 1 or active_roots[0] != target_root_id:
            raise serializers.ValidationError({
                'metadata': 'Unassigned users can only join the single active organization',
            })

    membership = None
    membership_id = metadata.get('membership_id')
    if action in {'transfer', 'role_change'}:
        membership = TeamMember.objects.select_related(
            'team', 'team__parent',
        ).filter(
            pk=membership_id,
            user=applicant,
            status__in=[TeamMember.Status.ACTIVE, TeamMember.Status.ON_LEAVE],
        ).first()
        if not membership:
            raise serializers.ValidationError({
                'metadata': 'membership_id must be an active membership of the applicant',
            })
        if _team_root_id(membership.team) != target_root_id:
            raise serializers.ValidationError({
                'metadata': 'Transfers and role changes must stay in the same organization',
            })
        if membership.role == TeamMember.Role.OWNER:
            raise serializers.ValidationError({
                'metadata': 'The owner must transfer ownership before changing membership',
            })

    target_membership = TeamMember.objects.filter(
        team=target_team,
        user=applicant,
    ).first()
    if action == 'join':
        if target_membership and target_membership.status != TeamMember.Status.EXITED:
            raise serializers.ValidationError({
                'metadata': 'Applicant is already an active member of the target team',
            })
    elif action == 'transfer':
        if membership.team_id == target_team.id:
            raise serializers.ValidationError({
                'metadata': 'Source and target team must be different',
            })
        if target_membership and target_membership.status != TeamMember.Status.EXITED:
            raise serializers.ValidationError({
                'metadata': 'Applicant is already an active member of the target team',
            })
    else:
        if membership.team_id != target_team.id:
            raise serializers.ValidationError({
                'metadata': 'Role changes must target the current membership team',
            })
        if membership.role == requested_role:
            raise serializers.ValidationError({
                'metadata': 'The requested role is already active',
            })

    if requested_role == TeamMember.Role.CO_LEAD and flow is not None:
        has_team_manager_step = any(
            isinstance(step, dict)
            and 'team_manager' in approval_reviewer_spec_for_step(step)[1]
            for step in (flow.steps or [])
        )
        if not has_team_manager_step:
            raise serializers.ValidationError({
                'metadata': 'Co-lead elevation requires a team_manager approval step',
            })

    normalized = {
        'action': action,
        'target_team_id': target_team.id,
        'requested_role': requested_role,
        'reason': str(metadata.get('reason', '')).strip(),
    }
    if membership:
        normalized['membership_id'] = membership.id
    return normalized


def approval_reviewer_spec_for_step(step):
    """Step-only variant used while validating a flow-bound request."""
    class _Flow:
        steps = [step]

    class _Request:
        flow = _Flow()
        current_step = 0

    return approval_reviewer_spec(_Request())


def validate_business_metadata(flow_type, metadata, applicant, flow=None):
    if not isinstance(metadata, dict):
        raise serializers.ValidationError({'metadata': 'Metadata must be an object'})
    normalized = dict(metadata)
    for reserved_key in (
        'reviews',
        'business_status',
        'result_membership_id',
        'source_membership_id',
    ):
        normalized.pop(reserved_key, None)
    if flow_type not in FLOW_TYPES:
        return normalized
    if flow_type == 'leave':
        start = parse_date(str(metadata.get('start_date', '')))
        end = parse_date(str(metadata.get('end_date', '')))
        if not start or not end or end < start:
            raise serializers.ValidationError({
                'metadata': 'Leave requests require a valid start_date and end_date',
            })
        normalized.update({'start_date': start.isoformat(), 'end_date': end.isoformat()})
    elif flow_type == 'expense':
        from apps.finance.models import FinanceExpense

        expense = FinanceExpense.objects.filter(pk=metadata.get('expense_id')).first()
        if not expense:
            raise serializers.ValidationError({'metadata': 'Expense does not exist'})
        if applicant.id not in {
            expense.spender_id, expense.applied_by_id, expense.project.leader_id,
        }:
            raise serializers.ValidationError({'metadata': 'Expense does not belong to applicant'})
        if expense.reimbursement_status not in {
            FinanceExpense.ReimbursementStatus.DRAFT,
            FinanceExpense.ReimbursementStatus.REJECTED,
            FinanceExpense.ReimbursementStatus.PENDING,
        }:
            raise serializers.ValidationError({'metadata': 'Expense cannot enter approval'})
        normalized['expense_id'] = expense.id
    elif flow_type == 'sensitive':
        from apps.sensitive.models import SensitiveAccessRequest

        access = SensitiveAccessRequest.objects.filter(
            pk=metadata.get('access_request_id'), applicant=applicant,
        ).first()
        if not access:
            raise serializers.ValidationError({'metadata': 'Sensitive access request does not exist'})
        if access.status != SensitiveAccessRequest.Status.PENDING:
            raise serializers.ValidationError({'metadata': 'Sensitive access request is not pending'})
        normalized['access_request_id'] = access.id
        expire_hours = metadata.get('expire_hours', 1)
        try:
            expire_hours = int(expire_hours)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError({'metadata': 'expire_hours must be an integer'}) from exc
        if not 1 <= expire_hours <= 168:
            raise serializers.ValidationError({'metadata': 'expire_hours must be between 1 and 168'})
        normalized['expire_hours'] = expire_hours
    elif flow_type == 'project':
        from apps.projects.models import Project, ProjectMember

        project = Project.objects.filter(pk=metadata.get('project_id')).first()
        if not project:
            raise serializers.ValidationError({'metadata': 'Project does not exist'})
        is_member = ProjectMember.objects.filter(project=project, user=applicant).exists()
        if project.leader_id != applicant.id and not is_member:
            raise serializers.ValidationError({'metadata': 'Applicant is not part of this project'})
        changes = metadata.get('changes')
        allowed = {'status', 'priority', 'current_stage', 'planned_end_date', 'intro'}
        if not isinstance(changes, dict) or not changes or set(changes) - allowed:
            raise serializers.ValidationError({'metadata': 'Project changes are missing or unsupported'})
        normalized.update({'project_id': project.id, 'changes': changes})
    elif flow_type == 'team_membership':
        normalized = _validate_team_membership_metadata(
            metadata,
            applicant,
            flow=flow,
        )
    return normalized


def prepare_business_request(approval_request):
    if approval_request.flow.flow_type != 'expense':
        return
    from apps.finance.models import FinanceExpense, FinanceReceipt

    expense = FinanceExpense.objects.get(pk=approval_request.metadata['expense_id'])
    if expense.reimbursement_status in {
        FinanceExpense.ReimbursementStatus.DRAFT,
        FinanceExpense.ReimbursementStatus.REJECTED,
    }:
        if not expense.receipts.filter(
            attachment_type__in=[
                FinanceReceipt.AttachmentType.INVOICE,
                FinanceReceipt.AttachmentType.ORIGINAL_RECEIPT,
            ],
        ).exists():
            raise serializers.ValidationError({
                'metadata': 'An invoice or original receipt is required before submission',
            })
        if not expense.payee_id:
            expense.payee_id = (
                expense.spender_id or approval_request.applicant_id
            )
            expense.save(update_fields=['payee'])
        expense.submit_reimbursement(approval_request.applicant)


@transaction.atomic
def apply_business_decision(approval_request, *, approved, actor, opinion=''):
    flow_type = approval_request.flow.flow_type
    metadata = dict(approval_request.metadata or {})
    if flow_type == 'leave':
        if approved:
            from apps.users.models import User

            applicant = User.objects.select_for_update().get(pk=approval_request.applicant_id)
            applicant.membership_status = User.MembershipStatus.ON_LEAVE
            applicant.save(update_fields=['membership_status'])
    elif flow_type == 'expense':
        from apps.finance.models import FinanceExpense
        from apps.finance.permissions import can_review_expense

        expense = FinanceExpense.objects.select_for_update().get(pk=metadata['expense_id'])
        if not can_review_expense(actor, expense):
            raise serializers.ValidationError(
                'The reviewer is not authorized or has a conflict of interest'
            )
        expense.review_reimbursement(actor, approved, opinion)
    elif flow_type == 'sensitive':
        from apps.sensitive.services import SensitiveDataService

        if approved:
            success, result = SensitiveDataService.approve_request(
                metadata['access_request_id'], actor,
                expire_hours=metadata.get('expire_hours', 1),
                approval_opinion=opinion,
            )
        else:
            success, result = SensitiveDataService.reject_request(
                metadata['access_request_id'], actor,
                approval_opinion=opinion,
            )
        if not success:
            raise serializers.ValidationError(str(result))
    elif flow_type == 'project' and approved:
        from apps.projects.models import Project
        from apps.projects.serializers import ProjectSerializer

        project = Project.objects.select_for_update().get(pk=metadata['project_id'])
        serializer = ProjectSerializer(
            project, data=metadata['changes'], partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
    elif flow_type == 'team_membership' and approved:
        metadata = _apply_team_membership_decision(
            approval_request,
            actor=actor,
        )
    metadata['business_status'] = 'approved' if approved else 'rejected'
    approval_request.metadata = metadata


def _apply_team_membership_decision(approval_request, *, actor):
    """Atomically materialize an approved team membership request."""
    from .team_models import Team, TeamMember, TeamMembershipEvent

    metadata = dict(approval_request.metadata or {})
    # Revalidate inside the final transaction to catch membership changes made
    # while the request was waiting for approval.
    normalized = _validate_team_membership_metadata(
        metadata,
        approval_request.applicant,
        flow=approval_request.flow,
    )
    action = normalized['action']
    target_team = Team.objects.select_for_update().get(
        pk=normalized['target_team_id'],
    )
    requested_role = normalized['requested_role']
    reason = normalized.get('reason', '')

    if action == 'role_change':
        membership = TeamMember.objects.select_for_update().get(
            pk=normalized['membership_id'],
            user=approval_request.applicant,
        )
        old_role = membership.role
        membership.role = requested_role
        membership.save(update_fields=['role'])
        TeamMembershipEvent.objects.create(
            membership=membership,
            event_type='role_changed',
            from_role=old_role,
            to_role=membership.role,
            from_status=membership.status,
            to_status=membership.status,
            reason=reason,
            operator=actor,
        )
        metadata['result_membership_id'] = membership.id
        approval_request.metadata = metadata
        return metadata

    if action == 'transfer':
        source = TeamMember.objects.select_for_update().get(
            pk=normalized['membership_id'],
            user=approval_request.applicant,
        )
        old_status = source.status
        source.status = TeamMember.Status.EXITED
        source.left_at = timezone.now()
        source.exit_reason = reason or f'转入 {target_team.name}'
        source.save(update_fields=['status', 'left_at', 'exit_reason'])
        TeamMembershipEvent.objects.create(
            membership=source,
            event_type='transferred_out',
            from_role=source.role,
            to_role=source.role,
            from_status=old_status,
            to_status=source.status,
            reason=source.exit_reason,
            operator=actor,
        )
        metadata['source_membership_id'] = source.id

    target, created = TeamMember.objects.select_for_update().get_or_create(
        team=target_team,
        user=approval_request.applicant,
        defaults={
            'role': requested_role,
            'status': TeamMember.Status.ACTIVE,
        },
    )
    if not created:
        previous_status = target.status
        previous_role = target.role
        target.status = TeamMember.Status.ACTIVE
        target.role = requested_role
        target.left_at = None
        target.exit_reason = ''
        target.handover_to = None
        target.handover_notes = ''
        target.save()
        event_type = 'transferred_in' if action == 'transfer' else 'reactivated'
        TeamMembershipEvent.objects.create(
            membership=target,
            event_type=event_type,
            from_role=previous_role,
            to_role=target.role,
            from_status=previous_status,
            to_status=target.status,
            reason=reason,
            operator=actor,
        )
    else:
        TeamMembershipEvent.objects.create(
            membership=target,
            event_type='transferred_in' if action == 'transfer' else 'joined',
            to_role=target.role,
            to_status=target.status,
            reason=reason,
            operator=actor,
        )
    metadata['result_membership_id'] = target.id
    approval_request.metadata = metadata
    return metadata


@transaction.atomic
def cancel_business_request(approval_request):
    flow_type = approval_request.flow.flow_type
    metadata = dict(approval_request.metadata or {})
    if flow_type == 'expense':
        from apps.finance.models import FinanceExpense

        expense = FinanceExpense.objects.select_for_update().get(pk=metadata['expense_id'])
        if expense.reimbursement_status == FinanceExpense.ReimbursementStatus.PENDING:
            expense.reimbursement_status = FinanceExpense.ReimbursementStatus.DRAFT
            expense.applied_by = None
            expense.applied_at = None
            expense.save(update_fields=['reimbursement_status', 'applied_by', 'applied_at'])
    elif flow_type == 'sensitive':
        from apps.sensitive.models import SensitiveAccessRequest

        SensitiveAccessRequest.objects.filter(
            pk=metadata['access_request_id'],
            status=SensitiveAccessRequest.Status.PENDING,
        ).update(status=SensitiveAccessRequest.Status.REJECTED)
    metadata['business_status'] = 'cancelled'
    approval_request.metadata = metadata
