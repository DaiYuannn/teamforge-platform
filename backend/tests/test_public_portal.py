"""
P17 公共门户增强测试
- 公共门户返回公开公告（已发布且 is_public=True）
- 公共门户返回项目统计（总数 / 进行中 / 已完成）
- 公共接口无需认证
"""
import pytest
from django.utils import timezone

from apps.intellectual_property.models import IntellectualPropertyApplication
from apps.notifications.models import Announcement
from apps.projects.models import Project


def extract_data(response):
    """从统一响应格式中提取 data"""
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.fixture
def make_announcement(db, make_user):
    """创建公告的工厂函数"""
    counter = [0]

    def _make(
        title=None,
        content='门户公告内容',
        status=Announcement.Status.PUBLISHED,
        is_public=True,
        is_pinned=False,
        author=None,
        published_at='auto',
    ):
        counter[0] += 1
        author = author or make_user(
            global_role='teacher',
            email=f'portal_author{counter[0]}@test.com',
            name=f'门户作者{counter[0]}',
        )
        if status == Announcement.Status.PUBLISHED and (published_at == 'auto' or published_at is None):
            published_at = timezone.now()
        elif status != Announcement.Status.PUBLISHED:
            published_at = None
        return Announcement.objects.create(
            title=title or f'门户公告{counter[0]}',
            content=content,
            status=status,
            is_public=is_public,
            is_pinned=is_pinned,
            author=author,
            published_at=published_at,
        )

    return _make


@pytest.mark.api
@pytest.mark.django_db
class TestPublicPortalAccess:
    """公共门户访问测试"""

    def test_public_portal_no_auth(self, api_client):
        """公共门户无需登录"""
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert 'stats' in data
        assert 'project_statistics' in data
        assert 'announcements' in data

    def test_public_portal_response_structure(self, api_client):
        """公共门户返回完整结构"""
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 核心字段均存在
        for key in ('stats', 'project_statistics', 'announcements',
                    'awarded_projects', 'ip_results', 'core_members'):
            assert key in data, f'缺失字段 {key}'


@pytest.mark.api
@pytest.mark.django_db
class TestPublicPortalAnnouncements:
    """公共门户公告测试"""

    def test_returns_public_published_announcements(self, api_client, make_announcement):
        """仅返回已发布且公开的公告"""
        make_announcement(title='公开公告', is_public=True, status=Announcement.Status.PUBLISHED)
        make_announcement(title='非公开公告', is_public=False, status=Announcement.Status.PUBLISHED)
        make_announcement(title='公开草稿', is_public=True, status=Announcement.Status.DRAFT)
        make_announcement(title='公开归档', is_public=True, status=Announcement.Status.ARCHIVED)

        resp = api_client.get('/api/v1/dashboard/public-portal/')
        assert resp.status_code == 200
        titles = [a['title'] for a in extract_data(resp)['announcements']]
        assert '公开公告' in titles
        assert '非公开公告' not in titles
        assert '公开草稿' not in titles
        assert '公开归档' not in titles

    def test_announcement_fields(self, api_client, make_announcement):
        """公告条目包含展示字段"""
        make_announcement(title='字段公告', is_public=True)
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        data = extract_data(resp)
        ann = next(a for a in data['announcements'] if a['title'] == '字段公告')
        assert 'id' in ann
        assert 'title' in ann
        assert 'content' in ann
        assert 'category' in ann
        assert 'category_display' in ann
        assert 'is_pinned' in ann
        assert 'author_name' in ann
        assert 'published_at' in ann

    def test_announcement_limit(self, api_client, make_announcement):
        """公告最多返回 10 条"""
        for i in range(15):
            make_announcement(title=f'公告{i}', is_public=True)
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        data = extract_data(resp)
        assert len(data['announcements']) <= 10

    def test_pinned_announcement_first(self, api_client, make_announcement):
        """置顶公告排在前面"""
        make_announcement(title='普通公告', is_public=True, is_pinned=False)
        make_announcement(title='置顶公告', is_public=True, is_pinned=True)
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        data = extract_data(resp)
        assert data['announcements'][0]['title'] == '置顶公告'
        assert data['announcements'][0]['is_pinned'] is True


@pytest.mark.api
@pytest.mark.django_db
class TestPublicPortalProjectStatistics:
    """公共门户项目统计测试"""

    def test_project_statistics_counts(self, api_client, make_project):
        """项目统计正确反映总数/进行中/已完成"""
        make_project(status=Project.Status.ACTIVE)
        make_project(status=Project.Status.ACTIVE)
        make_project(status=Project.Status.CLOSED)

        resp = api_client.get('/api/v1/dashboard/public-portal/')
        assert resp.status_code == 200
        stats = extract_data(resp)['project_statistics']
        assert stats['total_projects'] == 3
        assert stats['active_projects'] == 2
        assert stats['completed_projects'] == 1

    def test_project_statistics_fields(self, api_client):
        """项目统计包含必需字段"""
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        stats = extract_data(resp)['project_statistics']
        for key in ('total_projects', 'active_projects', 'completed_projects'):
            assert key in stats

    def test_project_statistics_empty(self, api_client):
        """无项目时统计为 0"""
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        stats = extract_data(resp)['project_statistics']
        assert stats['total_projects'] == 0
        assert stats['active_projects'] == 0
        assert stats['completed_projects'] == 0


@pytest.mark.api
@pytest.mark.django_db
class TestPublicPortalIPStatistics:
    def test_authorized_and_archived_results_are_counted(
        self, api_client, make_project
    ):
        project = make_project()
        common = {
            'related_project': project,
            'main_writer': project.leader,
            'created_by': project.leader,
        }
        IntellectualPropertyApplication.objects.create(
            title='已授权成果',
            application_code='IP-PORTAL-AUTHORIZED',
            status=IntellectualPropertyApplication.Status.AUTHORIZED,
            **common,
        )
        IntellectualPropertyApplication.objects.create(
            title='已归档成果',
            application_code='IP-PORTAL-ARCHIVED',
            status=IntellectualPropertyApplication.Status.ARCHIVED,
            **common,
        )
        IntellectualPropertyApplication.objects.create(
            title='仍在撰写的申请',
            application_code='IP-PORTAL-WRITING',
            status=IntellectualPropertyApplication.Status.WRITING,
            **common,
        )

        response = api_client.get('/api/v1/dashboard/public-portal/')

        assert response.status_code == 200
        assert extract_data(response)['stats']['total_ip'] == 2
