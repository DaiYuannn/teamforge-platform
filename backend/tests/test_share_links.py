"""
N33: 文件分享链接（Share Links）测试
- 模型层：FileShareLink 创建、令牌生成、有效性判断
- API 层：创建分享、令牌访问、撤销、访问次数/过期限制
- 权限验证
"""
from datetime import timedelta
from django.utils import timezone

import pytest

from apps.files.share_models import FileShareLink

SHARE_URL = '/api/v1/files/shares/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


def extract_results(resp):
    data = extract_data(resp)
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    if isinstance(data, list):
        return data
    return data


@pytest.mark.model
@pytest.mark.django_db
class TestFileShareLinkModel:
    """文件分享链接模型测试"""

    def test_create_share_link(self, make_file, make_user):
        """创建分享链接"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
        )
        assert link.id is not None
        assert link.is_active is True
        assert link.view_count == 0
        assert link.expire_at is None
        assert link.max_views is None
        assert len(link.token) == 32  # uuid4().hex 长度

    def test_generate_token_unique(self, make_file, make_user):
        """生成的令牌唯一"""
        f = make_file()
        user = make_user()
        tokens = {FileShareLink.generate_token() for _ in range(20)}
        assert len(tokens) == 20

    def test_token_unique_constraint(self, make_file, make_user):
        """令牌唯一约束"""
        f = make_file()
        user = make_user()
        token = FileShareLink.generate_token()
        FileShareLink.objects.create(file=f, created_by=user, token=token)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            FileShareLink.objects.create(file=f, created_by=user, token=token)

    def test_is_valid_active(self, make_file, make_user):
        """有效链接"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
        )
        assert link.is_valid is True
        assert link.is_expired is False
        assert link.is_view_limit_reached is False

    def test_is_valid_revoked(self, make_file, make_user):
        """已撤销的链接无效"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
            is_active=False,
        )
        assert link.is_valid is False

    def test_is_valid_expired(self, make_file, make_user):
        """已过期的链接无效"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
            expire_at=timezone.now() - timedelta(hours=1),
        )
        assert link.is_expired is True
        assert link.is_valid is False

    def test_is_valid_view_limit(self, make_file, make_user):
        """达访问上限的链接无效"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
            max_views=3, view_count=3,
        )
        assert link.is_view_limit_reached is True
        assert link.is_valid is False

    def test_cascade_delete_with_file(self, make_file, make_user):
        """删除文件时级联删除分享链接"""
        f = make_file()
        user = make_user()
        FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
        )
        assert FileShareLink.objects.count() == 1
        f.delete()
        assert FileShareLink.objects.count() == 0

    def test_related_name_share_links(self, make_file, make_user):
        """反向关系 file.share_links 可访问"""
        f = make_file()
        user = make_user()
        FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
        )
        assert f.share_links.count() == 1


@pytest.mark.api
@pytest.mark.django_db
class TestFileShareLinkAPI:
    """文件分享链接 API 测试"""

    def test_create_share_link(self, auth_client, make_file):
        """创建分享链接"""
        f = make_file()
        resp = auth_client.post(SHARE_URL, {
            'file': f.id,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['token']
        assert len(data['token']) == 32
        assert data['file'] == f.id
        assert data['created_by'] == auth_client.user.id
        assert data['is_active'] is True

    def test_create_share_link_with_expiry(self, auth_client, make_file):
        """创建带过期时间的分享链接"""
        f = make_file()
        expire = (timezone.now() + timedelta(days=7)).isoformat()
        resp = auth_client.post(SHARE_URL, {
            'file': f.id,
            'expire_at': expire,
            'max_views': 10,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['max_views'] == 10
        assert data['expire_at'] is not None

    def test_create_share_nonexistent_file(self, auth_client):
        """为不存在的文件创建分享链接"""
        resp = auth_client.post(SHARE_URL, {
            'file': 999999,
        }, format='json')
        assert resp.status_code == 404

    def test_list_share_links(self, auth_client, make_file):
        """查看自己创建的分享链接列表"""
        f = make_file()
        auth_client.post(SHARE_URL, {'file': f.id}, format='json')
        resp = auth_client.get(SHARE_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 1
        assert all(r['created_by'] == auth_client.user.id for r in results)

    def test_retrieve_share_link(self, auth_client, make_file):
        """查看分享链接详情"""
        f = make_file()
        create_resp = auth_client.post(SHARE_URL, {'file': f.id}, format='json')
        link_id = extract_data(create_resp)['id']
        resp = auth_client.get(f'{SHARE_URL}{link_id}/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['id'] == link_id

    def test_revoke_share_link(self, auth_client, make_file):
        """撤销分享链接"""
        f = make_file()
        create_resp = auth_client.post(SHARE_URL, {'file': f.id}, format='json')
        link_id = extract_data(create_resp)['id']
        resp = auth_client.post(f'{SHARE_URL}{link_id}/revoke/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['is_active'] is False

    def test_access_by_token(self, api_client, make_file, make_user):
        """通过令牌访问文件（无需认证）"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
        )
        resp = api_client.get(f'{SHARE_URL}access/?token={link.token}')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'token' not in data
        assert data['file']['name'] == f.name
        link.refresh_from_db()
        assert link.view_count == 1

    def test_access_by_token_increments_count(self, api_client, make_file, make_user):
        """多次访问增加访问次数"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
        )
        for _ in range(3):
            resp = api_client.get(f'{SHARE_URL}access/?token={link.token}')
            assert resp.status_code == 200
        link.refresh_from_db()
        assert link.view_count == 3

    def test_access_revoked_link(self, api_client, make_file, make_user):
        """访问已撤销的链接"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
            is_active=False,
        )
        resp = api_client.get(f'{SHARE_URL}access/?token={link.token}')
        assert resp.status_code == 403

    def test_access_expired_link(self, api_client, make_file, make_user):
        """访问已过期的链接"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
            expire_at=timezone.now() - timedelta(hours=1),
        )
        resp = api_client.get(f'{SHARE_URL}access/?token={link.token}')
        assert resp.status_code == 403

    def test_access_max_views_reached(self, api_client, make_file, make_user):
        """访问达上限的链接"""
        f = make_file()
        user = make_user()
        link = FileShareLink.objects.create(
            file=f, created_by=user, token=FileShareLink.generate_token(),
            max_views=2, view_count=2,
        )
        resp = api_client.get(f'{SHARE_URL}access/?token={link.token}')
        assert resp.status_code == 403

    def test_access_invalid_token(self, api_client):
        """访问无效令牌"""
        resp = api_client.get(f'{SHARE_URL}access/?token=invalidtoken')
        assert resp.status_code == 404

    def test_access_missing_token(self, api_client):
        """缺少令牌参数"""
        resp = api_client.get(f'{SHARE_URL}access/')
        assert resp.status_code == 400

    def test_delete_share_link_by_owner(self, auth_client, make_file):
        """创建人可删除分享链接"""
        f = make_file()
        create_resp = auth_client.post(SHARE_URL, {'file': f.id}, format='json')
        link_id = extract_data(create_resp)['id']
        resp = auth_client.delete(f'{SHARE_URL}{link_id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not FileShareLink.objects.filter(id=link_id).exists()

    def test_delete_share_link_by_non_owner(self, member_client, make_file, make_user):
        """非创建人不能删除（无法访问他人链接，返回 404）"""
        f = make_file()
        other_user = make_user(email='other_owner@test.com')
        link = FileShareLink.objects.create(
            file=f, created_by=other_user, token=FileShareLink.generate_token(),
        )
        resp = member_client.delete(f'{SHARE_URL}{link.id}/')
        # 普通成员的查询集仅含自己创建的链接，访问他人链接返回 404
        assert resp.status_code in (403, 404)
        assert FileShareLink.objects.filter(id=link.id).exists()

    def test_unauthenticated_cannot_list(self, api_client):
        """未认证不能查看分享列表"""
        resp = api_client.get(SHARE_URL)
        assert resp.status_code == 401
