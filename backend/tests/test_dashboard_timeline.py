"""统一时间线筛选契约测试。"""
from datetime import date

from apps.competitions.models import Competition
from apps.contributions.models import Contribution
from apps.projects.models import Project
from apps.users.models import User
from django.test import TestCase
from rest_framework.test import APIClient


TIMELINE_URL = '/api/v1/dashboard/timeline/'


def extract_data(response):
    body = response.json()
    return body.get('data', body)


class TestDashboardTimelineFiltering(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='timeline-filter@test.com',
            username='timeline-filter@test.com',
            password='TestPass123!',
            name='时间线测试用户',
        )
        cls.project = Project.objects.create(
            name='时间线测试项目',
            code='TIMELINE-TEST',
            leader=cls.user,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_keeps_single_exact_event_type_filter(self):
        Competition.objects.create(
            project=self.project,
            name='时间线筛选测试比赛',
            register_date=date(2026, 3, 1),
            result_date=date(2026, 6, 1),
        )

        response = self.client.get(TIMELINE_URL, {
            'project_id': self.project.id,
            'event_type': 'competition_result',
        })

        assert response.status_code == 200
        data = extract_data(response)
        assert data['total'] == 1
        assert [event['type'] for event in data['events']] == [
            'competition_result',
        ]

    def test_accepts_comma_separated_event_types(self):
        Competition.objects.create(
            project=self.project,
            name='多类型筛选测试比赛',
            register_date=date(2026, 3, 1),
            result_date=date(2026, 6, 1),
        )
        Contribution.objects.create(
            project=self.project,
            user=self.user,
            content='完成比赛材料整理',
        )

        response = self.client.get(TIMELINE_URL, {
            'project_id': self.project.id,
            'event_type': ' competition_register, contribution ',
        })

        assert response.status_code == 200
        data = extract_data(response)
        assert data['total'] == 2
        assert {event['type'] for event in data['events']} == {
            'competition_register',
            'contribution',
        }

    def test_date_range_filters_every_competition_business_date(self):
        Competition.objects.create(
            project=self.project,
            name='跨日期比赛',
            register_date=date(2026, 3, 1),
            defense_date=date(2026, 5, 15),
            result_date=date(2026, 6, 1),
        )

        response = self.client.get(TIMELINE_URL, {
            'project_id': self.project.id,
            'start_date': '2026-05-01',
            'end_date': '2026-05-31',
            'event_type': (
                'competition_register,competition_defense,competition_result'
            ),
        })

        assert response.status_code == 200
        data = extract_data(response)
        assert [event['type'] for event in data['events']] == [
            'competition_defense',
        ]

    def test_invalid_limit_falls_back_instead_of_raising_server_error(self):
        response = self.client.get(TIMELINE_URL, {'limit': 'not-a-number'})

        assert response.status_code == 200
