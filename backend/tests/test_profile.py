"""
P11: 个人中心（个人信息）测试
- GET /api/v1/users/me/ 获取当前用户信息
- PUT/PATCH /api/v1/users/me/ 修改个人信息（name/phone/avatar/is_student/grade/major）
- 只读字段：username/email/global_role 不可通过此接口修改
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestMyProfile:
    """个人中心接口测试"""

    def test_get_profile(self, member_client):
        """获取当前用户个人信息"""
        resp = member_client.get('/api/v1/users/me/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['id'] == member_client.user.id
        assert data['email'] == member_client.user.email
        assert 'name' in data
        assert 'phone' in data
        assert 'global_role' in data
        assert 'is_student' in data
        assert 'grade' in data
        assert 'major' in data

    def test_update_name(self, member_client):
        """修改姓名"""
        resp = member_client.patch('/api/v1/users/me/', {'name': '新名字'}, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['name'] == '新名字'
        member_client.user.refresh_from_db()
        assert member_client.user.name == '新名字'

    def test_update_phone(self, member_client):
        """修改手机号"""
        resp = member_client.patch('/api/v1/users/me/', {'phone': '13800138000'}, format='json')
        assert resp.status_code == 200, resp.json()
        member_client.user.refresh_from_db()
        assert member_client.user.phone == '13800138000'

    def test_update_student_info(self, member_client):
        """修改年级和专业"""
        resp = member_client.patch('/api/v1/users/me/', {
            'grade': '大三',
            'major': '计算机科学与技术',
            'is_student': True,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        member_client.user.refresh_from_db()
        assert member_client.user.grade == '大三'
        assert member_client.user.major == '计算机科学与技术'
        assert member_client.user.is_student is True

    def test_put_full_update(self, member_client):
        """PUT 全量更新"""
        resp = member_client.put('/api/v1/users/me/', {
            'name': '全量更新',
            'phone': '13900139000',
            'is_student': False,
            'grade': '研一',
            'major': '软件工程',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        member_client.user.refresh_from_db()
        assert member_client.user.name == '全量更新'
        assert member_client.user.phone == '13900139000'
        assert member_client.user.is_student is False

    def test_email_is_read_only(self, member_client):
        """email 为只读字段，不可通过此接口修改"""
        original_email = member_client.user.email
        resp = member_client.patch('/api/v1/users/me/', {
            'email': 'hacked@test.com',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        member_client.user.refresh_from_db()
        # email 未被修改
        assert member_client.user.email == original_email

    def test_global_role_is_read_only(self, member_client):
        """global_role 为只读字段，普通成员无法提权"""
        original_role = member_client.user.global_role
        resp = member_client.patch('/api/v1/users/me/', {
            'global_role': 'sys_admin',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        member_client.user.refresh_from_db()
        assert member_client.user.global_role == original_role

    def test_username_is_read_only(self, member_client):
        """username 为只读字段"""
        original_username = member_client.user.username
        resp = member_client.patch('/api/v1/users/me/', {
            'username': 'hacker',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        member_client.user.refresh_from_db()
        assert member_client.user.username == original_username

    def test_unauthenticated_cannot_access(self, api_client):
        """未认证用户无法访问个人中心"""
        resp = api_client.get('/api/v1/users/me/')
        assert resp.status_code in (401, 403)

    def test_admin_profile(self, admin_client):
        """管理员也能访问个人中心"""
        resp = admin_client.get('/api/v1/users/me/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['global_role'] == 'sys_admin'

    def test_empty_patch_keeps_data(self, member_client):
        """空 PATCH 不修改任何数据"""
        original_name = member_client.user.name
        resp = member_client.patch('/api/v1/users/me/', {}, format='json')
        assert resp.status_code == 200
        member_client.user.refresh_from_db()
        assert member_client.user.name == original_name
