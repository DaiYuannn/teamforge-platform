from decimal import Decimal

import pytest

from apps.members.models import FlexibleWorkSchedule


SCHEDULE_URL = '/api/v1/members/flexible-schedules/'


def response_data(response):
    payload = response.json()
    return payload.get('data', payload) if isinstance(payload, dict) else payload


@pytest.mark.api
@pytest.mark.django_db
class TestMemberAvailability:
    def test_member_records_date_ranges_and_capacity_days(self, member_client):
        response = member_client.post(SCHEDULE_URL, {
            'period_start': '2026-07-16',
            'period_end': '2026-07-31',
            'detail': {
                'availability_windows': [
                    {
                        'start_date': '2026-07-22',
                        'end_date': '2026-07-24',
                        'capacity_days': 1.5,
                        'note': '可以集中处理材料',
                    },
                    {
                        'start_date': '2026-07-29',
                        'end_date': '2026-07-29',
                        'capacity_days': 0.5,
                        'note': '',
                    },
                ],
            },
            'can_offline': True,
            'can_urgent': False,
            'is_saturated': False,
            'notes': '日期是可投入计划，不是实际工时统计',
        }, format='json')

        assert response.status_code == 201, response.json()
        schedule = FlexibleWorkSchedule.objects.get(user=member_client.user)
        assert schedule.detail['availability_windows'][0]['capacity_days'] == 1.5
        # work_hours 仅保留给旧报表兼容，页面以 2 天可投入量展示。
        assert schedule.work_hours == Decimal('16.0')
        assert response_data(response)['detail']['availability_windows'][1][
            'start_date'
        ] == '2026-07-29'

    @pytest.mark.parametrize(
        'window',
        [
            {
                'start_date': '2026-07-22',
                'end_date': '2026-07-24',
                'capacity_days': 0.3,
            },
            {
                'start_date': '2026-07-15',
                'end_date': '2026-07-20',
                'capacity_days': 1,
            },
            {
                'start_date': '2026-07-22',
                'end_date': '2026-07-23',
                'capacity_days': 3,
            },
        ],
    )
    def test_invalid_availability_window_is_rejected(
        self,
        member_client,
        window,
    ):
        response = member_client.post(SCHEDULE_URL, {
            'period_start': '2026-07-16',
            'period_end': '2026-07-31',
            'detail': {'availability_windows': [window]},
        }, format='json')

        assert response.status_code == 400

    def test_negative_legacy_hours_cannot_bypass_validation(self, member_client):
        response = member_client.post(SCHEDULE_URL, {
            'period_start': '2026-07-16',
            'period_end': '2026-07-31',
            'work_hours': '-1',
            'detail': {'availability_windows': []},
        }, format='json')

        assert response.status_code == 400
