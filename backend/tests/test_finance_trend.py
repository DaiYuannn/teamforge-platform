"""
N22 经费趋势分析测试
- 月度支出趋势、类别分布
"""
import pytest
from datetime import date

from apps.finance.models import FinanceExpense

TREND_URL = '/api/v1/finance/trends/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def make_expense(project, amount, expense_date, category='other', **extra):
    """创建经费明细的辅助函数"""
    defaults = {
        'title': '测试支出',
        'amount': amount,
        'expense_date': expense_date,
        'category': category,
        # 趋势图只统计已经形成实际团队支出的记录。
        'reimbursement_status': FinanceExpense.ReimbursementStatus.NOT_REQUIRED,
    }
    defaults.update(extra)
    return FinanceExpense.objects.create(project=project, **defaults)


@pytest.mark.api
@pytest.mark.django_db
class TestFinanceTrend:
    """经费趋势分析 API 测试"""

    def test_trend_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.get(TREND_URL)
        assert resp.status_code == 401

    def test_trend_empty(self, member_client):
        """无数据时返回零值"""
        resp = member_client.get(TREND_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total_expense'] == 0
        assert len(data['monthly_trend']) == 0

    def test_trend_monthly(self, member_client, make_project):
        """月度趋势"""
        project = make_project()
        make_expense(project, 100, date(2026, 1, 15))
        make_expense(project, 200, date(2026, 1, 20))
        make_expense(project, 300, date(2026, 2, 10))
        resp = member_client.get(TREND_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        monthly = {m['month']: m['amount'] for m in data['monthly_trend']}
        assert monthly['2026-01'] == 300.0
        assert monthly['2026-02'] == 300.0
        assert data['total_expense'] == 600.0

    def test_trend_category_breakdown(self, member_client, make_project):
        """类别分布"""
        project = make_project()
        make_expense(project, 100, date(2026, 1, 1), category='material')
        make_expense(project, 200, date(2026, 1, 1), category='equipment')
        make_expense(project, 50, date(2026, 1, 1), category='material')
        resp = member_client.get(TREND_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['category_breakdown']['material']['amount'] == 150.0
        assert data['category_breakdown']['equipment']['amount'] == 200.0

    def test_trend_category_percentage(self, member_client, make_project):
        """类别占比"""
        project = make_project()
        make_expense(project, 300, date(2026, 1, 1), category='material')
        make_expense(project, 100, date(2026, 1, 1), category='travel')
        resp = member_client.get(TREND_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['category_percentage']['material'] == 75.0
        assert data['category_percentage']['travel'] == 25.0

    def test_trend_filter_by_project(self, member_client, make_project):
        """按项目筛选"""
        p1 = make_project()
        p2 = make_project()
        make_expense(p1, 100, date(2026, 1, 1))
        make_expense(p2, 200, date(2026, 1, 1))
        resp = member_client.get(f'{TREND_URL}?project={p1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total_expense'] == 100.0

    def test_trend_sorted_by_month(self, member_client, make_project):
        """月度趋势按月份排序"""
        project = make_project()
        make_expense(project, 100, date(2026, 3, 1))
        make_expense(project, 100, date(2026, 1, 1))
        make_expense(project, 100, date(2026, 2, 1))
        resp = member_client.get(TREND_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        months = [m['month'] for m in data['monthly_trend']]
        assert months == sorted(months)
