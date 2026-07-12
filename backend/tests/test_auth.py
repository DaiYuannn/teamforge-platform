"""
认证和 JWT 测试
- 登录
- token 刷新
- token 结构不变
统一响应格式: {code: 0, message: '...', data: {token: {access, refresh}, user: {...}}}
"""
import pytest
from rest_framework_simplejwt.tokens import RefreshToken


def extract_data(response):
    """从统一响应格式中提取 data"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
class TestAuth:
    """认证接口测试"""

    def test_login_success(self, api_client, make_user):
        """正常登录获取 token"""
        make_user(email='login@test.com', password='TestPass123!')
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'login@test.com',
            'password': 'TestPass123!',
        }, format='json')
        assert resp.status_code == 200
        data = extract_data(resp)
        # token 嵌套在 data.token 中
        token = data.get('token', data)
        assert 'access' in token
        assert 'refresh' in token
        assert 'user' in data

    def test_login_wrong_password(self, api_client, make_user):
        """密码错误"""
        make_user(email='login@test.com', password='TestPass123!')
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'login@test.com',
            'password': 'WrongPass!',
        }, format='json')
        assert resp.status_code in (400, 401)

    @pytest.mark.django_db
    def test_login_nonexistent_user(self, api_client):
        """不存在的用户"""
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'nobody@test.com',
            'password': 'TestPass123!',
        }, format='json')
        assert resp.status_code in (400, 401)

    def test_token_refresh(self, api_client, make_user):
        """token 刷新"""
        user = make_user(email='refresh@test.com', password='TestPass123!')
        refresh = RefreshToken.for_user(user)
        resp = api_client.post('/api/v1/auth/refresh/', {
            'refresh': str(refresh),
        }, format='json')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert 'access' in data or 'access' in resp.json()

    def test_unauthenticated_access_blocked(self, api_client):
        """未认证访问受保护接口"""
        resp = api_client.get('/api/v1/users/')
        assert resp.status_code == 401

    def test_login_returns_user_fields(self, api_client, make_user):
        """登录返回用户信息必须使用 name/global_role 字段"""
        make_user(
            email='fields@test.com',
            password='TestPass123!',
            global_role='sys_admin',
            name='测试管理员',
        )
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'fields@test.com',
            'password': 'TestPass123!',
        }, format='json')
        data = extract_data(resp)
        user_data = data.get('user', {})
        assert 'name' in user_data
        assert 'global_role' in user_data
        assert user_data['name'] == '测试管理员'
        assert user_data['global_role'] == 'sys_admin'
        # 确保不使用旧字段
        assert 'real_name' not in user_data
        assert 'role' not in user_data

    def test_jwt_token_structure(self, api_client, make_user):
        """JWT token 结构不被改变"""
        user = make_user(email='jwt@test.com', password='TestPass123!')
        resp = api_client.post('/api/v1/auth/login/', {
            'email': 'jwt@test.com',
            'password': 'TestPass123!',
        }, format='json')
        data = extract_data(resp)
        token = data.get('token', data)
        access = token['access']
        # JWT 结构: header.payload.signature
        parts = access.split('.')
        assert len(parts) == 3, 'JWT token 必须有三部分'

    def test_invalid_token_rejected(self, api_client):
        """无效 token 被拒绝"""
        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_12345')
        resp = api_client.get('/api/v1/users/')
        assert resp.status_code == 401
