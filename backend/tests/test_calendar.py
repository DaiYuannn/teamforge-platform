"""
N46: 日历同步测试
- GET /api/v1/common/calendar/
"""
from datetime import timedelta
from django.utils import timezone

import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestCalendarSync:
    """日历同步测试"""

    def _make_task(self, make_task, **kwargs):
        return make_task(**kwargs)

    def test_calendar_returns_ical(self, member_client):
        """返回 iCal 格式日历"""
        resp = member_client.get('/api/v1/common/calendar/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['format'] == 'ical'
        assert 'BEGIN:VCALENDAR' in data['calendar']
        assert 'END:VCALENDAR' in data['calendar']

    def test_calendar_empty(self, member_client):
        """无任务时事件数为 0"""
        resp = member_client.get('/api/v1/common/calendar/')
        data = extract_data(resp)
        assert data['event_count'] == 0

    def test_calendar_with_task(self, member_client, make_task):
        """有截止日期的任务生成事件"""
        due = timezone.now() + timedelta(days=2)
        self._make_task(make_task, assignee=member_client.user, deadline=due, title='日历任务')
        resp = member_client.get('/api/v1/common/calendar/')
        data = extract_data(resp)
        assert data['event_count'] >= 1
        assert 'SUMMARY:日历任务' in data['calendar']

    def test_calendar_ical_format(self, member_client, make_task):
        """output=ical 返回 text/calendar"""
        due = timezone.now() + timedelta(days=1)
        make_task(assignee=member_client.user, deadline=due, title='原始格式')
        resp = member_client.get('/api/v1/common/calendar/?output=ical')
        assert resp.status_code == 200
        assert 'text/calendar' in resp.get('Content-Type', '')
        assert b'BEGIN:VCALENDAR' in resp.content

    def test_calendar_excludes_no_deadline(self, member_client, make_task):
        """无截止日期的任务不生成事件"""
        make_task(assignee=member_client.user, deadline=None, title='无截止')
        resp = member_client.get('/api/v1/common/calendar/')
        data = extract_data(resp)
        assert data['event_count'] == 0

    def test_calendar_unauthenticated_blocked(self, api_client):
        """未认证不可访问"""
        resp = api_client.get('/api/v1/common/calendar/')
        assert resp.status_code in (401, 403)

    def test_calendar_event_has_uid(self, member_client, make_task):
        """事件包含 UID"""
        due = timezone.now() + timedelta(days=3)
        make_task(assignee=member_client.user, deadline=due, title='UID任务')
        data = extract_data(member_client.get('/api/v1/common/calendar/'))
        assert 'UID:task-' in data['calendar']
