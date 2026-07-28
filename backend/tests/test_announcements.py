"""
公告模块 API 测试
- 公告 CRUD
- 置顶/取消置顶
- 公开接口（无需登录）
- 草稿可见性（仅老师/管理员）
"""
import pytest
from django.utils import timezone

from apps.notifications.models import Announcement


def extract_data(response):
    """从统一响应格式中提取 data"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


def get_results(data):
    """从分页或非分页数据中提取结果列表"""
    if isinstance(data, dict):
        return data.get('results', data)
    return data


@pytest.fixture
def make_announcement(db, make_user):
    """创建公告的工厂函数"""
    counter = [0]

    def _make(
        title=None,
        content='测试内容',
        category=Announcement.Category.SYSTEM,
        status=Announcement.Status.PUBLISHED,
        is_pinned=False,
        is_public=False,
        author=None,
        published_at='auto',
        **extra,
    ):
        counter[0] += 1
        author = author or make_user(
            global_role='teacher',
            email=f'ann_author{counter[0]}@test.com',
            name=f'公告作者{counter[0]}',
        )
        if status == Announcement.Status.PUBLISHED and (published_at == 'auto' or published_at is None):
            published_at = timezone.now()
        elif status != Announcement.Status.PUBLISHED:
            published_at = None
        return Announcement.objects.create(
            title=title or f'测试公告{counter[0]}',
            content=content,
            category=category,
            status=status,
            is_pinned=is_pinned,
            is_public=is_public,
            author=author,
            published_at=published_at,
            **extra,
        )

    return _make


@pytest.mark.api
@pytest.mark.django_db
class TestAnnouncementList:
    """公告列表与可见性测试"""

    def test_member_can_list_published(self, member_client, make_announcement):
        """普通成员可查看已发布公告"""
        make_announcement(title='已发布公告-成员可见')
        resp = member_client.get('/api/v1/notifications/announcements/')
        assert resp.status_code == 200
        results = get_results(extract_data(resp))
        assert len(results) > 0
        assert results[0]['title'] == '已发布公告-成员可见'

    def test_member_cannot_see_draft(self, member_client, make_announcement):
        """普通成员不可见草稿"""
        make_announcement(title='草稿不可见', status=Announcement.Status.DRAFT)
        resp = member_client.get('/api/v1/notifications/announcements/')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(extract_data(resp))]
        assert '草稿不可见' not in titles

    def test_teacher_can_see_draft(self, teacher_client, make_announcement):
        """老师可见草稿"""
        make_announcement(title='草稿-老师可见', status=Announcement.Status.DRAFT)
        resp = teacher_client.get('/api/v1/notifications/announcements/')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(extract_data(resp))]
        assert '草稿-老师可见' in titles

    def test_admin_can_see_draft(self, admin_client, make_announcement):
        """管理员可见草稿"""
        make_announcement(title='草稿-管理员可见', status=Announcement.Status.DRAFT)
        resp = admin_client.get('/api/v1/notifications/announcements/')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(extract_data(resp))]
        assert '草稿-管理员可见' in titles

    def test_list_requires_auth(self, api_client):
        """未登录访问公告列表返回 401"""
        resp = api_client.get('/api/v1/notifications/announcements/')
        assert resp.status_code == 401

    def test_retrieve_announcement(self, member_client, make_announcement):
        """公告详情含展示字段"""
        ann = make_announcement(title='详情公告')
        resp = member_client.get(f'/api/v1/notifications/announcements/{ann.id}/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['title'] == '详情公告'
        assert 'category_display' in data
        assert 'status_display' in data
        assert 'author_name' in data


@pytest.mark.api
@pytest.mark.django_db
class TestAnnouncementCreate:
    """公告创建测试"""

    def test_teacher_can_create_published(self, teacher_client):
        """老师可创建已发布公告，自动设置作者与发布时间"""
        resp = teacher_client.post('/api/v1/notifications/announcements/', {
            'title': '新公告',
            'content': '公告内容',
            'category': 'system',
            'status': 'published',
            'is_public': False,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['title'] == '新公告'
        assert data['status'] == 'published'
        assert data['status_display'] == '已发布'
        assert data['category_display'] == '系统公告'
        assert data['author'] == teacher_client.user.id
        assert data['author_name'] == teacher_client.user.name
        assert data['published_at'] is not None

    def test_teacher_create_draft_no_published_at(self, teacher_client):
        """创建草稿公告不带发布时间"""
        resp = teacher_client.post('/api/v1/notifications/announcements/', {
            'title': '草稿公告',
            'content': '内容',
            'status': 'draft',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['status'] == 'draft'
        assert data['published_at'] is None

    def test_admin_can_create(self, admin_client):
        """管理员可创建公告"""
        resp = admin_client.post('/api/v1/notifications/announcements/', {
            'title': '管理员公告',
            'content': '内容',
            'status': 'published',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['title'] == '管理员公告'
        assert data['author'] == admin_client.user.id

    def test_member_cannot_create(self, member_client):
        """普通成员不能创建公告"""
        resp = member_client.post('/api/v1/notifications/announcements/', {
            'title': '成员公告',
            'content': '内容',
        }, format='json')
        assert resp.status_code == 403

    def test_active_team_co_lead_can_create(self, member_client, make_user):
        from apps.common.team_models import Team, TeamMember

        owner = make_user(email='announcement-owner@test.com')
        team = Team.objects.create(
            name='公告小团队',
            code='ANNOUNCEMENT-SQUAD',
            owner=owner,
        )
        TeamMember.objects.create(
            team=team,
            user=owner,
            role=TeamMember.Role.OWNER,
        )
        TeamMember.objects.create(
            team=team,
            user=member_client.user,
            role=TeamMember.Role.CO_LEAD,
        )

        resp = member_client.post('/api/v1/notifications/announcements/', {
            'title': '共同负责人公告',
            'content': '团队日常通知',
            'status': 'published',
        }, format='json')

        assert resp.status_code == 201, resp.json()
        assert extract_data(resp)['author'] == member_client.user.id

    def test_announcement_supports_resource_categories_and_links(
        self,
        teacher_client,
    ):
        resp = teacher_client.post('/api/v1/notifications/announcements/', {
            'title': '会议与模板资料',
            'content': '请先看回放，再使用计划书模板。',
            'category': 'meeting',
            'status': 'published',
            'resource_links': [
                {
                    'title': '腾讯会议回放',
                    'url': 'https://example.com/replay',
                },
                {
                    'title': '计划书模板',
                    'url': 'https://example.com/template',
                },
            ],
        }, format='json')

        assert resp.status_code == 201, resp.json()
        data = extract_data(resp)
        assert data['category_display'] == '会议回放'
        assert data['resource_links'][0] == {
            'title': '腾讯会议回放',
            'url': 'https://example.com/replay',
        }

    def test_resource_link_rejects_non_web_scheme(self, teacher_client):
        resp = teacher_client.post('/api/v1/notifications/announcements/', {
            'title': '危险链接',
            'content': '链接不应被接受',
            'resource_links': [
                {'title': '本地文件', 'url': 'file:///tmp/private.docx'},
            ],
        }, format='json')

        assert resp.status_code == 400


@pytest.mark.api
@pytest.mark.django_db
class TestAnnouncementUpdate:
    """公告更新测试"""

    def test_teacher_can_update(self, teacher_client, make_announcement):
        """老师可更新公告"""
        ann = make_announcement(title='原标题')
        resp = teacher_client.patch(f'/api/v1/notifications/announcements/{ann.id}/', {
            'title': '新标题',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['title'] == '新标题'

    def test_update_draft_to_published_sets_published_at(self, teacher_client, make_announcement):
        """草稿更新为已发布时自动设置发布时间"""
        ann = make_announcement(title='草稿', status=Announcement.Status.DRAFT)
        assert ann.published_at is None
        resp = teacher_client.patch(f'/api/v1/notifications/announcements/{ann.id}/', {
            'status': 'published',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['status'] == 'published'
        assert data['published_at'] is not None

    def test_member_cannot_update(self, member_client, make_announcement):
        """普通成员不能更新公告"""
        ann = make_announcement(title='公告')
        resp = member_client.patch(f'/api/v1/notifications/announcements/{ann.id}/', {
            'title': '篡改',
        }, format='json')
        assert resp.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
class TestAnnouncementDelete:
    """公告删除测试"""

    def test_teacher_can_delete(self, teacher_client, make_announcement):
        """老师可删除公告"""
        ann = make_announcement(title='待删除')
        resp = teacher_client.delete(f'/api/v1/notifications/announcements/{ann.id}/')
        assert resp.status_code in (200, 204)
        assert not Announcement.objects.filter(id=ann.id).exists()

    def test_admin_can_delete(self, admin_client, make_announcement):
        """管理员可删除公告"""
        ann = make_announcement(title='管理员删除')
        resp = admin_client.delete(f'/api/v1/notifications/announcements/{ann.id}/')
        assert resp.status_code in (200, 204)
        assert not Announcement.objects.filter(id=ann.id).exists()

    def test_member_cannot_delete(self, member_client, make_announcement):
        """普通成员不能删除公告"""
        ann = make_announcement(title='公告')
        resp = member_client.delete(f'/api/v1/notifications/announcements/{ann.id}/')
        assert resp.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
class TestAnnouncementPin:
    """公告置顶/取消置顶测试"""

    def test_pin_announcement(self, teacher_client, make_announcement):
        """置顶公告"""
        ann = make_announcement(title='公告', is_pinned=False)
        resp = teacher_client.post(f'/api/v1/notifications/announcements/{ann.id}/pin/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['is_pinned'] is True

    def test_unpin_announcement(self, teacher_client, make_announcement):
        """取消置顶"""
        ann = make_announcement(title='公告', is_pinned=True)
        resp = teacher_client.post(f'/api/v1/notifications/announcements/{ann.id}/pin/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['is_pinned'] is False

    def test_pin_toggle_persists(self, teacher_client, make_announcement):
        """置顶状态持久化"""
        ann = make_announcement(title='公告', is_pinned=False)
        teacher_client.post(f'/api/v1/notifications/announcements/{ann.id}/pin/')
        ann.refresh_from_db()
        assert ann.is_pinned is True

    def test_member_cannot_pin(self, member_client, make_announcement):
        """普通成员不能置顶"""
        ann = make_announcement(title='公告')
        resp = member_client.post(f'/api/v1/notifications/announcements/{ann.id}/pin/')
        assert resp.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
class TestAnnouncementPublic:
    """公开公告接口测试"""

    def test_public_no_auth_required(self, api_client, make_announcement):
        """公开接口无需登录"""
        make_announcement(title='公开公告', is_public=True)
        resp = api_client.get('/api/v1/notifications/announcements/public/')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(extract_data(resp))]
        assert '公开公告' in titles

    def test_public_excludes_non_public(self, api_client, make_announcement):
        """公开接口仅返回 is_public=True 的公告"""
        make_announcement(title='公开', is_public=True)
        make_announcement(title='非公开', is_public=False)
        resp = api_client.get('/api/v1/notifications/announcements/public/')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(extract_data(resp))]
        assert '公开' in titles
        assert '非公开' not in titles

    def test_public_excludes_draft(self, api_client, make_announcement):
        """公开接口不含草稿"""
        make_announcement(title='公开草稿', is_public=True, status=Announcement.Status.DRAFT)
        resp = api_client.get('/api/v1/notifications/announcements/public/')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(extract_data(resp))]
        assert '公开草稿' not in titles

    def test_public_excludes_archived(self, api_client, make_announcement):
        """公开接口不含已归档"""
        make_announcement(title='公开归档', is_public=True, status=Announcement.Status.ARCHIVED)
        resp = api_client.get('/api/v1/notifications/announcements/public/')
        assert resp.status_code == 200
        titles = [r['title'] for r in get_results(extract_data(resp))]
        assert '公开归档' not in titles
