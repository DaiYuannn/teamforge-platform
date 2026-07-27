"""Account-level primary color API and persistence contracts."""
from importlib import import_module

import pytest
from django.apps import apps as django_apps

from apps.users.models import UserPreference


PREFERENCE_URL = '/api/v1/users/preference/'
PROFILE_URL = '/api/v1/users/me/'
LOGIN_URL = '/api/v1/auth/login/'


def extract_data(response):
    body = response.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data')
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestUserPrimaryColor:
    @staticmethod
    def assert_complete_preferences(preferences, expected_color):
        assert preferences == {
            'dashboard_layout': {},
            'theme_color': UserPreference.theme_for_primary_color(expected_color),
            'primary_color': expected_color,
            'theme_mode': UserPreference.DEFAULT_THEME_MODE,
            'schedule_start': UserPreference.DEFAULT_SCHEDULE_START,
            'schedule_end': UserPreference.DEFAULT_SCHEDULE_END,
            'default_landing': 'dashboard',
            'sidebar_collapsed': False,
            'notification_sound': True,
            'language': 'zh-CN',
            'items_per_page': 20,
            'default_scope': 'mine',
            'sidebar_order': [],
            'favorite_routes': [],
            'saved_filters': {},
            'notification_preferences': {},
        }

    def test_default_color_is_safe_without_creating_preference(self, member_client):
        response = member_client.get(PREFERENCE_URL)

        assert response.status_code == 200
        data = extract_data(response)
        assert data['primary_color'] == '#176b73'
        assert data['theme_color'] == 'blue'
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    def test_patch_primary_color_persists_for_current_user(self, member_client):
        response = member_client.patch(
            PREFERENCE_URL, {'primary_color': '#2F6F4E'}, format='json'
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert data['primary_color'] == '#2f6f4e'
        assert data['theme_color'] == 'green'
        preference = UserPreference.objects.get(user=member_client.user)
        assert preference.theme_color == 'green'
        assert preference.primary_color == '#2f6f4e'

    def test_patch_custom_primary_color_persists_for_current_user(self, member_client):
        response = member_client.patch(
            PREFERENCE_URL, {'primary_color': '#245C8A'}, format='json'
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert data['primary_color'] == '#245c8a'
        preference = UserPreference.objects.get(user=member_client.user)
        assert preference.primary_color == '#245c8a'

    def test_legacy_theme_color_remains_compatible(self, member_client):
        response = member_client.put(
            PREFERENCE_URL, {'theme_color': 'purple'}, format='json'
        )

        assert response.status_code == 200, response.json()
        data = extract_data(response)
        assert data['theme_color'] == 'purple'
        assert data['primary_color'] == '#6f5a86'

    @pytest.mark.parametrize(
        'value',
        ('red', '#fff', '#00000g', 'var(--color-primary)', 'url(javascript:alert(1))'),
    )
    def test_rejects_malformed_or_unsafe_color_values(self, member_client, value):
        response = member_client.patch(
            PREFERENCE_URL, {'primary_color': value}, format='json'
        )

        assert response.status_code == 400
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    def test_primary_color_is_authoritative_over_legacy_theme_value(self, member_client):
        response = member_client.patch(PREFERENCE_URL, {
            'theme_color': 'orange',
            'primary_color': '#2f6f4e',
        }, format='json')

        assert response.status_code == 200
        data = extract_data(response)
        assert data['theme_color'] == 'green'
        assert data['primary_color'] == '#2f6f4e'

    def test_profile_exposes_default_and_persisted_primary_color(self, member_client):
        default_response = member_client.get(PROFILE_URL)
        self.assert_complete_preferences(
            extract_data(default_response)['preferences'],
            '#176b73',
        )

        member_client.patch(
            PREFERENCE_URL, {'primary_color': '#9a6238'}, format='json'
        )
        response = member_client.get(PROFILE_URL)

        assert response.status_code == 200
        self.assert_complete_preferences(
            extract_data(response)['preferences'],
            '#9a6238',
        )

    def test_profile_patch_cannot_write_nested_preferences(self, member_client):
        response = member_client.patch(PROFILE_URL, {
            'preferences': {'primary_color': '#9a6238'},
        }, format='json')

        assert response.status_code == 200
        self.assert_complete_preferences(
            extract_data(response)['preferences'],
            '#176b73',
        )
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    def test_login_response_includes_persisted_primary_color(
        self, api_client, make_user
    ):
        user = make_user(email='primary-login@test.com')
        UserPreference.objects.create(user=user, theme_color='purple')

        response = api_client.post(LOGIN_URL, {
            'email': user.email,
            'password': 'TestPass123!',
        }, format='json')

        assert response.status_code == 200, response.json()
        self.assert_complete_preferences(
            extract_data(response)['user']['preferences'],
            '#6f5a86',
        )

    def test_model_declares_only_supported_theme_keys(self):
        field = UserPreference._meta.get_field('theme_color')
        assert {value for value, _ in field.choices} == {
            'blue', 'green', 'purple', 'orange'
        }

    def test_data_migration_assigns_demo_account_themes(self, make_user):
        admin = make_user(email='admin@demo.com')
        leader = make_user(email='leader1@demo.com')
        member = make_user(email='member2@demo.com')
        legacy_user = make_user(email='legacy-theme@test.com')
        UserPreference.objects.create(user=legacy_user, theme_color='unsafe-value')
        migration = import_module('apps.users.migrations.0004_user_primary_color')

        migration.assign_demo_themes(django_apps, None)

        assert UserPreference.objects.get(user=admin).theme_color == 'blue'
        assert UserPreference.objects.get(user=leader).theme_color == 'green'
        assert UserPreference.objects.get(user=member).theme_color == 'green'
        assert UserPreference.objects.get(user=legacy_user).theme_color == 'blue'
