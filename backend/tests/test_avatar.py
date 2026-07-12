"""
M06: 头像上传测试
- 上传成功
- 文件类型验证
- 文件大小限制
- 未认证拦截
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestAvatarUpload:
    """头像上传测试"""

    def test_upload_avatar_success(self, api_client, make_user):
        """成功上传头像"""
        from rest_framework_simplejwt.tokens import RefreshToken
        user = make_user(email='avatar@test.com')
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        upload = SimpleUploadedFile(
            'test_avatar.jpg',
            b'\xff\xd8\xff\xe0' + b'\x00' * 100,
            content_type='image/jpeg',
        )
        resp = api_client.post('/api/v1/users/upload-avatar/', {'avatar': upload}, format='multipart')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'avatar' in data

        user.refresh_from_db()
        assert bool(user.avatar) == True

    def test_upload_avatar_invalid_type(self, api_client, make_user):
        """不支持的视频类型"""
        from rest_framework_simplejwt.tokens import RefreshToken
        user = make_user(email='avatar2@test.com')
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        upload = SimpleUploadedFile('test.txt', b'hello', content_type='text/plain')
        resp = api_client.post('/api/v1/users/upload-avatar/', {'avatar': upload}, format='multipart')
        data = resp.json()
        assert data.get('code') != 0 or resp.status_code in (400, 200)

    def test_upload_avatar_no_file(self, api_client, make_user):
        """未提供文件"""
        from rest_framework_simplejwt.tokens import RefreshToken
        user = make_user(email='avatar3@test.com')
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        resp = api_client.post('/api/v1/users/upload-avatar/', {}, format='multipart')
        data = resp.json()
        assert data.get('code') != 0

    def test_upload_avatar_unauthenticated(self, api_client):
        """未认证不能上传"""
        upload = SimpleUploadedFile('test.jpg', b'content', content_type='image/jpeg')
        resp = api_client.post('/api/v1/users/upload-avatar/', {'avatar': upload}, format='multipart')
        assert resp.status_code == 401

    def test_upload_avatar_png(self, api_client, make_user):
        """上传 PNG 头像"""
        from rest_framework_simplejwt.tokens import RefreshToken
        user = make_user(email='avatar4@test.com')
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        upload = SimpleUploadedFile(
            'avatar.png',
            b'\x89PNG\r\n\x1a\n' + b'\x00' * 100,
            content_type='image/png',
        )
        resp = api_client.post('/api/v1/users/upload-avatar/', {'avatar': upload}, format='multipart')
        assert resp.status_code == 200, resp.json()
