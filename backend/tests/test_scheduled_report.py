"""
N50 定时报表测试
- CRUD、run_now、activate/deactivate、频率计算
"""
import pytest
from django.utils import timezone

from apps.exports.custom_report_models import CustomReport
from apps.exports.scheduled_report_models import ScheduledReport

SCHEDULED_REPORT_URL = '/api/v1/exports/scheduled-reports/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.fixture
def make_report(member_client):
    """创建一个自定义报表用于关联"""
    resp = member_client.post('/api/v1/exports/custom-reports/', {
        'name': '关联报表', 'report_type': 'summary', 'config': {},
    }, format='json')
    return extract_data(resp)


@pytest.mark.api
@pytest.mark.django_db
class TestScheduledReport:
    """定时报表 API 测试"""

    def test_requires_auth(self, api_client):
        """未认证不可访问"""
        resp = api_client.get(SCHEDULED_REPORT_URL)
        assert resp.status_code == 401

    def test_create_scheduled_report(self, member_client, make_report, make_user):
        """创建定时报表"""
        recipient = make_user(email='recv@test.com')
        resp = member_client.post(SCHEDULED_REPORT_URL, {
            'report': make_report['id'],
            'frequency': 'daily',
            'is_active': True,
            'recipient_ids': [recipient.id],
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['report'] == make_report['id']
        assert data['frequency'] == 'daily'
        assert data['next_run'] is not None
        assert recipient.id in data['recipient_ids']

    def test_list_scheduled_reports(self, member_client, make_report):
        """列表"""
        report = CustomReport.objects.get(id=make_report['id'])
        ScheduledReport.objects.create(report=report, frequency='weekly')
        resp = member_client.get(SCHEDULED_REPORT_URL)
        assert resp.status_code == 200
        data = extract_data(resp)
        results = data.get('results', data) if isinstance(data, dict) else data
        assert len(results) >= 1

    def test_retrieve_scheduled_report(self, member_client, make_report):
        """详情"""
        report = CustomReport.objects.get(id=make_report['id'])
        schedule = ScheduledReport.objects.create(report=report, frequency='monthly')
        resp = member_client.get(f'{SCHEDULED_REPORT_URL}{schedule.id}/')
        assert resp.status_code == 200
        assert extract_data(resp)['id'] == schedule.id

    def test_update_scheduled_report(self, member_client, make_report):
        """更新"""
        report = CustomReport.objects.get(id=make_report['id'])
        schedule = ScheduledReport.objects.create(report=report, frequency='daily')
        resp = member_client.patch(f'{SCHEDULED_REPORT_URL}{schedule.id}/', {
            'frequency': 'weekly',
        }, format='json')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['frequency'] == 'weekly'

    def test_delete_scheduled_report(self, member_client, make_report):
        """删除"""
        report = CustomReport.objects.get(id=make_report['id'])
        schedule = ScheduledReport.objects.create(report=report, frequency='daily')
        resp = member_client.delete(f'{SCHEDULED_REPORT_URL}{schedule.id}/')
        assert resp.status_code in (200, 204)
        assert not ScheduledReport.objects.filter(id=schedule.id).exists()

    # ---------- run_now ----------

    def test_run_now(self, member_client, make_report):
        """手动触发运行"""
        report = CustomReport.objects.get(id=make_report['id'])
        schedule = ScheduledReport.objects.create(
            report=report, frequency='daily', next_run=timezone.now(),
        )
        assert schedule.last_run is None
        resp = member_client.post(f'{SCHEDULED_REPORT_URL}{schedule.id}/run_now/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['last_run'] is not None
        assert data['next_run'] is not None

    # ---------- activate / deactivate ----------

    def test_deactivate(self, member_client, make_report):
        """停用"""
        report = CustomReport.objects.get(id=make_report['id'])
        schedule = ScheduledReport.objects.create(
            report=report, frequency='daily', is_active=True,
        )
        resp = member_client.post(f'{SCHEDULED_REPORT_URL}{schedule.id}/deactivate/')
        assert resp.status_code == 200
        assert extract_data(resp)['is_active'] is False

    def test_activate(self, member_client, make_report):
        """启用"""
        report = CustomReport.objects.get(id=make_report['id'])
        schedule = ScheduledReport.objects.create(
            report=report, frequency='daily', is_active=False,
        )
        resp = member_client.post(f'{SCHEDULED_REPORT_URL}{schedule.id}/activate/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['is_active'] is True
        assert data['next_run'] is not None


@pytest.mark.model
@pytest.mark.django_db
class TestScheduledReportModel:
    """定时报表模型测试"""

    def test_str(self, member_client, make_report):
        report = CustomReport.objects.get(id=make_report['id'])
        schedule = ScheduledReport.objects.create(report=report, frequency='weekly')
        assert '关联报表' in str(schedule)
        assert '每周' in str(schedule)

    def test_default_active(self, make_report):
        report = CustomReport.objects.get(id=make_report['id'])
        schedule = ScheduledReport.objects.create(report=report, frequency='daily')
        assert schedule.is_active is True
        assert schedule.last_run is None

    def test_recipients(self, make_report, make_user):
        report = CustomReport.objects.get(id=make_report['id'])
        u1 = make_user(email='r1@test.com')
        u2 = make_user(email='r2@test.com')
        schedule = ScheduledReport.objects.create(report=report, frequency='daily')
        schedule.recipients.add(u1, u2)
        assert schedule.recipients.count() == 2
