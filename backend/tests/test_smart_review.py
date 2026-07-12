"""
N54 智能复盘测试
- 成果总结、问题领域、时间线分析、团队表现
"""
import pytest
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.tasks.models import Task
from apps.finance.models import FinanceBudget
from apps.competitions.models import Competition
from apps.projects.risk_models import ProjectRisk
from apps.projects.models import ProjectMember, ProjectStageLog

SMART_REVIEW_URL = '/api/v1/projects/smart-review/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestSmartReview:
    """智能复盘 API 测试"""

    def test_requires_auth(self, api_client, make_project):
        """未认证不可访问"""
        project = make_project()
        resp = api_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 401

    def test_missing_project_id(self, member_client):
        """缺少 project_id"""
        resp = member_client.get(SMART_REVIEW_URL)
        assert resp.status_code in (400, 404)

    def test_project_not_found(self, member_client):
        """项目不存在"""
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id=99999')
        assert resp.status_code in (400, 404)

    def test_basic_structure(self, member_client, make_project):
        """基本结构"""
        project = make_project()
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        for key in [
            'summary', 'achievements', 'problem_areas', 'lessons',
            'improvements', 'task_statistics', 'finance_summary',
            'team_performance', 'timeline',
        ]:
            assert key in data, f'缺少字段 {key}'

    def test_task_statistics(self, member_client, make_project, make_task):
        """任务统计"""
        project = make_project()
        make_task(project=project, status='done')
        make_task(project=project, status='done')
        make_task(project=project, status='overdue')
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['task_statistics']['total'] == 3
        assert data['task_statistics']['done'] == 2
        assert data['task_statistics']['overdue'] == 1

    def test_achievements(self, member_client, make_project):
        """比赛成果"""
        project = make_project()
        Competition.objects.create(
            project=project, name='校赛', level='school',
            is_awarded=True, award_level='一等奖',
        )
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['achievements']) >= 1
        assert data['achievements'][0]['award_level'] == '一等奖'

    def test_problem_areas_overdue(self, member_client, make_project, make_task):
        """问题领域 - 逾期"""
        project = make_project()
        make_task(project=project, status='overdue')
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        areas = [p['area'] for p in data['problem_areas']]
        assert 'task_overdue' in areas

    def test_problem_areas_budget(self, member_client, make_project):
        """问题领域 - 预算超支"""
        project = make_project()
        FinanceBudget.objects.create(
            project=project,
            bonus_amount=Decimal('1000'),
            used_amount=Decimal('1500'),
        )
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        areas = [p['area'] for p in data['problem_areas']]
        assert 'budget_overrun' in areas

    def test_lessons_generated(self, member_client, make_project, make_task):
        """经验教训生成"""
        project = make_project()
        make_task(project=project, status='overdue')
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['lessons']) > 0

    def test_improvements_generated(self, member_client, make_project, make_task):
        """改进建议生成"""
        project = make_project()
        make_task(project=project, status='overdue')
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['improvements']) > 0

    def test_team_performance(self, member_client, make_project, make_task, make_user):
        """团队表现"""
        project = make_project()
        member = make_user(email='member_tp@test.com')
        ProjectMember.objects.create(
            project=project, user=member, role_in_project='participant',
        )
        make_task(project=project, assignee=member, status='done')
        make_task(project=project, assignee=member, status='done')
        make_task(project=project, assignee=member, status='todo')
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 应包含项目成员（leader + 新增 member）
        assert len(data['team_performance']) >= 2

    def test_timeline(self, member_client, make_project):
        """时间线分析"""
        project = make_project()
        ProjectStageLog.objects.create(
            project=project, from_stage=1, to_stage=2, note='立项',
        )
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['timeline']) >= 1

    def test_summary_text(self, member_client, make_project):
        """总结文本生成"""
        project = make_project()
        resp = member_client.get(f'{SMART_REVIEW_URL}?project_id={project.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert isinstance(data['summary'], str)
        assert project.name in data['summary']
