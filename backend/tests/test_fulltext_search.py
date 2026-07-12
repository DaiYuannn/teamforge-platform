"""
N29: 全文搜索增强测试
- 搜索知识库文章
- 搜索讨论主题
- search_type 参数限定搜索模块
- 多模块搜索
- 结果结构完整性
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestFullTextSearch:
    """全文搜索增强测试"""

    def test_search_knowledge_by_title(self, member_client, make_user):
        """搜索知识库文章（标题）"""
        from apps.projects.knowledge_models import KnowledgeArticle
        author = make_user()
        KnowledgeArticle.objects.create(title='Django开发指南', content='c', author=author)
        KnowledgeArticle.objects.create(title='其他文章', content='c', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=Django')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['knowledge']) >= 1
        assert 'Django' in data['knowledge'][0]['title']

    def test_search_knowledge_by_content(self, member_client, make_user):
        """搜索知识库文章（内容）"""
        from apps.projects.knowledge_models import KnowledgeArticle
        author = make_user()
        KnowledgeArticle.objects.create(title='标题A', content='包含特殊关键词KNOWLEDGE_KEY', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=KNOWLEDGE_KEY')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['knowledge']) >= 1
        assert data['knowledge'][0]['title'] == '标题A'

    def test_search_knowledge_by_tags(self, member_client, make_user):
        """搜索知识库文章（标签）"""
        from apps.projects.knowledge_models import KnowledgeArticle
        author = make_user()
        KnowledgeArticle.objects.create(title='标签文章', content='c', author=author, tags='Python,Search')
        resp = member_client.get('/api/v1/dashboard/search/?q=Python')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['knowledge']) >= 1
        assert data['knowledge'][0]['title'] == '标签文章'

    def test_search_discussions_by_title(self, member_client, make_project, make_user):
        """搜索讨论主题（标题）"""
        from apps.projects.discussion_models import DiscussionTopic
        project = make_project()
        author = make_user()
        DiscussionTopic.objects.create(project=project, title='讨论Django架构', content='c', author=author)
        DiscussionTopic.objects.create(project=project, title='无关主题', content='c', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=Django')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['discussions']) >= 1
        assert 'Django' in data['discussions'][0]['title']

    def test_search_discussions_by_content(self, member_client, make_project, make_user):
        """搜索讨论主题（内容）"""
        from apps.projects.discussion_models import DiscussionTopic
        project = make_project()
        author = make_user()
        DiscussionTopic.objects.create(project=project, title='标题', content='内容包含DISCUSSION_KEYWORD', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=DISCUSSION_KEYWORD')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['discussions']) >= 1
        assert data['discussions'][0]['title'] == '标题'

    def test_search_type_knowledge_only(self, member_client, make_user, make_project):
        """search_type=knowledge 仅搜索知识库"""
        from apps.projects.knowledge_models import KnowledgeArticle
        author = make_user()
        project = make_project(name='搜索目标项目')
        # 创建同名的知识库文章和项目，但只搜索 knowledge
        KnowledgeArticle.objects.create(title='搜索目标项目', content='c', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=搜索目标&search_type=knowledge')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['knowledge']) >= 1
        # search_type=knowledge 时 projects 应为空（不搜索）
        assert data['projects'] == []
        assert data['search_type'] == 'knowledge'

    def test_search_type_discussions_only(self, member_client, make_project, make_user):
        """search_type=discussions 仅搜索讨论区"""
        from apps.projects.discussion_models import DiscussionTopic
        project = make_project(name='搜索目标项目')
        author = make_user()
        DiscussionTopic.objects.create(project=project, title='搜索目标项目', content='c', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=搜索目标&search_type=discussions')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['discussions']) >= 1
        assert data['knowledge'] == []
        assert data['projects'] == []

    def test_search_type_multiple_modules(self, member_client, make_user, make_project):
        """search_type 支持多个模块（逗号分隔）"""
        from apps.projects.knowledge_models import KnowledgeArticle
        from apps.projects.discussion_models import DiscussionTopic
        author = make_user()
        project = make_project()
        KnowledgeArticle.objects.create(title='多模块搜索项', content='c', author=author)
        DiscussionTopic.objects.create(project=project, title='多模块搜索项', content='c', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=多模块搜索&search_type=knowledge,discussions')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['knowledge']) >= 1
        assert len(data['discussions']) >= 1
        # 未请求的模块应为空
        assert data['projects'] == []

    def test_search_type_invalid_module(self, member_client, make_project):
        """search_type 无效模块返回空结果"""
        make_project(name='无效模块测试')
        resp = member_client.get('/api/v1/dashboard/search/?q=无效模块&search_type=nonexistent')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 无效模块不匹配任何已知模块，所有结果为空
        assert data['total'] == 0

    def test_search_includes_new_modules_in_structure(self, member_client, make_project):
        """搜索结果结构包含 knowledge 和 discussions 字段"""
        make_project(name='结构测试项目')
        resp = member_client.get('/api/v1/dashboard/search/?q=结构测试')
        assert resp.status_code == 200
        data = extract_data(resp)
        for key in ['projects', 'tasks', 'members', 'files', 'competitions',
                     'knowledge', 'discussions', 'total', 'query']:
            assert key in data, f'搜索结果缺少 {key} 字段'

    def test_search_total_counts_only_active_modules(self, member_client, make_user):
        """total 只计算活跃模块的结果数"""
        from apps.projects.knowledge_models import KnowledgeArticle
        author = make_user()
        KnowledgeArticle.objects.create(title='总量计算测试', content='c', author=author)
        KnowledgeArticle.objects.create(title='总量计算测试2', content='c', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=总量计算&search_type=knowledge')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == len(data['knowledge'])

    def test_search_empty_query_returns_all_modules(self, member_client):
        """空查询返回所有模块的空列表"""
        resp = member_client.get('/api/v1/dashboard/search/?search_type=knowledge')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == 0
        assert data['knowledge'] == []

    def test_search_knowledge_result_structure(self, member_client, make_user):
        """知识库搜索结果结构完整"""
        from apps.projects.knowledge_models import KnowledgeArticle
        author = make_user()
        KnowledgeArticle.objects.create(title='结构验证文章', content='c', author=author, tags='Tag1')
        resp = member_client.get('/api/v1/dashboard/search/?q=结构验证')
        assert resp.status_code == 200
        data = extract_data(resp)
        if data['knowledge']:
            a = data['knowledge'][0]
            for field in ['id', 'title', 'category', 'category_display',
                          'author_name', 'project_name', 'tags', 'url']:
                assert field in a, f'知识库结果缺少 {field} 字段'

    def test_search_discussions_result_structure(self, member_client, make_project, make_user):
        """讨论搜索结果结构完整"""
        from apps.projects.discussion_models import DiscussionTopic
        project = make_project()
        author = make_user()
        DiscussionTopic.objects.create(project=project, title='结构验证讨论', content='c', author=author)
        resp = member_client.get('/api/v1/dashboard/search/?q=结构验证')
        assert resp.status_code == 200
        data = extract_data(resp)
        if data['discussions']:
            t = data['discussions'][0]
            for field in ['id', 'title', 'project_name', 'author_name',
                          'is_pinned', 'is_closed', 'reply_count', 'url']:
                assert field in t, f'讨论结果缺少 {field} 字段'
