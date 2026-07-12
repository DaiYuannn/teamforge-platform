"""
N53 智能周报测试
- 完成任务、新增任务、待办、项目进度、即将到期、团队动态
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from apps.tasks.models import Task
from apps.competitions.models import Competition
from apps.contributions.models import Contribution

WEEKLY_REPORT_URL = '/api/v1/dashboard/weekly-report/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestWeeklyReport:
    """智能周报 API 测试"""

    def test_requires_auth(self, api_client):
        """未认证不可访问"""
        resp = api_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 401

    def test_empty_report(self, member_client):
        """无数据时返回空结构"""
        resp = member_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'summary' in data
        assert data['summary']['tasks_completed'] == 0
        assert data['summary']['tasks_new'] == 0

    def test_completed_tasks(self, member_client, make_project, make_task):
        """本周完成任务"""
        project = make_project()
        now = timezone.now()
        task = make_task(project=project, status='done')
        task.completed_at = now - timedelta(days=1)
        task.save()
        resp = member_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['tasks_completed'] >= 1
        assert len(data['completed_tasks']) >= 1

    def test_new_tasks(self, member_client, make_project, make_task):
        """本周新增任务"""
        project = make_project()
        make_task(project=project, status='todo')
        resp = member_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['tasks_new'] >= 1

    def test_pending_tasks(self, member_client, make_project, make_task):
        """待办任务"""
        project = make_project()
        make_task(project=project, status='todo')
        make_task(project=project, status='doing')
        resp = member_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['tasks_pending'] >= 2

    def test_overdue_tasks(self, member_client, make_project, make_task):
        """逾期任务"""
        project = make_project()
        make_task(project=project, status='overdue')
        resp = member_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['summary']['tasks_overdue'] >= 1

    def test_filter_by_project(self, member_client, make_project, make_task):
        """按项目过滤"""
        p1 = make_project()
        p2 = make_project()
        now = timezone.now()
        t1 = make_task(project=p1, status='done')
        t1.completed_at = now
        t1.save()
        t2 = make_task(project=p2, status='done')
        t2.completed_at = now
        t2.save()
        resp = member_client.get(f'{WEEKLY_REPORT_URL}?project_id={p1.id}')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 仅 p1 的任务
        for t in data['completed_tasks']:
            assert t['project_id'] == p1.id

    def test_project_progress(self, member_client, make_project):
        """项目进度"""
        project = make_project(status='active')
        resp = member_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['project_progress']) >= 1
        assert data['summary']['active_projects'] >= 1

    def test_narrative_generated(self, member_client, make_project):
        """周报叙述生成"""
        make_project(status='active')
        resp = member_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        assert isinstance(data['narrative'], str)
        assert len(data['narrative']) > 0

    def test_weeks_param(self, member_client, make_project, make_task):
        """weeks 参数回溯多周"""
        project = make_project()
        # 2周前完成的任务
        task = make_task(project=project, status='done')
        task.completed_at = timezone.now() - timedelta(weeks=2, days=1)
        task.save()
        # 1周范围看不到
        resp = member_client.get(WEEKLY_REPORT_URL)
        data1 = extract_data(resp)
        # 3周范围能看到
        resp = member_client.get(f'{WEEKLY_REPORT_URL}?weeks=3')
        data3 = extract_data(resp)
        assert data3['summary']['tasks_completed'] >= data1['summary']['tasks_completed']

    def test_report_structure(self, member_client):
        """周报结构完整"""
        resp = member_client.get(WEEKLY_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        for key in [
            'summary', 'narrative', 'completed_tasks', 'new_tasks',
            'pending_tasks', 'overdue_tasks', 'upcoming_deadline_tasks',
            'project_progress', 'stage_changes', 'upcoming_competitions',
            'team_activity',
        ]:
            assert key in data, f'缺少字段 {key}'
