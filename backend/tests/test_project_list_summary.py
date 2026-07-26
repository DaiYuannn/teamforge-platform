from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.competitions.models import Competition
from apps.finance.models import FinanceBudget
from apps.projects.models import ProjectMember


def extract_results(response):
    payload = response.json()
    data = payload.get('data', payload)
    return data.get('results', data)


@pytest.mark.api
@pytest.mark.django_db
def test_project_list_includes_operational_summary(
    member_client,
    make_project,
    make_task,
    make_user,
):
    project = make_project()
    extra_member = make_user(email='project-summary-member@test.com')
    exited_member = make_user(email='project-summary-exited@test.com')
    ProjectMember.objects.create(project=project, user=extra_member)
    ProjectMember.objects.create(
        project=project,
        user=exited_member,
        status=ProjectMember.Status.EXITED,
    )
    make_task(project=project)
    make_task(project=project)
    Competition.objects.create(project=project, name='汇总测试比赛')
    Competition.objects.create(project=project, name='汇总测试比赛（二）')
    FinanceBudget.objects.create(
        project=project,
        bonus_amount=Decimal('1000.00'),
        other_income=Decimal('250.00'),
        used_amount=Decimal('400.00'),
    )
    FinanceBudget.objects.create(
        project=project,
        bonus_amount=Decimal('500.00'),
        used_amount=Decimal('125.00'),
        period='2026-08',
    )

    response = member_client.get('/api/v1/projects/')

    assert response.status_code == 200
    row = next(item for item in extract_results(response) if item['id'] == project.id)
    assert row['member_count'] == 2
    assert row['task_count'] == 2
    assert row['competition_count'] == 2
    assert Decimal(row['finance_balance']) == Decimal('1225.00')
    assert row['created_at']


@pytest.mark.api
@pytest.mark.django_db
def test_project_list_summary_uses_fixed_query_count(
    member_client,
    make_project,
    make_task,
):
    """项目数量增加时，预算汇总和关联计数不能退化成逐项目查询。"""
    for index in range(6):
        project = make_project(name=f'聚合查询项目 {index}')
        make_task(project=project)
        Competition.objects.create(project=project, name=f'聚合比赛 {index}')
        FinanceBudget.objects.create(
            project=project,
            bonus_amount=Decimal('1000.00'),
            used_amount=Decimal('100.00'),
            period=f'2026-{index + 1:02d}',
        )

    with CaptureQueriesContext(connection) as captured:
        response = member_client.get('/api/v1/projects/?page_size=100')

    assert response.status_code == 200
    assert len(extract_results(response)) >= 6
    assert len(captured) <= 6


@pytest.mark.api
@pytest.mark.django_db
def test_project_leader_can_edit_only_own_project_expense(
    member_client,
    make_project,
    make_finance,
):
    own_project = make_project(leader=member_client.user, name='负责人项目')
    other_project = make_project(name='其他负责人项目')
    own_expense = make_finance(project=own_project, title='可编辑支出')
    other_expense = make_finance(project=other_project, title='不可编辑支出')

    response = member_client.patch(
        f'/api/v1/finance/expenses/{own_expense.id}/',
        {'title': '负责人已更新'},
        format='json',
    )
    forbidden = member_client.patch(
        f'/api/v1/finance/expenses/{other_expense.id}/',
        {'title': '越权更新'},
        format='json',
    )

    assert response.status_code == 200
    assert response.json()['data']['title'] == '负责人已更新'
    assert forbidden.status_code == 403


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_external_project_summary_never_exposes_finance(
    api_client,
    make_user,
    make_project,
):
    external = make_user(
        email='external-project-summary@test.com',
        membership_status='external',
    )
    assigned_project = make_project(name='外部协作者获授权项目')
    hidden_project = make_project(name='外部协作者未授权项目')
    ProjectMember.objects.create(
        project=assigned_project,
        user=external,
        role_in_project=ProjectMember.RoleInProject.EXTERNAL,
        status=ProjectMember.Status.ACTIVE,
    )
    for project in (assigned_project, hidden_project):
        FinanceBudget.objects.create(
            project=project,
            bonus_amount=Decimal('10000.00'),
            used_amount=Decimal('2500.00'),
        )
    api_client.force_authenticate(user=external)

    with CaptureQueriesContext(connection) as captured:
        response = api_client.get('/api/v1/projects/?page_size=100')

    assert response.status_code == 200
    rows = extract_results(response)
    assert [row['id'] for row in rows] == [assigned_project.id]
    assert rows[0]['finance_balance'] is None
    assert not any(
        'finance_budgets' in query['sql'].lower()
        for query in captured.captured_queries
    )

    detail = api_client.get(f'/api/v1/projects/{assigned_project.id}/')
    assert detail.status_code == 200
    detail_payload = detail.json()
    detail_data = detail_payload.get('data', detail_payload)
    assert 'finance_balance' not in detail_data
    assert 'budgets' not in detail_data
