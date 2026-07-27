"""
N49 自定义报表测试
- CRUD、generate（根据 config 生成数据）、报表类型
"""
import pytest
from datetime import datetime
from django.utils import timezone
from rest_framework.test import APIClient

from apps.exports.custom_report_models import CustomReport
from apps.tasks.models import Task
from apps.finance.models import FinanceExpense
from datetime import date

CUSTOM_REPORT_URL = '/api/v1/exports/custom-reports/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestCustomReport:
    """自定义报表 API 测试"""

    def test_requires_auth(self, api_client):
        """未认证不可访问"""
        resp = api_client.get(CUSTOM_REPORT_URL)
        assert resp.status_code == 401

    def test_create_report(self, member_client):
        """创建报表"""
        resp = member_client.post(CUSTOM_REPORT_URL, {
            'name': '任务汇总报表',
            'description': '按状态汇总任务',
            'report_type': 'summary',
            'config': {
                'data_source': 'task',
                'group_by': 'status',
                'chart_type': 'pie',
            },
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['name'] == '任务汇总报表'
        assert data['report_type'] == 'summary'
        assert data['created_by'] == member_client.user.id

    def test_list_reports(self, member_client):
        """列表"""
        CustomReport.objects.create(
            name='报表A', report_type='summary', config={},
            created_by=member_client.user,
        )
        resp = member_client.get(CUSTOM_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) >= 1

    def test_member_cannot_read_or_generate_another_members_report(
        self, member_client, make_user
    ):
        owner = make_user(email='report-owner@test.com')
        report = CustomReport.objects.create(
            name='他人私有报表',
            report_type='summary',
            config={'data_source': 'project'},
            created_by=owner,
        )

        listed = member_client.get(CUSTOM_REPORT_URL)
        detail = member_client.get(f'{CUSTOM_REPORT_URL}{report.id}/')
        generated = member_client.post(
            f'{CUSTOM_REPORT_URL}{report.id}/generate/'
        )

        results = extract_data(listed)
        if isinstance(results, dict):
            results = results.get('results', [])
        assert report.id not in {item['id'] for item in results}
        assert detail.status_code == 404
        assert generated.status_code == 404

    def test_external_member_cannot_access_custom_reports(
        self, make_user
    ):
        from apps.users.models import User

        external = make_user(
            email='external-report@test.com',
            membership_status=User.MembershipStatus.EXTERNAL,
        )
        client = APIClient()
        client.force_authenticate(user=external)

        assert client.get(CUSTOM_REPORT_URL).status_code == 403

    def test_retrieve_report(self, member_client):
        """详情"""
        report = CustomReport.objects.create(
            name='详情报表', report_type='trend', config={'k': 'v'},
            created_by=member_client.user,
        )
        resp = member_client.get(f'{CUSTOM_REPORT_URL}{report.id}/')
        assert resp.status_code == 200
        assert extract_data(resp)['id'] == report.id

    def test_update_report(self, member_client):
        """更新"""
        report = CustomReport.objects.create(
            name='原报表', report_type='summary', config={},
            created_by=member_client.user,
        )
        resp = member_client.patch(f'{CUSTOM_REPORT_URL}{report.id}/', {
            'name': '更新报表',
            'config': {'data_source': 'finance'},
        }, format='json')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['name'] == '更新报表'
        assert data['config']['data_source'] == 'finance'

    def test_delete_report(self, member_client):
        """删除"""
        report = CustomReport.objects.create(
            name='待删', report_type='summary', config={},
            created_by=member_client.user,
        )
        resp = member_client.delete(f'{CUSTOM_REPORT_URL}{report.id}/')
        assert resp.status_code in (200, 204)
        assert not CustomReport.objects.filter(id=report.id).exists()

    # ---------- generate ----------

    def test_generate_task_report(self, member_client, make_project, make_task):
        """生成任务报表数据"""
        project = make_project()
        make_task(project=project, status='done')
        make_task(project=project, status='done')
        make_task(project=project, status='todo')

        report = CustomReport.objects.create(
            name='任务报表', report_type='summary',
            config={'data_source': 'task', 'group_by': 'status', 'chart_type': 'bar'},
            created_by=member_client.user,
        )
        resp = member_client.post(f'{CUSTOM_REPORT_URL}{report.id}/generate/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['data']['data_source'] == 'task'
        assert data['data']['summary']['total'] == 3
        assert data['data']['summary']['done'] == 2
        assert data['data']['summary']['todo'] == 1
        assert len(data['data']['groups']) > 0

    def test_generate_finance_report(self, member_client, make_project, make_finance):
        """生成经费报表数据"""
        project = make_project()
        make_finance(project=project, amount=100, category='material')
        make_finance(project=project, amount=200, category='travel')

        report = CustomReport.objects.create(
            name='经费报表', report_type='summary',
            config={'data_source': 'finance', 'group_by': 'category', 'chart_type': 'pie'},
            created_by=member_client.user,
        )
        resp = member_client.post(f'{CUSTOM_REPORT_URL}{report.id}/generate/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['data']['summary']['total_amount'] == 300.0
        assert len(data['data']['groups']) >= 2

    def test_generate_project_report(self, member_client, make_project):
        """生成项目报表数据"""
        make_project(status='active')
        make_project(status='closed')

        report = CustomReport.objects.create(
            name='项目报表', report_type='comparison',
            config={'data_source': 'project', 'group_by': 'status', 'chart_type': 'table'},
            created_by=member_client.user,
        )
        resp = member_client.post(f'{CUSTOM_REPORT_URL}{report.id}/generate/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['data']['summary']['total'] >= 2

    def test_generate_competition_report(self, member_client, make_project):
        """生成比赛报表数据"""
        from apps.competitions.models import Competition
        project = make_project()
        Competition.objects.create(
            project=project, name='校赛A', level='school', is_awarded=True,
        )
        Competition.objects.create(
            project=project, name='省赛B', level='province',
        )

        report = CustomReport.objects.create(
            name='比赛报表', report_type='summary',
            config={'data_source': 'competition', 'group_by': 'level', 'chart_type': 'bar'},
            created_by=member_client.user,
        )
        resp = member_client.post(f'{CUSTOM_REPORT_URL}{report.id}/generate/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['data']['summary']['total'] == 2
        assert data['data']['summary']['awarded'] == 1

    def test_generate_with_filter(self, member_client, make_project, make_task):
        """带过滤器的报表生成"""
        p1 = make_project()
        p2 = make_project()
        make_task(project=p1, status='done')
        make_task(project=p2, status='done')

        report = CustomReport.objects.create(
            name='过滤报表', report_type='summary',
            config={
                'data_source': 'task', 'group_by': 'status',
                'filters': {'project_id': p1.id},
            },
            created_by=member_client.user,
        )
        resp = member_client.post(f'{CUSTOM_REPORT_URL}{report.id}/generate/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['data']['summary']['total'] == 1

    def test_generate_unknown_source(self, member_client):
        """未知数据源"""
        report = CustomReport.objects.create(
            name='未知源', report_type='summary',
            config={'data_source': 'unknown'},
            created_by=member_client.user,
        )
        resp = member_client.post(f'{CUSTOM_REPORT_URL}{report.id}/generate/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert 'message' in data['data']['summary']

    def test_comparison_report_adds_rank_share_and_average(
        self, member_client, make_project, make_task
    ):
        first = make_project(name='Comparison A')
        second = make_project(name='Comparison B')
        make_task(project=first)
        make_task(project=first)
        make_task(project=second)
        report = CustomReport.objects.create(
            name='Comparison semantics', report_type='comparison',
            config={
                'data_source': 'task', 'group_by': 'project',
                'chart_type': 'bar',
            },
            created_by=member_client.user,
        )

        response = member_client.post(f'{CUSTOM_REPORT_URL}{report.id}/generate/')

        assert response.status_code == 200, response.json()
        data = extract_data(response)['data']
        assert data['report_type'] == 'comparison'
        assert data['groups'][0]['rank'] == 1
        assert data['groups'][0]['share_percent'] > data['groups'][1]['share_percent']
        assert data['comparison']['average'] == 1.5

    def test_trend_report_groups_records_by_month(
        self, member_client, make_project, make_task
    ):
        project = make_project()
        january = make_task(project=project)
        february = make_task(project=project)
        from apps.tasks.models import Task
        Task.objects.filter(pk=january.pk).update(
            created_at=timezone.make_aware(datetime(2026, 1, 15, 9, 0)),
        )
        Task.objects.filter(pk=february.pk).update(
            created_at=timezone.make_aware(datetime(2026, 2, 15, 9, 0)),
        )
        report = CustomReport.objects.create(
            name='Trend semantics', report_type='trend',
            config={
                'data_source': 'task', 'group_by': 'status',
                'chart_type': 'line', 'filters': {'project_id': project.id},
            },
            created_by=member_client.user,
        )

        response = member_client.post(f'{CUSTOM_REPORT_URL}{report.id}/generate/')

        assert response.status_code == 200, response.json()
        data = extract_data(response)['data']
        assert data['report_type'] == 'trend'
        assert data['group_by'] == 'month'
        assert [group['label'] for group in data['groups']] == ['2026-01', '2026-02']


@pytest.mark.model
@pytest.mark.django_db
class TestCustomReportModel:
    """自定义报表模型测试"""

    def test_str(self):
        report = CustomReport.objects.create(
            name='模型测试', report_type='summary', config={},
        )
        assert str(report) == '模型测试'

    def test_default_config(self):
        report = CustomReport.objects.create(name='默认', report_type='trend')
        assert report.config == {}
        assert report.is_scheduled is False
        assert report.schedule_cron == ''

    def test_scheduled_report(self, make_user):
        user = make_user()
        report = CustomReport.objects.create(
            name='定时报表', report_type='summary',
            is_scheduled=True, schedule_cron='0 8 * * *',
            created_by=user,
        )
        assert report.is_scheduled is True
        assert report.schedule_cron == '0 8 * * *'
