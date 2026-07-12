"""
M05: 密码与账号安全测试
- 修改密码
- 旧密码验证
- 新密码强度验证
- 密码修改后操作日志
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.api
@pytest.mark.django_db
class TestChangePassword:
    """修改密码测试"""

    def test_change_password_success(self, api_client, make_user):
        """成功修改密码"""
        user = make_user(email='pwd@test.com', password='OldPass123!')
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        resp = api_client.post('/api/v1/users/change-password/', {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        assert '成功' in resp.json().get('message', '')

        # 验证新密码可用
        user.refresh_from_db()
        assert user.check_password('NewPass456!')
        assert not user.check_password('OldPass123!')

    def test_change_password_wrong_old(self, api_client, make_user):
        """旧密码错误"""
        user = make_user(email='pwd2@test.com', password='OldPass123!')
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        resp = api_client.post('/api/v1/users/change-password/', {
            'old_password': 'WrongPass!',
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        assert resp.status_code in (400, 200)
        data = resp.json()
        assert data.get('code') != 0 or '错误' in data.get('message', '')

    def test_change_password_mismatch(self, api_client, make_user):
        """两次新密码不一致"""
        user = make_user(email='pwd3@test.com', password='OldPass123!')
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        resp = api_client.post('/api/v1/users/change-password/', {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'confirm_password': 'DifferentPass!',
        }, format='json')
        assert resp.status_code in (400, 200)
        data = resp.json()
        assert data.get('code') != 0 or '不一致' in data.get('message', '')

    def test_change_password_same_as_old(self, api_client, make_user):
        """新密码不能与旧密码相同"""
        user = make_user(email='pwd4@test.com', password='SamePass123!')
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        resp = api_client.post('/api/v1/users/change-password/', {
            'old_password': 'SamePass123!',
            'new_password': 'SamePass123!',
            'confirm_password': 'SamePass123!',
        }, format='json')
        data = resp.json()
        assert data.get('code') != 0 or '相同' in data.get('message', '')

    def test_change_password_unauthenticated(self, api_client):
        """未认证不能修改密码"""
        resp = api_client.post('/api/v1/users/change-password/', {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        assert resp.status_code == 401

    def test_change_password_logged(self, api_client, make_user):
        """修改密码必须记录操作日志"""
        from apps.audit.models import OperationLog
        user = make_user(email='pwd5@test.com', password='OldPass123!')
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        api_client.post('/api/v1/users/change-password/', {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')

        logs = OperationLog.objects.filter(
            module='users',
            operator=user,
        )
        assert logs.exists(), '修改密码必须记录操作日志'
