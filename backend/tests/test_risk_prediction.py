"""
N51 风险预测测试
- 风险评分、风险因子、改进建议
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from apps.tasks.models import Task
from apps.finance.models import FinanceBudget
from apps.projects.risk_models import ProjectRisk
from apps.projects.models import ProjectMember

RISK_PREDICTION_URL = '/api/v1/projects/risk-prediction/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestRiskPrediction:
    """风险预测 API 测试"""

    def test_requires_auth(self, api_client, make_project):
        """未认证不可访问"""
        project = make_project()
        resp = api_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 401

    def test_missing_project_id(self, member_client):
        """缺少 project_id"""
        resp = member_client.get(RISK_PREDICTION_URL)
        assert resp.status_code in (400, 404)

    def test_project_not_found(self, member_client):
        """项目不存在"""
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id=99999')
        assert resp.status_code in (400, 404)

    def test_low_risk_project(self, member_client, make_project):
        """低风险项目（无逾期、无超支、有成员）"""
        from django.utils import timezone
        project = make_project(last_leader_update=timezone.now())
        # make_project 默认已创建 leader 成员
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 0 <= data['risk_score'] <= 100
        assert data['risk_level'] == 'low'
        assert 'risk_factors' in data
        assert 'recommendations' in data

    def test_overdue_tasks_risk(self, member_client, make_project, make_task):
        """逾期任务风险"""
        project = make_project()
        # 创建逾期任务
        make_task(project=project, status='overdue')
        make_task(project=project, status='overdue')
        make_task(project=project, status='done')
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 应检测到逾期任务因子
        categories = [f['category'] for f in data['risk_factors']]
        assert 'overdue_tasks' in categories
        assert data['risk_score'] > 0

    def test_budget_overrun_risk(self, member_client, make_project):
        """预算超支风险"""
        from decimal import Decimal
        project = make_project()
        FinanceBudget.objects.create(
            project=project,
            bonus_amount=Decimal('1000'),
            used_amount=Decimal('1100'),
            status='abnormal',
        )
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        categories = [f['category'] for f in data['risk_factors']]
        assert 'budget_overrun' in categories

    def test_no_members_risk(self, member_client, make_project):
        """无成员风险"""
        project = make_project()
        # make_project 默认创建一个 leader 成员，先移除
        ProjectMember.objects.filter(project=project).delete()
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        categories = [f['category'] for f in data['risk_factors']]
        assert 'no_members' in categories

    def test_stale_update_risk(self, member_client, make_project):
        """长期未更新风险"""
        project = make_project(last_leader_update=timezone.now() - timedelta(days=30))
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        categories = [f['category'] for f in data['risk_factors']]
        assert 'stale_update' in categories

    def test_open_risks_factor(self, member_client, make_project):
        """未关闭高风险因子"""
        project = make_project()
        ProjectRisk.objects.create(
            project=project, title='高风险A', level='critical', status='open',
        )
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        categories = [f['category'] for f in data['risk_factors']]
        assert 'open_risks' in categories

    def test_recommendations_generated(self, member_client, make_project, make_task):
        """改进建议生成"""
        project = make_project()
        make_task(project=project, status='overdue')
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['recommendations']) > 0

    def test_risk_score_in_range(self, member_client, make_project):
        """风险评分在 0-100 范围内"""
        project = make_project()
        resp = member_client.get(f'{RISK_PREDICTION_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert 0 <= data['risk_score'] <= 100
