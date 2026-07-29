"""Small-team generic workflow and team-membership application coverage."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.common.approval_models import ApprovalFlow, ApprovalRequest
from apps.common.team_models import Team, TeamMember, TeamMembershipEvent


REQUESTS_URL = '/api/v1/approvals/requests/'
TODO_URL = '/api/v1/todo/'


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


def extract_data(response):
    body = response.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def make_organization(make_user):
    manager = make_user(email='team-approval-manager@example.com')
    root = Team.objects.create(name='数字创新实践团队', owner=manager)
    TeamMember.objects.create(
        team=root,
        user=manager,
        role=TeamMember.Role.OWNER,
    )
    first = Team.objects.create(
        name='项目一组',
        owner=manager,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    second = Team.objects.create(
        name='项目二组',
        owner=manager,
        parent=root,
        team_type=Team.TeamType.SQUAD,
    )
    for team in (first, second):
        TeamMember.objects.create(
            team=team,
            user=manager,
            role=TeamMember.Role.OWNER,
        )
    return manager, root, first, second


def membership_flow(*, role='team_manager'):
    return ApprovalFlow.objects.create(
        name='团队成员关系申请',
        flow_type='team_membership',
        steps=[{'name': '团队负责人审批', 'reviewer_role': role}],
    )


def submit_membership_request(user, flow, metadata, title='团队成员申请'):
    return client_for(user).post(
        REQUESTS_URL,
        {
            'flow': flow.id,
            'title': title,
            'content': metadata.get('reason', ''),
            'metadata': metadata,
        },
        format='json',
    )


@pytest.mark.api
@pytest.mark.django_db
class TestTeamMembershipApproval:
    def test_team_owner_approves_join_and_history_is_exposed(
        self,
        make_user,
    ):
        manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='join-applicant@example.com')
        flow = membership_flow()

        created = submit_membership_request(
            applicant,
            flow,
            {
                'action': 'join',
                'target_team_id': target.id,
                'requested_role': TeamMember.Role.MEMBER,
                'reason': '加入项目一组',
            },
        )
        assert created.status_code in (200, 201), created.json()
        request_id = extract_data(created)['id']

        approved = client_for(manager).post(
            f'{REQUESTS_URL}{request_id}/approve/',
            {'opinion': '同意加入'},
            format='json',
        )
        assert approved.status_code == 200, approved.json()
        payload = extract_data(approved)
        assert payload['status'] == ApprovalRequest.Status.APPROVED
        assert payload['review_history'][0]['by'] == manager.id
        assert payload['review_history'][0]['step_name'] == '团队负责人审批'

        membership = TeamMember.objects.get(team=target, user=applicant)
        assert membership.role == TeamMember.Role.MEMBER
        assert membership.status == TeamMember.Status.ACTIVE
        assert TeamMembershipEvent.objects.filter(
            membership=membership,
            event_type='joined',
            operator=manager,
        ).exists()

    def test_team_owner_approves_transfer_and_preserves_source_history(
        self,
        make_user,
    ):
        manager, _root, source_team, target_team = make_organization(make_user)
        applicant = make_user(email='transfer-applicant@example.com')
        source = TeamMember.objects.create(
            team=source_team,
            user=applicant,
            role=TeamMember.Role.MEMBER,
        )
        flow = membership_flow()

        created = submit_membership_request(
            applicant,
            flow,
            {
                'action': 'transfer',
                'target_team_id': target_team.id,
                'membership_id': source.id,
                'requested_role': TeamMember.Role.MEMBER,
                'reason': '转入项目二组',
            },
        )
        request_id = extract_data(created)['id']
        response = client_for(manager).post(
            f'{REQUESTS_URL}{request_id}/approve/',
            {},
            format='json',
        )
        assert response.status_code == 200, response.json()

        source.refresh_from_db()
        target = TeamMember.objects.get(team=target_team, user=applicant)
        assert source.status == TeamMember.Status.EXITED
        assert source.left_at is not None
        assert target.status == TeamMember.Status.ACTIVE
        assert TeamMembershipEvent.objects.filter(
            membership=source,
            event_type='transferred_out',
        ).exists()
        assert TeamMembershipEvent.objects.filter(
            membership=target,
            event_type='transferred_in',
        ).exists()

    def test_owner_approves_role_change_and_co_lead_elevation(
        self,
        make_user,
    ):
        manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='role-applicant@example.com')
        membership = TeamMember.objects.create(
            team=target,
            user=applicant,
            role=TeamMember.Role.MEMBER,
        )
        flow = membership_flow()

        created = submit_membership_request(
            applicant,
            flow,
            {
                'action': 'role_change',
                'target_team_id': target.id,
                'membership_id': membership.id,
                'requested_role': TeamMember.Role.CO_LEAD,
                'reason': '承担项目负责人工作',
            },
        )
        assert created.status_code in (200, 201), created.json()
        request_id = extract_data(created)['id']
        approved = client_for(manager).post(
            f'{REQUESTS_URL}{request_id}/approve/',
            {'opinion': '确认提权'},
            format='json',
        )
        assert approved.status_code == 200, approved.json()
        membership.refresh_from_db()
        assert membership.role == TeamMember.Role.CO_LEAD
        event = TeamMembershipEvent.objects.get(
            membership=membership,
            event_type='role_changed',
        )
        assert event.from_role == TeamMember.Role.MEMBER
        assert event.to_role == TeamMember.Role.CO_LEAD

    def test_read_only_teacher_cannot_review_but_operating_teacher_can_fallback(
        self,
        make_user,
    ):
        _manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='teacher-boundary-applicant@example.com')
        viewing_teacher = make_user(email='viewing-teacher@example.com')
        TeamMember.objects.create(
            team=target,
            user=viewing_teacher,
            role=TeamMember.Role.TEACHER,
        )
        operating_teacher = make_user(
            email='operating-teacher@example.com',
            global_role='teacher',
        )
        flow = membership_flow()
        created = submit_membership_request(
            applicant,
            flow,
            {
                'action': 'join',
                'target_team_id': target.id,
                'requested_role': TeamMember.Role.MEMBER,
                'reason': '权限边界',
            },
        )
        request_id = extract_data(created)['id']

        denied = client_for(viewing_teacher).post(
            f'{REQUESTS_URL}{request_id}/approve/',
            {},
            format='json',
        )
        assert denied.status_code in (403, 404)

        approved = client_for(operating_teacher).post(
            f'{REQUESTS_URL}{request_id}/approve/',
            {},
            format='json',
        )
        assert approved.status_code == 200, approved.json()
        assert TeamMember.objects.filter(
            team=target,
            user=applicant,
            status=TeamMember.Status.ACTIVE,
        ).exists()

    def test_operating_teacher_can_review_explicit_teacher_step(
        self,
        make_user,
    ):
        _manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='teacher-explicit-applicant@example.com')
        operating_teacher = make_user(
            email='explicit-operating-teacher@example.com',
            global_role='teacher',
        )
        flow = membership_flow(role='teacher')
        created = submit_membership_request(
            applicant,
            flow,
            {
                'action': 'join',
                'target_team_id': target.id,
                'requested_role': TeamMember.Role.MEMBER,
                'reason': '明确交给操作老师',
            },
        )
        request_id = extract_data(created)['id']

        approved = client_for(operating_teacher).post(
            f'{REQUESTS_URL}{request_id}/approve/',
            {},
            format='json',
        )
        assert approved.status_code == 200, approved.json()
        assert TeamMember.objects.filter(
            team=target,
            user=applicant,
            status=TeamMember.Status.ACTIVE,
        ).exists()

    def test_applicant_cannot_self_review_even_when_a_team_admin(
        self,
        make_user,
    ):
        _manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='self-review-applicant@example.com')
        membership = TeamMember.objects.create(
            team=target,
            user=applicant,
            role=TeamMember.Role.ADMIN,
        )
        flow = membership_flow()
        created = submit_membership_request(
            applicant,
            flow,
            {
                'action': 'role_change',
                'target_team_id': target.id,
                'membership_id': membership.id,
                'requested_role': TeamMember.Role.MEMBER,
                'reason': '主动降级',
            },
        )
        request_id = extract_data(created)['id']

        denied = client_for(applicant).post(
            f'{REQUESTS_URL}{request_id}/approve/',
            {},
            format='json',
        )
        assert denied.status_code == 403
        membership.refresh_from_db()
        assert membership.role == TeamMember.Role.ADMIN

    def test_rejection_and_cancellation_do_not_change_membership(
        self,
        make_user,
    ):
        manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='no-mutation-applicant@example.com')
        flow = membership_flow()
        metadata = {
            'action': 'join',
            'target_team_id': target.id,
            'requested_role': TeamMember.Role.MEMBER,
            'reason': '不应落地',
        }

        rejected = submit_membership_request(applicant, flow, metadata)
        rejected_id = extract_data(rejected)['id']
        assert client_for(manager).post(
            f'{REQUESTS_URL}{rejected_id}/reject/',
            {'opinion': '暂不同意'},
            format='json',
        ).status_code == 200
        assert not TeamMember.objects.filter(team=target, user=applicant).exists()

        cancelled = submit_membership_request(applicant, flow, metadata)
        cancelled_id = extract_data(cancelled)['id']
        assert client_for(applicant).post(
            f'{REQUESTS_URL}{cancelled_id}/cancel/',
            {},
            format='json',
        ).status_code == 200
        assert not TeamMember.objects.filter(team=target, user=applicant).exists()


@pytest.mark.api
@pytest.mark.django_db
class TestWorkflowApprovalTodo:
    def test_assigned_manager_gets_one_card_with_deep_link(self, make_user):
        manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='todo-workflow-applicant@example.com')
        flow = membership_flow()
        created = submit_membership_request(
            applicant,
            flow,
            {
                'action': 'join',
                'target_team_id': target.id,
                'requested_role': TeamMember.Role.MEMBER,
                'reason': '待办定位',
            },
        )
        request_id = extract_data(created)['id']

        response = client_for(manager).get(
            f'{TODO_URL}?type=workflow_approval'
        )
        assert response.status_code == 200, response.json()
        results = extract_data(response)['results']
        assert len(results) == 1
        assert results[0]['id'] == request_id
        assert results[0]['type'] == 'workflow_approval'
        assert results[0]['route_name'] == 'PlatformCapabilities'
        assert results[0]['route_query'] == {
            'tab': 'approvals',
            'request_id': request_id,
        }
        assert (
            results[0]['url']
            == f'/admin/platform-capabilities?tab=approvals&request_id={request_id}'
        )

    def test_unrelated_viewing_teacher_has_no_workflow_card(self, make_user):
        _manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='todo-hidden-applicant@example.com')
        viewer = make_user(email='todo-viewing-teacher@example.com')
        TeamMember.objects.create(
            team=target,
            user=viewer,
            role=TeamMember.Role.TEACHER,
        )
        flow = membership_flow()
        submit_membership_request(
            applicant,
            flow,
            {
                'action': 'join',
                'target_team_id': target.id,
                'requested_role': TeamMember.Role.MEMBER,
                'reason': '不广播',
            },
        )

        response = client_for(viewer).get(
            f'{TODO_URL}?type=workflow_approval'
        )
        assert response.status_code == 200
        assert extract_data(response)['results'] == []

    def test_operating_teacher_can_process_but_is_not_notified_when_owner_is_primary(
        self,
        make_user,
    ):
        _manager, _root, target, _other = make_organization(make_user)
        applicant = make_user(email='todo-primary-applicant@example.com')
        operating_teacher = make_user(
            email='todo-fallback-teacher@example.com',
            global_role='teacher',
        )
        flow = membership_flow()
        created = submit_membership_request(
            applicant,
            flow,
            {
                'action': 'join',
                'target_team_id': target.id,
                'requested_role': TeamMember.Role.MEMBER,
                'reason': '负责人优先处理',
            },
        )
        request_id = extract_data(created)['id']

        todo_response = client_for(operating_teacher).get(
            f'{TODO_URL}?type=workflow_approval'
        )
        assert extract_data(todo_response)['results'] == []

        # The sole operating teacher still has the global fallback capability.
        detail = client_for(operating_teacher).get(
            f'{REQUESTS_URL}{request_id}/'
        )
        assert detail.status_code == 200
        assert extract_data(detail)['can_review'] is True

    def test_operating_teacher_gets_fallback_card_for_unassigned_legacy_flow(
        self,
        make_user,
    ):
        applicant = make_user(email='todo-legacy-applicant@example.com')
        operating_teacher = make_user(
            email='todo-legacy-teacher@example.com',
            global_role='teacher',
        )
        flow = ApprovalFlow.objects.create(
            name='历史未分配流程',
            flow_type='generic',
            steps=[],
        )
        approval_request = ApprovalRequest.objects.create(
            applicant=applicant,
            flow=flow,
            title='需要操作老师兜底',
        )

        response = client_for(operating_teacher).get(
            f'{TODO_URL}?type=workflow_approval'
        )
        results = extract_data(response)['results']
        assert [item['id'] for item in results] == [approval_request.id]


@pytest.mark.api
@pytest.mark.django_db
def test_new_legacy_shape_flow_is_normalized_to_explicit_admin(admin_client):
    response = admin_client.post(
        '/api/v1/approvals/flows/',
        {
            'name': '旧形状兼容流程',
            'flow_type': 'generic',
            'steps': [{'name': '历史节点'}],
        },
        format='json',
    )
    assert response.status_code in (200, 201), response.json()
    flow = ApprovalFlow.objects.get(name='旧形状兼容流程')
    assert flow.steps == [{
        'name': '历史节点',
        'reviewer_role': 'sys_admin',
    }]


@pytest.mark.api
@pytest.mark.django_db
class TestUnifiedExpenseApprovalGuardrails:
    def test_generic_workflow_cannot_submit_expense_without_source_document(
        self,
        make_user,
        make_project,
    ):
        from apps.finance.models import FinanceExpense

        applicant = make_user(email='expense-document-applicant@example.com')
        project = make_project(leader=applicant)
        expense = FinanceExpense.objects.create(
            project=project,
            title='缺少票据的报销',
            amount='120.00',
            expense_date='2026-07-29',
            spender=applicant,
            payee=applicant,
        )
        flow = ApprovalFlow.objects.create(
            name='通用报销审批',
            flow_type='expense',
            steps=[{'name': '操作老师审核', 'reviewer_role': 'teacher'}],
        )

        response = client_for(applicant).post(
            REQUESTS_URL,
            {
                'flow': flow.id,
                'title': '提交报销',
                'metadata': {'expense_id': expense.id},
            },
            format='json',
        )
        assert response.status_code == 400
        expense.refresh_from_db()
        assert expense.reimbursement_status == FinanceExpense.ReimbursementStatus.DRAFT
        assert not ApprovalRequest.objects.filter(
            flow=flow,
            applicant=applicant,
        ).exists()

    def test_operating_teacher_still_cannot_review_when_they_are_payee(
        self,
        make_user,
        make_project,
    ):
        from apps.finance.models import FinanceExpense, FinanceReceipt

        applicant = make_user(email='expense-conflict-applicant@example.com')
        operating_teacher = make_user(
            email='expense-conflict-teacher@example.com',
            global_role='teacher',
        )
        project = make_project(leader=applicant)
        expense = FinanceExpense.objects.create(
            project=project,
            title='老师代垫报销',
            amount='260.00',
            expense_date='2026-07-29',
            spender=operating_teacher,
            payee=operating_teacher,
        )
        FinanceReceipt.objects.create(
            expense=expense,
            attachment_type=FinanceReceipt.AttachmentType.INVOICE,
            file=SimpleUploadedFile(
                'invoice.png',
                b'fake-png-content',
                content_type='image/png',
            ),
            uploaded_by=applicant,
        )
        flow = ApprovalFlow.objects.create(
            name='利益冲突报销审批',
            flow_type='expense',
            steps=[{'name': '操作老师审核', 'reviewer_role': 'teacher'}],
        )
        created = client_for(applicant).post(
            REQUESTS_URL,
            {
                'flow': flow.id,
                'title': '老师代垫报销申请',
                'metadata': {'expense_id': expense.id},
            },
            format='json',
        )
        assert created.status_code in (200, 201), created.json()
        request_id = extract_data(created)['id']

        denied = client_for(operating_teacher).post(
            f'{REQUESTS_URL}{request_id}/approve/',
            {},
            format='json',
        )
        assert denied.status_code == 403
        expense.refresh_from_db()
        assert expense.reimbursement_status == FinanceExpense.ReimbursementStatus.PENDING
