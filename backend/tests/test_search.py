"""
M07: 全局搜索 API 测试
- 跨模块搜索: 项目、任务、成员、文件、比赛
- 空查询
- 权限验证
- 结果结构
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestGlobalSearch:
    """全局搜索测试"""

    def test_search_empty_query(self, member_client):
        """空查询返回空结果"""
        resp = member_client.get('/api/v1/dashboard/search/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] == 0
        assert data['projects'] == []

    def test_search_projects(self, member_client, make_project):
        """搜索项目"""
        make_project(name='人工智能挑战赛项目')
        make_project(name='Web开发测试项目')
        resp = member_client.get('/api/v1/dashboard/search/?q=人工智能')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['projects']) >= 1
        assert '人工智能' in data['projects'][0]['name']
        assert 'url' in data['projects'][0]

    def test_search_tasks(self, member_client, make_task):
        """搜索任务"""
        make_task(title='准备比赛材料')
        make_task(title='编写技术文档')
        resp = member_client.get('/api/v1/dashboard/search/?q=比赛材料')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['tasks']) >= 1
        assert '比赛' in data['tasks'][0]['title']

    def test_search_members(self, member_client, make_user):
        """搜索成员"""
        make_user(name='张三丰', email='zsf@test.com')
        make_user(name='李四光', email='lsg@test.com')
        resp = member_client.get('/api/v1/dashboard/search/?q=张三')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['members']) >= 1
        assert '张三' in data['members'][0]['name']

    def test_search_files(self, member_client, make_file):
        """搜索文件"""
        make_file(name='项目计划书.pdf')
        make_file(name='比赛报告.docx')
        resp = member_client.get('/api/v1/dashboard/search/?q=计划书')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['files']) >= 1

    def test_search_returns_total(self, member_client, make_project):
        """搜索返回总结果数"""
        make_project(name='测试搜索项目A')
        make_project(name='测试搜索项目B')
        resp = member_client.get('/api/v1/dashboard/search/?q=测试搜索')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['total'] >= 2
        assert data['query'] == '测试搜索'

    def test_search_unauthenticated(self, api_client):
        """未认证不能搜索"""
        resp = api_client.get('/api/v1/dashboard/search/?q=test')
        assert resp.status_code == 401

    def test_search_limit(self, member_client, make_project):
        """搜索结果限制"""
        for i in range(10):
            make_project(name=f'限量搜索项目{i}')
        resp = member_client.get('/api/v1/dashboard/search/?q=限量搜索&limit=3')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert len(data['projects']) <= 3

    def test_search_result_structure(self, member_client, make_project):
        """搜索结果结构完整"""
        make_project(name='结构测试项目')
        resp = member_client.get('/api/v1/dashboard/search/?q=结构测试')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 验证所有分类都存在
        for key in ['projects', 'tasks', 'members', 'files', 'competitions', 'total', 'query']:
            assert key in data
        # 验证项目结果结构
        if data['projects']:
            p = data['projects'][0]
            for field in ['id', 'name', 'code', 'status', 'leader_name', 'url']:
                assert field in p, f'项目结果缺少 {field} 字段'
