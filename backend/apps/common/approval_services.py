from django.db import transaction
from django.utils.dateparse import parse_date
from rest_framework import serializers


FLOW_TYPES = {'leave', 'expense', 'sensitive', 'project'}


def validate_business_metadata(flow_type, metadata, applicant):
    if flow_type not in FLOW_TYPES:
        return dict(metadata) if isinstance(metadata, dict) else {}
    if not isinstance(metadata, dict):
        raise serializers.ValidationError({'metadata': 'Metadata must be an object'})
    normalized = dict(metadata)
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
    return normalized


def prepare_business_request(approval_request):
    if approval_request.flow.flow_type != 'expense':
        return
    from apps.finance.models import FinanceExpense

    expense = FinanceExpense.objects.get(pk=approval_request.metadata['expense_id'])
    if expense.reimbursement_status in {
        FinanceExpense.ReimbursementStatus.DRAFT,
        FinanceExpense.ReimbursementStatus.REJECTED,
    }:
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

        expense = FinanceExpense.objects.select_for_update().get(pk=metadata['expense_id'])
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
    metadata['business_status'] = 'approved' if approved else 'rejected'
    approval_request.metadata = metadata


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
