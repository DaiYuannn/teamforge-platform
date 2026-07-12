"""
N21 经费预警测试
- 预算使用率 > 80% 预警, > 100% 超支
"""
import pytest
from decimal import Decimal

from apps.finance.models import FinanceBudget

ALERT_URL = '/api/v1/finance/alerts/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def make_budget(project, bonus=1000, other=0, used=0, pending=0, **extra):
    """创建经费预算的辅助函数"""
    return FinanceBudget.objects.create(
        project=project,
        bonus_amount=Decimal(str(bonus)),
        other_income=Decimal(str(other)),
        used_amount=Decimal(str(used)),
        pending_reimbursement=Decimal(str(pending)),
        **extra,
    )


@pytest.mark.api
@pytest.mark.django_db
class TestFinanceAlert:
    """经费预警 API 测试"""

    def test_alert_requires_auth(self, api_client):
        """未认证用户不能访问"""
        resp = api_client.get(ALERT_URL)
        assert resp.status_code == 401

    def test_alert_empty(self, member_client):
        """无数据时返回空"""
        resp = member_client.get(ALERT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['total_budgets'] == 0
        assert data['warning_count'] == 0

    def test_alert_normal(self, member_client, make_project):
        """正常预算（使用率 < 80%）"""
        project = make_project()
        make_budget(project, bonus=1000, used=500)
        resp = member_client.get(ALERT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['normal'] == 1
        assert data['summary']['warning'] == 0
        alert = data['alerts'][0]
        assert alert['alert_level'] == 'normal'

    def test_alert_warning(self, member_client, make_project):
        """预警预算（使用率 > 80%）"""
        project = make_project()
        make_budget(project, bonus=1000, used=850)
        resp = member_client.get(ALERT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['warning'] == 1
        alert = data['alerts'][0]
        assert alert['alert_level'] == 'warning'
        assert alert['usage_rate'] == 85.0

    def test_alert_danger(self, member_client, make_project):
        """超支预算（使用率 > 100%）"""
        project = make_project()
        make_budget(project, bonus=1000, used=1200)
        resp = member_client.get(ALERT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['danger'] == 1
        alert = data['alerts'][0]
        assert alert['alert_level'] == 'danger'
        assert alert['usage_rate'] == 120.0

    def test_alert_warnings_filter(self, member_client, make_project):
        """warnings 仅包含需要关注的项"""
        project = make_project()
        make_budget(project, bonus=1000, used=500)   # normal
        make_budget(project, bonus=1000, used=900)   # warning
        make_budget(project, bonus=1000, used=1100)  # danger
        resp = member_client.get(ALERT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['total_budgets'] == 3
        assert data['warning_count'] == 2
        assert len(data['warnings']) == 2

    def test_alert_filter_by_project(self, member_client, make_project):
        """按项目筛选"""
        p1 = make_project()
        p2 = make_project()
        make_budget(p1, bonus=1000, used=900)
        make_budget(p2, bonus=1000, used=500)
        resp = member_client.get(f'{ALERT_URL}?project={p1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['total_budgets'] == 1
        assert data['alerts'][0]['project_id'] == p1.id

    def test_alert_zero_income_with_expense(self, member_client, make_project):
        """无收入但有支出视为超支"""
        project = make_project()
        make_budget(project, bonus=0, used=100)
        resp = member_client.get(ALERT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        alert = data['alerts'][0]
        assert alert['alert_level'] == 'danger'

    def test_alert_usage_rate_calculation(self, member_client, make_project):
        """使用率计算正确（含其他收入）"""
        project = make_project()
        # total_income = 1000 + 500 = 1500, used = 1200 => 80%
        make_budget(project, bonus=1000, other=500, used=1200)
        resp = member_client.get(ALERT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        alert = data['alerts'][0]
        assert alert['usage_rate'] == 80.0
