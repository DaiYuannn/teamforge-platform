"""
N52 健康度评分测试
- 总分、分类评分、等级 A/B/C/D
"""
import pytest
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.tasks.models import Task
from apps.finance.models import FinanceBudget
from apps.projects.risk_models import ProjectRisk
from apps.projects.models import ProjectMember

HEALTH_SCORE_URL = '/api/v1/projects/health-score/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestHealthScore:
    """健康度评分 API 测试"""

    def test_requires_auth(self, api_client, make_project):
        """未认证不可访问"""
        project = make_project()
        resp = api_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 401

    def test_missing_project_id(self, member_client):
        """缺少 project_id"""
        resp = member_client.get(HEALTH_SCORE_URL)
        assert resp.status_code in (400, 404)

    def test_project_not_found(self, member_client):
        """项目不存在"""
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id=99999')
        assert resp.status_code in (400, 404)

    def test_basic_score_structure(self, member_client, make_project):
        """基本评分结构"""
        project = make_project()
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 0 <= data['overall_score'] <= 100
        assert data['grade'] in ['A', 'B', 'C', 'D']
        assert 'category_scores' in data
        # 五个评分维度
        categories = data['category_scores']
        assert 'task_completion' in categories
        assert 'schedule_adherence' in categories
        assert 'budget_utilization' in categories
        assert 'team_engagement' in categories
        assert 'risk_status' in categories

    def test_task_completion_score(self, member_client, make_project, make_task):
        """任务完成率影响评分"""
        project = make_project()
        make_task(project=project, status='done')
        make_task(project=project, status='done')
        make_task(project=project, status='todo')
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 完成率 2/3
        assert data['category_scores']['task_completion']['score'] > 50

    def test_no_tasks_full_score(self, member_client, make_project):
        """无任务时任务完成率满分"""
        project = make_project()
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['category_scores']['task_completion']['score'] == 100.0

    def test_budget_score(self, member_client, make_project):
        """经费使用评分"""
        project = make_project()
        FinanceBudget.objects.create(
            project=project,
            bonus_amount=Decimal('1000'),
            used_amount=Decimal('600'),
            status='normal',
        )
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 使用率 60% 在 50%-90% 区间，满分
        assert data['category_scores']['budget_utilization']['score'] == 100.0

    def test_budget_overrun_low_score(self, member_client, make_project):
        """经费超支评分低"""
        project = make_project()
        FinanceBudget.objects.create(
            project=project,
            bonus_amount=Decimal('1000'),
            used_amount=Decimal('1500'),
            status='abnormal',
        )
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['category_scores']['budget_utilization']['score'] <= 60

    def test_risk_status_score(self, member_client, make_project):
        """风险状态评分"""
        project = make_project()
        # 无开放风险，满分
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['category_scores']['risk_status']['score'] == 100.0

        # 添加开放风险
        ProjectRisk.objects.create(
            project=project, title='风险1', level='high', status='open',
        )
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        data = extract_data(resp)
        assert data['category_scores']['risk_status']['score'] < 100

    def test_team_engagement_score(self, member_client, make_project, make_user):
        """团队参与评分"""
        project = make_project()
        # 添加更多成员
        for i in range(3):
            u = make_user(email=f'team{i}@test.com')
            ProjectMember.objects.create(project=project, user=u, role_in_project='participant')
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['category_scores']['team_engagement']['score'] > 0

    def test_grade_mapping(self, member_client, make_project):
        """等级映射"""
        project = make_project(current_stage=13, status='closed')  # 已获奖/已关闭
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['grade'] in ['A', 'B', 'C', 'D']

    def test_closed_project_full_schedule(self, member_client, make_project):
        """已关闭项目进度满分"""
        project = make_project(status='closed')
        resp = member_client.get(f'{HEALTH_SCORE_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['category_scores']['schedule_adherence']['score'] == 100.0
