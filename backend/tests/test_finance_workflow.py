"""收入流水、逐笔报销和预算自动汇总。"""
from decimal import Decimal

import pytest

from apps.finance.models import FinanceBudget, FinanceExpense, FinanceIncome


def response_data(response):
    payload = response.json()
    return payload.get('data', payload) if isinstance(payload, dict) else payload


@pytest.mark.api
@pytest.mark.django_db
class TestFinanceWorkflow:
    def test_income_flow_updates_budget_and_remains_readable(
        self, teacher_client, member_client, make_project
    ):
        project = make_project(leader=teacher_client.user)
        response = teacher_client.post('/api/v1/finance/incomes/', {
            'project': project.id,
            'title': '省赛奖金',
            'amount': '12000.00',
            'income_type': 'bonus',
            'income_date': '2026-07-20',
            'source': '赛事主办方',
            'reference_number': 'BONUS-001',
        }, format='json')
        assert response.status_code == 201, response.json()
        income = FinanceIncome.objects.get(project=project)
        assert income.recorded_by == teacher_client.user

        budget = FinanceBudget.objects.get(project=project)
        assert budget.bonus_amount == Decimal('12000.00')
        assert budget.other_income == Decimal('0.00')

        list_response = member_client.get(
            f'/api/v1/finance/incomes/?project={project.id}'
        )
        assert list_response.status_code == 200
        results = response_data(list_response)
        results = results.get('results', results)
        assert results[0]['reference_number'] == 'BONUS-001'

    def test_member_cannot_create_income(self, member_client, make_project):
        project = make_project()
        response = member_client.post('/api/v1/finance/incomes/', {
            'project': project.id,
            'title': '无权限收入',
            'amount': '100.00',
            'income_date': '2026-07-20',
        }, format='json')
        assert response.status_code == 403

    def test_reimbursement_transitions_drive_budget(
        self, teacher_client, make_project
    ):
        project = make_project(leader=teacher_client.user)
        FinanceIncome.objects.create(
            project=project,
            title='项目拨款',
            amount=Decimal('5000.00'),
            income_type=FinanceIncome.IncomeType.GRANT,
            income_date='2026-07-01',
            recorded_by=teacher_client.user,
        )
        created = teacher_client.post('/api/v1/finance/expenses/', {
            'project': project.id,
            'title': '材料采购',
            'amount': '600.00',
            'expense_date': '2026-07-21',
            'category': 'material',
        }, format='json')
        assert created.status_code == 201, created.json()
        expense_id = response_data(created)['id']
        expense = FinanceExpense.objects.get(pk=expense_id)
        assert expense.reimbursement_status == FinanceExpense.ReimbursementStatus.DRAFT

        submitted = teacher_client.post(
            f'/api/v1/finance/expenses/{expense_id}/submit_reimbursement/',
            {},
            format='json',
        )
        assert submitted.status_code == 200, submitted.json()
        budget = FinanceBudget.objects.get(project=project)
        assert budget.pending_reimbursement == Decimal('600.00')
        assert budget.used_amount == Decimal('0.00')

        reviewed = teacher_client.post(
            f'/api/v1/finance/expenses/{expense_id}/review_reimbursement/',
            {'approved': True, 'opinion': '票据齐全'},
            format='json',
        )
        assert reviewed.status_code == 200, reviewed.json()
        paid = teacher_client.post(
            f'/api/v1/finance/expenses/{expense_id}/mark_paid/',
            {'payment_method': '银行转账', 'payment_reference': 'PAY-2026-001'},
            format='json',
        )
        assert paid.status_code == 200, paid.json()

        expense.refresh_from_db()
        budget.refresh_from_db()
        assert expense.reimbursement_status == FinanceExpense.ReimbursementStatus.PAID
        assert expense.reviewer == teacher_client.user
        assert expense.paid_by == teacher_client.user
        assert expense.payment_reference == 'PAY-2026-001'
        assert budget.pending_reimbursement == Decimal('0.00')
        assert budget.used_amount == Decimal('600.00')
        assert budget.remaining_amount == Decimal('4400.00')

    def test_invalid_payment_transition_is_rejected(
        self, teacher_client, make_project
    ):
        project = make_project(leader=teacher_client.user)
        expense = FinanceExpense.objects.create(
            project=project,
            title='未审核支出',
            amount=Decimal('100.00'),
            expense_date='2026-07-20',
            spender=teacher_client.user,
        )
        response = teacher_client.post(
            f'/api/v1/finance/expenses/{expense.id}/mark_paid/',
            {'payment_method': '现金'},
            format='json',
        )
        assert response.status_code == 400
        expense.refresh_from_db()
        assert expense.reimbursement_status == FinanceExpense.ReimbursementStatus.DRAFT

    def test_soft_delete_paid_expense_recalculates_budget(
        self, teacher_client, make_project
    ):
        project = make_project(leader=teacher_client.user)
        FinanceIncome.objects.create(
            project=project,
            title='拨款',
            amount=Decimal('1000'),
            income_date='2026-07-01',
        )
        expense = FinanceExpense.objects.create(
            project=project,
            title='已付款支出',
            amount=Decimal('300'),
            expense_date='2026-07-10',
            reimbursement_status=FinanceExpense.ReimbursementStatus.PAID,
        )
        budget = FinanceBudget.objects.get(project=project)
        assert budget.used_amount == Decimal('300')

        response = teacher_client.delete(
            f'/api/v1/finance/expenses/{expense.id}/'
        )
        assert response.status_code == 200
        budget.refresh_from_db()
        assert budget.used_amount == Decimal('0')

    def test_planned_budget_uses_committed_expenses_not_drafts(
        self,
        teacher_client,
        make_project,
    ):
        project = make_project(leader=teacher_client.user)
        response = teacher_client.post('/api/v1/finance/budgets/', {
            'project': project.id,
            'planned_amount': '1000.00',
            'period': '2026',
        }, format='json')
        assert response.status_code == 201, response.json()

        for title, amount, reimbursement_status in [
            ('草稿不占用', '100.00', FinanceExpense.ReimbursementStatus.DRAFT),
            ('待审核占用', '300.00', FinanceExpense.ReimbursementStatus.PENDING),
            ('待打款占用', '250.00', FinanceExpense.ReimbursementStatus.APPROVED),
            ('已打款占用', '200.00', FinanceExpense.ReimbursementStatus.PAID),
            ('驳回不占用', '90.00', FinanceExpense.ReimbursementStatus.REJECTED),
        ]:
            FinanceExpense.objects.create(
                project=project,
                title=title,
                amount=amount,
                expense_date='2026-07-20',
                reimbursement_status=reimbursement_status,
            )

        budget = FinanceBudget.objects.get(project=project)
        assert budget.planned_amount == Decimal('1000.00')
        assert budget.used_amount == Decimal('200.00')
        assert budget.pending_reimbursement == Decimal('550.00')
        assert budget.committed_amount == Decimal('750.00')
        assert budget.available_amount == Decimal('250.00')
        assert budget.status == FinanceBudget.Status.NORMAL

        FinanceExpense.objects.create(
            project=project,
            title='追加待审核',
            amount='100.00',
            expense_date='2026-07-21',
            reimbursement_status=FinanceExpense.ReimbursementStatus.PENDING,
        )
        budget.refresh_from_db()
        assert budget.committed_amount == Decimal('850.00')
        assert budget.available_amount == Decimal('150.00')
        assert budget.status == FinanceBudget.Status.WARNING

        detail = teacher_client.get(f'/api/v1/finance/budgets/{budget.id}/')
        assert detail.status_code == 200
        payload = response_data(detail)
        assert payload['budget_basis'] == '1000.00'
        assert payload['committed_amount'] == '850.00'
        assert payload['available_amount'] == '150.00'

    def test_planned_budget_cannot_be_negative(
        self,
        teacher_client,
        make_project,
    ):
        project = make_project(leader=teacher_client.user)
        response = teacher_client.post('/api/v1/finance/budgets/', {
            'project': project.id,
            'planned_amount': '-1.00',
        }, format='json')

        assert response.status_code == 400
