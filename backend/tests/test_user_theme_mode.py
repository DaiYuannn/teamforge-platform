"""User-level light, dark, system, and scheduled theme preferences."""

import pytest
from django.core.exceptions import ValidationError

from apps.users.models import UserPreference


PREFERENCE_URL = '/api/v1/users/preference/'
PROFILE_URL = '/api/v1/users/me/'


def extract_data(response):
    body = response.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data')
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestUserThemeMode:
    def test_default_preference_follows_system_without_creating_record(
        self, member_client
    ):
        response = member_client.get(PREFERENCE_URL)

        assert response.status_code == 200
        data = extract_data(response)
        assert data['theme_mode'] == 'system'
        assert data['schedule_start'] == '19:00'
        assert data['schedule_end'] == '07:00'
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    @pytest.mark.parametrize('theme_mode', UserPreference.ThemeMode.values)
    def test_accepts_every_supported_theme_mode(self, member_client, theme_mode):
        response = member_client.patch(
            PREFERENCE_URL,
            {'theme_mode': theme_mode},
            format='json',
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert data['theme_mode'] == theme_mode
        preference = UserPreference.objects.get(user=member_client.user)
        assert preference.theme_mode == theme_mode

    @pytest.mark.parametrize(
        'theme_mode',
        ['auto', 'SYSTEM', '', None, 1, True, []],
    )
    def test_rejects_unknown_or_non_string_theme_modes(
        self, member_client, theme_mode
    ):
        response = member_client.patch(
            PREFERENCE_URL,
            {'theme_mode': theme_mode},
            format='json',
        )

        assert response.status_code == 400, response.json()
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    def test_accepts_schedule_time_boundaries(self, member_client):
        response = member_client.patch(
            PREFERENCE_URL,
            {
                'theme_mode': 'schedule',
                'schedule_start': '00:00',
                'schedule_end': '23:59',
            },
            format='json',
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert data['schedule_start'] == '00:00'
        assert data['schedule_end'] == '23:59'

    @pytest.mark.parametrize('field', ['schedule_start', 'schedule_end'])
    @pytest.mark.parametrize(
        'value',
        ['24:00', '23:60', '7:00', '07:0', '07:00:00', ' 07:00', None, 700],
    )
    def test_rejects_invalid_schedule_times(self, member_client, field, value):
        response = member_client.patch(
            PREFERENCE_URL,
            {field: value},
            format='json',
        )

        assert response.status_code == 400, response.json()
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    def test_schedule_mode_rejects_identical_start_and_end(self, member_client):
        response = member_client.patch(
            PREFERENCE_URL,
            {
                'theme_mode': 'schedule',
                'schedule_start': '08:00',
                'schedule_end': '08:00',
            },
            format='json',
        )

        assert response.status_code == 400, response.json()
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    def test_switching_existing_equal_schedule_to_schedule_is_rejected(
        self, member_client
    ):
        first_response = member_client.patch(
            PREFERENCE_URL,
            {
                'theme_mode': 'system',
                'schedule_start': '08:00',
                'schedule_end': '08:00',
            },
            format='json',
        )
        assert first_response.status_code == 200

        response = member_client.patch(
            PREFERENCE_URL,
            {'theme_mode': 'schedule'},
            format='json',
        )

        assert response.status_code == 400, response.json()
        preference = UserPreference.objects.get(user=member_client.user)
        assert preference.theme_mode == 'system'

    def test_theme_mode_and_legacy_color_preferences_are_independent(
        self, member_client
    ):
        member_client.patch(
            PREFERENCE_URL,
            {'primary_color': '#245C8A'},
            format='json',
        )

        response = member_client.patch(
            PREFERENCE_URL,
            {'theme_mode': 'dark'},
            format='json',
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert data['theme_mode'] == 'dark'
        assert data['theme_color'] == 'blue'
        assert data['primary_color'] == '#245c8a'

    def test_profile_exposes_persisted_schedule(self, member_client):
        member_client.patch(
            PREFERENCE_URL,
            {
                'theme_mode': 'schedule',
                'schedule_start': '20:15',
                'schedule_end': '06:45',
            },
            format='json',
        )

        response = member_client.get(PROFILE_URL)

        assert response.status_code == 200
        preferences = extract_data(response)['preferences']
        assert preferences['theme_mode'] == 'schedule'
        assert preferences['schedule_start'] == '20:15'
        assert preferences['schedule_end'] == '06:45'

    @pytest.mark.parametrize(
        'overrides',
        [
            {'theme_mode': 'auto'},
            {'schedule_start': '24:00'},
            {'schedule_end': '07:00:00'},
            {
                'theme_mode': 'schedule',
                'schedule_start': '08:00',
                'schedule_end': '08:00',
            },
        ],
    )
    def test_model_save_rejects_invalid_theme_settings(self, make_user, overrides):
        preference = UserPreference(user=make_user(), **overrides)

        with pytest.raises(ValidationError):
            preference.save()

        assert not UserPreference.objects.filter(user=preference.user).exists()

    def test_model_declares_supported_modes_and_defaults(self):
        mode_field = UserPreference._meta.get_field('theme_mode')
        assert {value for value, _ in mode_field.choices} == {
            'light', 'dark', 'system', 'schedule',
        }
        assert mode_field.default == 'system'
        assert UserPreference._meta.get_field('schedule_start').default == '19:00'
        assert UserPreference._meta.get_field('schedule_end').default == '07:00'
