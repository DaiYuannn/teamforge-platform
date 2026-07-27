from datetime import datetime, timezone

import pytest
from unittest.mock import patch
from django.core import mail
from rest_framework_simplejwt.tokens import RefreshToken


def response_data(response):
    payload = response.json()
    return payload.get('data', payload)


@pytest.mark.api
@pytest.mark.django_db
class TestPasswordReset:
    def test_request_sends_working_one_time_link(self, api_client, make_user):
        user = make_user(email='reset@example.com', password='OldPass123!')
        response = api_client.post(
            '/api/v1/auth/password-reset/request/',
            {'email': 'reset@example.com'}, format='json',
        )
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        reset_url = mail.outbox[0].body.splitlines()[3]
        values = dict(
            item.split('=', 1) for item in reset_url.split('?', 1)[1].split('&')
        )

        confirmed = api_client.post(
            '/api/v1/auth/password-reset/confirm/',
            {
                **values,
                'new_password': 'NewPass456!',
                'confirm_password': 'NewPass456!',
            }, format='json',
        )
        assert confirmed.status_code == 200, confirmed.json()
        user.refresh_from_db()
        assert user.check_password('NewPass456!')

        reused = api_client.post(
            '/api/v1/auth/password-reset/confirm/',
            {
                **values,
                'new_password': 'OtherPass789!',
                'confirm_password': 'OtherPass789!',
            }, format='json',
        )
        assert reused.status_code == 400

    def test_request_does_not_reveal_unknown_account(self, api_client):
        response = api_client.post(
            '/api/v1/auth/password-reset/request/',
            {'email': 'missing@example.com'}, format='json',
        )
        assert response.status_code == 200
        assert mail.outbox == []

    def test_mail_failure_does_not_reveal_existing_account(
        self, api_client, make_user
    ):
        make_user(email='mail-failure@example.com', password='OldPass123!')
        with patch('apps.users.views.send_mail', side_effect=RuntimeError('smtp down')):
            response = api_client.post(
                '/api/v1/auth/password-reset/request/',
                {'email': 'mail-failure@example.com'}, format='json',
            )
        assert response.status_code == 200

    def test_invalid_token_does_not_change_password(self, api_client, make_user):
        user = make_user(email='invalid@example.com', password='OldPass123!')
        response = api_client.post(
            '/api/v1/auth/password-reset/confirm/',
            {
                'uid': 'MQ', 'token': 'invalid-token',
                'new_password': 'NewPass456!',
                'confirm_password': 'NewPass456!',
            }, format='json',
        )
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password('OldPass123!')

    @pytest.mark.parametrize(('remember_me', 'expected_days'), [(False, 1), (True, 30)])
    def test_remember_me_controls_refresh_lifetime(
        self, api_client, make_user, remember_me, expected_days
    ):
        email = f'remember-{remember_me}@example.com'
        make_user(email=email, password='TestPass123!')
        response = api_client.post('/api/v1/auth/login/', {
            'email': email,
            'password': 'TestPass123!',
            'remember_me': remember_me,
        }, format='json')
        assert response.status_code == 200
        token = RefreshToken(response_data(response)['token']['refresh'])
        lifetime = datetime.fromtimestamp(token['exp'], tz=timezone.utc) - datetime.fromtimestamp(
            token['iat'], tz=timezone.utc
        )
        seconds = lifetime.total_seconds()
        assert expected_days * 86400 - 2 <= seconds <= expected_days * 86400 + 2
