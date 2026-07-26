"""
N47: Open API 文档测试
- GET /api/v1/common/api-docs/
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestAPIDocs:
    """Open API 文档测试"""

    def test_returns_api_info(self, teacher_client):
        """返回 API 文档信息"""
        resp = teacher_client.get('/api/v1/common/api-docs/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'title' in data
        assert 'version' in data

    def test_returns_endpoint_count(self, teacher_client):
        """返回端点数量"""
        data = extract_data(teacher_client.get('/api/v1/common/api-docs/'))
        assert 'endpoint_count' in data
        assert isinstance(data['endpoint_count'], int)
        assert data['endpoint_count'] > 0

    def test_returns_schema_url(self, teacher_client):
        """返回 schema URL"""
        data = extract_data(teacher_client.get('/api/v1/common/api-docs/'))
        assert 'schema_url' in data
        assert data['schema_url']

    def test_returns_docs_urls(self, teacher_client):
        """返回文档 URL"""
        data = extract_data(teacher_client.get('/api/v1/common/api-docs/'))
        assert 'docs_url' in data
        assert 'redoc_url' in data

    def test_unauthenticated_blocked(self, api_client):
        """未认证不可访问"""
        resp = api_client.get('/api/v1/common/api-docs/')
        assert resp.status_code in (401, 403)
