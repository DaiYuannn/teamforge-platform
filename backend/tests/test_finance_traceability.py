from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import Competition, CompetitionEvent
from apps.finance.models import (
    FinanceBudget,
    FinanceExpense,
    FinanceIncome,
    FinanceInternalTransfer,
    FinancePayment,
)
from apps.projects.models import ProjectMember


def data(response):
    payload = response.json()
    return payload.get('data', payload)


def upload(name, content=b'proof'):
    return SimpleUploadedFile(name, content, content_type='image/png')


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    client.user = user
    return client


def add_project_member(project, user, role=ProjectMember.RoleInProject.PARTICIPANT):
    member, _ = ProjectMember.objects.update_or_create(
        project=project,
        user=user,
        defaults={
            'role_in_project': role,
            'status': ProjectMember.Status.ACTIVE,
        },
    )
    return member


def make_entry(project, suffix='A'):
    event = CompetitionEvent.objects.create(
        name=f'创新比赛{suffix}',
        edition='2026',
        organizer='主办方',
    )
    return Competition.objects.create(
        project=project,
        event=event,
        entry_name=f'{project.name}-{suffix}队',
        name=event.name,
    )


def make_shared_entry(project, event, suffix):
    return Competition.objects.create(
        project=project,
        event=event,
        entry_name=f'{project.name}-{suffix}队',
        name=event.name,
    )


@pytest.mark.api
@pytest.mark.django_db
class TestFinanceTraceability:
    def test_member_claim_partial_payments_require_proof_and_drive_budget(
        self,
        make_project,
        make_user,
    ):
        teacher = make_user(
            email='trace-reviewer@example.com',
            global_role='teacher',
        )
        member = make_user(email='trace-applicant@example.com')
        teacher_client = client_for(teacher)
        member_client = client_for(member)
        project = make_project(leader=teacher)
        add_project_member(project, member)
        entry = make_entry(project)

        created = member_client.post('/api/v1/finance/expenses/', {
            'project': project.id,
            'competition_entry': entry.id,
            'title': '比赛现场往返车费',
            'amount': '100.00',
            'expense_date': '2026-07-29',
            'category': 'travel',
            'payee': teacher.id,
        }, format='json')
        assert created.status_code == 201, created.json()
        expense_id = data(created)['id']
        expense = FinanceExpense.objects.get(pk=expense_id)
        assert expense.spender == member
        assert expense.payee == member

        missing_invoice = member_client.post(
            f'/api/v1/finance/expenses/{expense_id}/submit_reimbursement/',
            {},
            format='json',
        )
        assert missing_invoice.status_code == 400

        receipt = member_client.post('/api/v1/finance/receipts/', {
            'expense': expense_id,
            'attachment_type': 'invoice',
            'file': upload('invoice.png'),
        }, format='multipart')
        assert receipt.status_code == 201, receipt.json()
        submitted = member_client.post(
            f'/api/v1/finance/expenses/{expense_id}/submit_reimbursement/',
            {},
            format='json',
        )
        assert submitted.status_code == 200, submitted.json()

        reviewed = teacher_client.post(
            f'/api/v1/finance/expenses/{expense_id}/review_reimbursement/',
            {'approved': True, 'opinion': '票据有效'},
            format='json',
        )
        assert reviewed.status_code == 200, reviewed.json()
        budget = FinanceBudget.objects.get(project=project)
        assert budget.pending_reimbursement == Decimal('100.00')
        assert budget.used_amount == Decimal('0.00')

        no_proof = teacher_client.post('/api/v1/finance/payments/', {
            'expense': expense_id,
            'amount': '40.00',
            'recipient': member.id,
            'status': 'completed',
            'payment_method': '银行转账',
        }, format='json')
        assert no_proof.status_code == 400

        first = teacher_client.post('/api/v1/finance/payments/', {
            'expense': expense_id,
            'amount': '40.00',
            'recipient': member.id,
            'status': 'completed',
            'payment_method': '银行转账',
            'payment_reference': 'PAY-1',
            'proof_file': upload('payment-1.png'),
        }, format='multipart')
        assert first.status_code == 201, first.json()
        expense.refresh_from_db()
        budget.refresh_from_db()
        assert expense.reimbursement_status == 'partial_paid'
        assert expense.paid_amount == Decimal('40.00')
        assert budget.used_amount == Decimal('40.00')
        assert budget.pending_reimbursement == Decimal('60.00')
        payment_proof = FinancePayment.objects.get(
            payment_reference='PAY-1',
        ).receipts.get(attachment_type='payment_proof')
        protected = teacher_client.delete(
            f'/api/v1/finance/receipts/{payment_proof.id}/'
        )
        assert protected.status_code == 400

        second = teacher_client.post('/api/v1/finance/payments/', {
            'expense': expense_id,
            'amount': '60.00',
            'recipient': member.id,
            'status': 'completed',
            'payment_method': '银行转账',
            'payment_reference': 'PAY-2',
            'proof_file': upload('payment-2.png'),
        }, format='multipart')
        assert second.status_code == 201, second.json()
        expense.refresh_from_db()
        budget.refresh_from_db()
        assert expense.reimbursement_status == 'paid'
        assert budget.used_amount == Decimal('100.00')
        assert budget.pending_reimbursement == Decimal('0.00')
        assert expense.payments.count() == 2
        assert expense.payments.filter(receipts__attachment_type='payment_proof').count() == 2

    def test_bonus_stages_and_entry_allocations(
        self,
        teacher_client,
        make_project,
    ):
        project = make_project(leader=teacher_client.user)
        first_entry = make_entry(project, 'A')
        second_entry = make_entry(project, 'B')

        income_response = teacher_client.post('/api/v1/finance/incomes/', {
            'project': project.id,
            'competition_entry': first_entry.id,
            'title': '省赛奖金',
            'amount': '3000.00',
            'income_type': 'bonus',
            'stage': 'expected',
            'income_date': '2026-07-29',
        }, format='json')
        assert income_response.status_code == 201, income_response.json()
        income_id = data(income_response)['id']
        budget = FinanceBudget.objects.get(project=project)
        assert budget.bonus_amount == Decimal('0.00')

        confirmed = teacher_client.post(
            f'/api/v1/finance/incomes/{income_id}/set_stage/',
            {'stage': 'confirmed'},
            format='json',
        )
        assert confirmed.status_code == 200, confirmed.json()
        without_proof = teacher_client.post(
            f'/api/v1/finance/incomes/{income_id}/set_stage/',
            {'stage': 'received'},
            format='json',
        )
        assert without_proof.status_code == 400
        received = teacher_client.post(
            f'/api/v1/finance/incomes/{income_id}/set_stage/',
            {
                'stage': 'received',
                'proof_file': upload('bonus-arrival.png'),
            },
            format='multipart',
        )
        assert received.status_code == 200, received.json()
        budget.refresh_from_db()
        assert budget.bonus_amount == Decimal('3000.00')
        assert FinanceIncome.objects.get(pk=income_id).receipts.filter(
            attachment_type='income_proof',
        ).exists()

        shared = teacher_client.post('/api/v1/finance/incomes/', {
            'project': project.id,
            'title': '两队共享预计奖金',
            'amount': '1000.00',
            'income_type': 'bonus',
            'stage': 'expected',
            'income_date': '2026-07-29',
        }, format='json')
        shared_id = data(shared)['id']
        wrong_sum = teacher_client.post(
            f'/api/v1/finance/incomes/{shared_id}/set_allocations/',
            {'allocations': [
                {'competition_entry': first_entry.id, 'amount': '400.00'},
                {'competition_entry': second_entry.id, 'amount': '500.00'},
            ]},
            format='json',
        )
        assert wrong_sum.status_code == 400
        allocated = teacher_client.post(
            f'/api/v1/finance/incomes/{shared_id}/set_allocations/',
            {'allocations': [
                {'competition_entry': first_entry.id, 'amount': '400.00'},
                {'competition_entry': second_entry.id, 'amount': '600.00'},
            ]},
            format='json',
        )
        assert allocated.status_code == 200, allocated.json()
        assert len(data(allocated)['allocations']) == 2

    def test_dual_perspective_detail_timeline_and_todos(
        self,
        make_project,
        make_user,
    ):
        teacher = make_user(
            email='trace-viewer@example.com',
            global_role='teacher',
        )
        member = make_user(email='trace-todo-member@example.com')
        teacher_client = client_for(teacher)
        member_client = client_for(member)
        project = make_project(leader=teacher)
        add_project_member(project, member)
        entry = make_entry(project)
        expense = FinanceExpense.objects.create(
            project=project,
            competition_entry=entry,
            title='待审核交通费',
            amount=Decimal('88.00'),
            spender=member,
            payee=member,
            expense_date='2026-07-29',
        )
        member_client.post('/api/v1/finance/receipts/', {
            'expense': expense.id,
            'attachment_type': 'original_receipt',
            'file': upload('ticket.png'),
        }, format='multipart')
        member_client.post(
            f'/api/v1/finance/expenses/{expense.id}/submit_reimbursement/',
            {},
            format='json',
        )

        project_view = teacher_client.get(
            '/api/v1/finance/traceability/summary/?perspective=project'
        )
        assert project_view.status_code == 200, project_view.json()
        assert any(
            group['project'] == project.id
            for group in data(project_view)['groups']
        )
        competition_view = teacher_client.get(
            '/api/v1/finance/traceability/summary/?perspective=competition'
        )
        assert competition_view.status_code == 200, competition_view.json()
        assert data(competition_view)['groups'][0]['entries'][0][
            'competition_entry'
        ] == entry.id

        detail = teacher_client.get(
            f'/api/v1/finance/traceability/detail/?competition_entry={entry.id}'
        )
        assert detail.status_code == 200, detail.json()
        assert data(detail)['expenses'][0]['id'] == expense.id
        timeline = teacher_client.get(
            f'/api/v1/finance/traceability/timeline/?expense={expense.id}'
        )
        assert timeline.status_code == 200
        timeline_rows = data(timeline)
        assert {
            item['event_type'] for item in timeline_rows
        } >= {'attachment_uploaded', 'reimbursement_submitted'}
        assert {'title', 'operator_name', 'occurred_at'} <= set(
            timeline_rows[0]
        )

        todos = teacher_client.get('/api/v1/finance/fund-todos/')
        assert todos.status_code == 200, todos.json()
        assert data(todos)['summary']['pending_review']['count'] == 1

    def test_self_review_and_team_teacher_write_are_forbidden(
        self,
        teacher_client,
        make_project,
        make_user,
    ):
        project = make_project(leader=teacher_client.user)
        expense = FinanceExpense.objects.create(
            project=project,
            title='负责人本人垫付',
            amount=Decimal('50.00'),
            spender=teacher_client.user,
            payee=teacher_client.user,
            expense_date='2026-07-29',
        )
        teacher_client.post('/api/v1/finance/receipts/', {
            'expense': expense.id,
            'attachment_type': 'invoice',
            'file': upload('self.png'),
        }, format='multipart')
        teacher_client.post(
            f'/api/v1/finance/expenses/{expense.id}/submit_reimbursement/',
            {},
            format='json',
        )
        self_review = teacher_client.post(
            f'/api/v1/finance/expenses/{expense.id}/review_reimbursement/',
            {'approved': True},
            format='json',
        )
        assert self_review.status_code == 403

        readonly_teacher = make_user(
            email='team-teacher-readonly@example.com',
            global_role='member',
        )
        add_project_member(project, readonly_teacher)
        team = Team.objects.create(
            name='经费测试总团队',
            code='FINANCE-READONLY-TEACHER',
            owner=teacher_client.user,
        )
        TeamMember.objects.create(
            team=team,
            user=readonly_teacher,
            role=TeamMember.Role.TEACHER,
        )
        client = APIClient()
        client.force_authenticate(readonly_teacher)
        denied = client.post('/api/v1/finance/payments/', {
            'expense': expense.id,
            'recipient': teacher_client.user.id,
            'amount': '50.00',
            'payment_method': '银行转账',
        }, format='json')
        assert denied.status_code == 403

    def test_internal_transfer_never_double_counts_cashflow(
        self,
        make_project,
        make_user,
    ):
        teacher = make_user(
            email='trace-transfer-teacher@example.com',
            global_role='teacher',
        )
        member = make_user(email='trace-transfer-recipient@example.com')
        teacher_client = client_for(teacher)
        project = make_project(leader=teacher)
        add_project_member(project, member)
        before = FinanceBudget.objects.create(
            project=project,
            planned_amount=Decimal('1000.00'),
        )
        response = teacher_client.post('/api/v1/finance/transfers/', {
            'project': project.id,
            'from_user': teacher.id,
            'to_user': member.id,
            'amount': '200.00',
            'status': 'completed',
            'payment_method': '银行转账',
            'payment_reference': 'INTERNAL-1',
            'proof_file': upload('internal-transfer.png'),
        }, format='multipart')
        assert response.status_code == 201, response.json()
        transfer = FinanceInternalTransfer.objects.get(pk=data(response)['id'])
        assert transfer.status == 'completed'
        assert transfer.receipts.filter(attachment_type='transfer_proof').exists()
        before.refresh_from_db()
        assert before.used_amount == Decimal('0.00')
        assert before.pending_reimbursement == Decimal('0.00')

    def test_one_event_four_projects_share_income_and_expense_without_duplication(
        self,
        teacher_client,
        make_project,
    ):
        root = Team.objects.create(
            name='跨项目资金追溯总团队',
            code='FINANCE-CROSS-PROJECT-ROOT',
            owner=teacher_client.user,
        )
        projects = [
            make_project(leader=teacher_client.user)
            for _ in range(4)
        ]
        for project in projects:
            project.teams.add(root)
        event = CompetitionEvent.objects.create(
            organization=root,
            name='全国创新实践赛',
            edition='2026',
            organizer='赛事组委会',
        )
        entries = [
            make_shared_entry(project, event, suffix)
            for project, suffix in zip(projects, 'ABCD')
        ]
        shares = [Decimal('100'), Decimal('200'), Decimal('300'), Decimal('400')]

        income = FinanceIncome.objects.create(
            project=projects[0],
            title='四队共享到账奖金',
            amount=Decimal('1000'),
            income_type=FinanceIncome.IncomeType.BONUS,
            stage=FinanceIncome.Stage.RECEIVED,
            income_date='2026-07-29',
            recorded_by=teacher_client.user,
        )
        expense = FinanceExpense.objects.create(
            project=projects[0],
            title='四队共享场地支出',
            amount=Decimal('1000'),
            expense_date='2026-07-29',
            category=FinanceExpense.Category.COMPETITION_FEE,
            reimbursement_status=FinanceExpense.ReimbursementStatus.NOT_REQUIRED,
            spender=teacher_client.user,
            payee=teacher_client.user,
        )
        allocation_payload = {
            'allocations': [
                {
                    'competition_entry': entry.id,
                    'amount': str(share),
                }
                for entry, share in zip(entries, shares)
            ],
        }
        income_allocated = teacher_client.post(
            f'/api/v1/finance/incomes/{income.id}/set_allocations/',
            allocation_payload,
            format='json',
        )
        assert income_allocated.status_code == 200, income_allocated.json()
        expense_allocated = teacher_client.post(
            f'/api/v1/finance/expenses/{expense.id}/set_allocations/',
            allocation_payload,
            format='json',
        )
        assert expense_allocated.status_code == 200, expense_allocated.json()

        project_response = teacher_client.get(
            '/api/v1/finance/traceability/summary/?perspective=project'
        )
        assert project_response.status_code == 200, project_response.json()
        project_groups = {
            group['project']: group
            for group in data(project_response)['groups']
            if group['project'] in {project.id for project in projects}
        }
        assert len(project_groups) == 4
        assert Decimal(
            data(project_response)['metrics']['received_funds']
        ) == Decimal('1000')
        assert Decimal(
            data(project_response)['metrics']['actual_paid']
        ) == Decimal('1000')
        for project, share in zip(projects, shares):
            totals = project_groups[project.id]['totals']
            assert Decimal(totals['received_bonus']) == share
            assert Decimal(totals['received_income']) == share
            assert Decimal(totals['recorded_expense']) == share
            assert Decimal(totals['paid_expense']) == share
        assert sum(
            Decimal(group['totals']['received_income'])
            for group in project_groups.values()
        ) == Decimal('1000')
        assert sum(
            Decimal(group['totals']['paid_expense'])
            for group in project_groups.values()
        ) == Decimal('1000')

        competition_response = teacher_client.get(
            '/api/v1/finance/traceability/summary/?perspective=competition'
        )
        assert competition_response.status_code == 200
        event_group = next(
            group for group in data(competition_response)['groups']
            if group['event'] == event.id
        )
        assert len(event_group['entries']) == 4
        assert Decimal(event_group['totals']['received_income']) == Decimal('1000')
        assert Decimal(event_group['totals']['paid_expense']) == Decimal('1000')

        filtered = teacher_client.get(
            '/api/v1/finance/traceability/summary/',
            {'perspective': 'project', 'project': projects[1].id},
        )
        assert filtered.status_code == 200
        assert Decimal(data(filtered)['metrics']['received_funds']) == shares[1]
        assert Decimal(data(filtered)['metrics']['actual_paid']) == shares[1]
        trend = teacher_client.get(
            '/api/v1/finance/trends/',
            {'project': projects[1].id},
        )
        assert trend.status_code == 200
        assert Decimal(str(data(trend)['total_expense'])) == shares[1]

        detail = teacher_client.get(
            '/api/v1/finance/traceability/detail/',
            {'competition_entry': entries[1].id},
        )
        assert detail.status_code == 200
        assert Decimal(data(detail)['expenses'][0]['attributed_amount']) == shares[1]
        assert Decimal(data(detail)['incomes'][0]['attributed_amount']) == shares[1]

    def test_cross_project_allocations_reject_other_event_and_root_team(
        self,
        teacher_client,
        make_project,
    ):
        first_root = Team.objects.create(
            name='第一总团队',
            code='FINANCE-SCOPE-ROOT-A',
            owner=teacher_client.user,
        )
        second_root = Team.objects.create(
            name='第二总团队',
            code='FINANCE-SCOPE-ROOT-B',
            owner=teacher_client.user,
        )
        anchor = make_project(leader=teacher_client.user)
        same_root_project = make_project(leader=teacher_client.user)
        other_root_project = make_project(leader=teacher_client.user)
        anchor.teams.add(first_root)
        same_root_project.teams.add(first_root)
        other_root_project.teams.add(second_root)
        first_event = CompetitionEvent.objects.create(
            organization=first_root,
            name='第一届比赛',
            edition='2026',
            organizer='组委会',
        )
        other_event = CompetitionEvent.objects.create(
            organization=first_root,
            name='另一届比赛',
            edition='2027',
            organizer='组委会',
        )
        anchor_entry = make_shared_entry(anchor, first_event, 'A')
        wrong_event_entry = make_shared_entry(
            same_root_project,
            other_event,
            'B',
        )
        wrong_root_entry = make_shared_entry(
            other_root_project,
            first_event,
            'C',
        )
        income = FinanceIncome.objects.create(
            project=anchor,
            title='边界校验奖金',
            amount=Decimal('100'),
            income_type=FinanceIncome.IncomeType.BONUS,
            stage=FinanceIncome.Stage.EXPECTED,
            income_date='2026-07-29',
            recorded_by=teacher_client.user,
        )

        wrong_event = teacher_client.post(
            f'/api/v1/finance/incomes/{income.id}/set_allocations/',
            {'allocations': [
                {'competition_entry': anchor_entry.id, 'amount': '50'},
                {'competition_entry': wrong_event_entry.id, 'amount': '50'},
            ]},
            format='json',
        )
        assert wrong_event.status_code == 400
        assert '同一比赛届次' in str(wrong_event.json())

        wrong_root = teacher_client.post(
            f'/api/v1/finance/incomes/{income.id}/set_allocations/',
            {'allocations': [
                {'competition_entry': anchor_entry.id, 'amount': '50'},
                {'competition_entry': wrong_root_entry.id, 'amount': '50'},
            ]},
            format='json',
        )
        assert wrong_root.status_code == 400
        assert '同一总团队' in str(wrong_root.json())
