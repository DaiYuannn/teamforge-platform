"""2FA 明确不在当前产品范围，历史接口不得继续暴露。"""

import pytest


@pytest.mark.api
@pytest.mark.django_db
@pytest.mark.parametrize(
    ('method', 'path'),
    [
        ('post', '/api/v1/users/2fa/generate/'),
        ('post', '/api/v1/users/2fa/verify/'),
        ('post', '/api/v1/users/2fa/disable/'),
        ('get', '/api/v1/users/2fa/disable/'),
    ],
)
def test_two_factor_endpoints_are_not_exposed(member_client, method, path):
    response = getattr(member_client, method)(path, {}, format='json')

    assert response.status_code == 404
