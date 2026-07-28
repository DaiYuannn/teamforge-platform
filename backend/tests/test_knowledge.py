"""
N28: 知识库（Knowledge Base）测试
- 模型层：KnowledgeArticle 创建与类别
- API 层：文章 CRUD、搜索（标题/内容/标签）、按类别/项目过滤、浏览数
- 权限验证
"""
import pytest

from apps.common.team_models import Team, TeamMember
from apps.projects.knowledge_models import KnowledgeArticle

KNOWLEDGE_URL = '/api/v1/projects/knowledge/'


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
class TestKnowledgeArticleModel:
    """知识库文章模型测试"""

    def test_create_article(self, make_user):
        """创建文章"""
        author = make_user()
        article = KnowledgeArticle.objects.create(
            title='指南1', content='内容', author=author,
        )
        assert article.id is not None
        assert article.category == 'other'
        assert article.is_published is True
        assert article.view_count == 0
        assert article.tags == ''

    def test_category_choices(self, make_user):
        """类别枚举"""
        author = make_user()
        for cat in ['guide', 'template', 'faq', 'experience', 'other']:
            KnowledgeArticle.objects.create(
                title=f'文章-{cat}', content='内容', author=author, category=cat,
            )
        assert KnowledgeArticle.objects.count() == 5

    def test_tag_list_property(self, make_user):
        """tag_list 属性拆分标签"""
        author = make_user()
        article = KnowledgeArticle.objects.create(
            title='带标签', content='内容', author=author,
            tags='Python, Django, REST',
        )
        assert article.tag_list == ['Python', 'Django', 'REST']

    def test_tag_list_empty(self, make_user):
        """空标签"""
        author = make_user()
        article = KnowledgeArticle.objects.create(
            title='无标签', content='内容', author=author,
        )
        assert article.tag_list == []

    def test_article_with_project(self, make_project, make_user):
        """关联项目的文章"""
        project = make_project()
        author = make_user()
        article = KnowledgeArticle.objects.create(
            title='项目文章', content='内容', author=author, project=project,
        )
        assert article.project == project
        assert project.knowledge_articles.count() == 1

    def test_author_set_null_on_delete(self, make_user):
        """作者删除后文章作者置空"""
        author = make_user()
        article = KnowledgeArticle.objects.create(
            title='文章', content='内容', author=author,
        )
        author.delete()
        article.refresh_from_db()
        assert article.author is None


@pytest.mark.api
@pytest.mark.django_db
class TestKnowledgeArticleAPI:
    """知识库文章 API 测试"""

    def test_create_article(self, auth_client):
        """认证用户可以创建文章"""
        resp = auth_client.post(KNOWLEDGE_URL, {
            'title': 'API创建文章',
            'content': '这是内容',
            'category': 'guide',
            'tags': 'Python,Django',
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['title'] == 'API创建文章'
        assert data['category'] == 'guide'
        assert data['author'] == auth_client.user.id

    def test_list_articles(self, member_client, make_user):
        """普通成员可以查看文章列表"""
        author = make_user()
        KnowledgeArticle.objects.create(title='文章1', content='c', author=author)
        KnowledgeArticle.objects.create(title='文章2', content='c', author=author)
        resp = member_client.get(KNOWLEDGE_URL)
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) >= 2

    def test_retrieve_article_increments_view(self, auth_client, make_user):
        """获取详情时增加浏览数"""
        author = make_user()
        article = KnowledgeArticle.objects.create(
            title='详情', content='内容', author=author,
        )
        assert article.view_count == 0
        resp = auth_client.get(f'{KNOWLEDGE_URL}{article.id}/')
        assert resp.status_code == 200, resp.json()
        article.refresh_from_db()
        assert article.view_count == 1

    def test_filter_by_category(self, member_client, make_user):
        """按类别过滤"""
        author = make_user()
        KnowledgeArticle.objects.create(title='指南', content='c', author=author, category='guide')
        KnowledgeArticle.objects.create(title='模板', content='c', author=author, category='template')
        resp = member_client.get(f'{KNOWLEDGE_URL}?category=guide')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['category'] == 'guide' for r in results)
        titles = [r['title'] for r in results]
        assert '指南' in titles
        assert '模板' not in titles

    def test_filter_by_project(self, member_client, make_project, make_user):
        """按项目过滤"""
        p1 = make_project()
        p2 = make_project()
        author = make_user()
        KnowledgeArticle.objects.create(title='A', content='c', author=author, project=p1)
        KnowledgeArticle.objects.create(title='B', content='c', author=author, project=p2)
        resp = member_client.get(f'{KNOWLEDGE_URL}?project={p1.id}')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert all(r['project'] == p1.id for r in results)

    def test_search_by_title(self, member_client, make_user):
        """按标题搜索"""
        author = make_user()
        KnowledgeArticle.objects.create(title='Django入门指南', content='c', author=author)
        KnowledgeArticle.objects.create(title='其他文章', content='c', author=author)
        resp = member_client.get(f'{KNOWLEDGE_URL}?search=Django')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) == 1
        assert 'Django' in results[0]['title']

    def test_search_by_content(self, member_client, make_user):
        """按内容搜索"""
        author = make_user()
        KnowledgeArticle.objects.create(title='标题A', content='包含特殊关键词XYZ的内容', author=author)
        KnowledgeArticle.objects.create(title='标题B', content='普通内容', author=author)
        resp = member_client.get(f'{KNOWLEDGE_URL}?search=XYZ')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) == 1
        assert results[0]['title'] == '标题A'

    def test_search_by_tags(self, member_client, make_user):
        """按标签搜索"""
        author = make_user()
        KnowledgeArticle.objects.create(title='文章1', content='c', author=author, tags='Python,Web')
        KnowledgeArticle.objects.create(title='文章2', content='c', author=author, tags='Java')
        resp = member_client.get(f'{KNOWLEDGE_URL}?search=Python')
        assert resp.status_code == 200
        results = extract_results(resp)
        assert len(results) == 1
        assert results[0]['title'] == '文章1'

    def test_search_action(self, member_client, make_user):
        """search 动作"""
        author = make_user()
        KnowledgeArticle.objects.create(title='FAQ常见问题', content='c', author=author)
        KnowledgeArticle.objects.create(title='其他', content='c', author=author)
        resp = member_client.get(f'{KNOWLEDGE_URL}search/?q=FAQ')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data) == 1
        assert 'FAQ' in data[0]['title']

    def test_search_action_empty_query(self, member_client):
        """search 动作空查询返回空列表"""
        resp = member_client.get(f'{KNOWLEDGE_URL}search/?q=')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data == []

    def test_by_tag_action(self, member_client, make_user):
        """按标签查询文章"""
        author = make_user()
        KnowledgeArticle.objects.create(title='A', content='c', author=author, tags='Python,Web')
        KnowledgeArticle.objects.create(title='B', content='c', author=author, tags='Java')
        KnowledgeArticle.objects.create(title='C', content='c', author=author, tags='Web,API')
        resp = member_client.get(f'{KNOWLEDGE_URL}by-tag/?tag=Web')
        assert resp.status_code == 200
        data = extract_data(resp)
        titles = [d['title'] for d in data]
        assert 'A' in titles
        assert 'C' in titles
        assert 'B' not in titles

    def test_by_tag_missing_param(self, member_client):
        """by-tag 缺少参数"""
        resp = member_client.get(f'{KNOWLEDGE_URL}by-tag/')
        assert resp.status_code == 400

    def test_update_article_by_author(self, auth_client, make_user):
        """作者可以更新文章"""
        article = KnowledgeArticle.objects.create(
            title='原标题', content='内容', author=auth_client.user,
        )
        resp = auth_client.patch(f'{KNOWLEDGE_URL}{article.id}/', {
            'title': '新标题',
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['title'] == '新标题'

    def test_delete_article_by_author(self, auth_client, make_user):
        """作者可以删除文章"""
        article = KnowledgeArticle.objects.create(
            title='待删除', content='内容', author=auth_client.user,
        )
        resp = auth_client.delete(f'{KNOWLEDGE_URL}{article.id}/')
        assert resp.status_code in (200, 204), resp.json()
        assert not KnowledgeArticle.objects.filter(id=article.id).exists()

    def test_update_by_non_author_forbidden(self, auth_client, make_user):
        """非作者不能更新他人文章"""
        author = make_user()
        article = KnowledgeArticle.objects.create(
            title='他人文章', content='内容', author=author,
        )
        resp = auth_client.patch(f'{KNOWLEDGE_URL}{article.id}/', {
            'title': '篡改',
        }, format='json')
        assert resp.status_code == 403

    def test_global_article_visible_inside_single_root_team(
        self, member_client, make_user,
    ):
        """Project-less knowledge stays usable in an unambiguous tenant."""
        owner = make_user()
        root = Team.objects.create(
            name='Knowledge root',
            code='KNOWLEDGE-SINGLE-ROOT',
            owner=owner,
        )
        TeamMember.objects.create(team=root, user=owner, role=TeamMember.Role.OWNER)
        TeamMember.objects.create(team=root, user=member_client.user)
        article = KnowledgeArticle.objects.create(
            title='single-root-global-article',
            content='organization knowledge',
            author=owner,
        )

        list_resp = member_client.get(KNOWLEDGE_URL)
        assert list_resp.status_code == 200
        assert article.id in {
            row['id'] for row in extract_results(list_resp)
        }

    def test_global_article_hidden_when_multiple_root_teams_exist(
        self, member_client, make_user,
    ):
        """An unscoped article must not leak across independent root teams."""
        other_owner = make_user()
        viewer_root = Team.objects.create(
            name='Viewer root',
            code='KNOWLEDGE-VIEWER-ROOT',
            owner=member_client.user,
        )
        other_root = Team.objects.create(
            name='Other root',
            code='KNOWLEDGE-OTHER-ROOT',
            owner=other_owner,
        )
        TeamMember.objects.create(
            team=viewer_root,
            user=member_client.user,
            role=TeamMember.Role.OWNER,
        )
        TeamMember.objects.create(
            team=other_root,
            user=other_owner,
            role=TeamMember.Role.OWNER,
        )
        article = KnowledgeArticle.objects.create(
            title='cross-root-global-secret',
            content='must remain tenant scoped',
            author=other_owner,
        )

        list_resp = member_client.get(KNOWLEDGE_URL)
        assert list_resp.status_code == 200
        assert article.id not in {
            row['id'] for row in extract_results(list_resp)
        }

        detail_resp = member_client.get(f'{KNOWLEDGE_URL}{article.id}/')
        assert detail_resp.status_code == 404

        search_resp = member_client.get(
            '/api/v1/dashboard/search/'
            '?q=cross-root-global-secret&search_type=knowledge'
        )
        assert search_resp.status_code == 200
        assert extract_data(search_resp)['knowledge'] == []

        create_resp = member_client.post(KNOWLEDGE_URL, {
            'title': 'ambiguous-global-article',
            'content': 'must bind to a project',
        }, format='json')
        assert create_resp.status_code == 403

    def test_unauthenticated_cannot_access(self, api_client):
        """未认证不能访问"""
        resp = api_client.get(KNOWLEDGE_URL)
        assert resp.status_code == 401
