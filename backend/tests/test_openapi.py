"""
N60: OpenAPI Schema 测试
- GET /api/v1/common/openapi/schema/
- GET /api/v1/common/openapi/endpoints/
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestOpenAPISchema:
    """OpenAPI Schema 测试"""

    def test_schema_requires_auth(self, api_client):
        """Schema 需认证"""
        resp = api_client.get('/api/v1/common/openapi/schema/')
        assert resp.status_code in (401, 403)

    def test_schema_returns_openapi_version(self, member_client):
        """返回 openapi 版本字段"""
        resp = member_client.get('/api/v1/common/openapi/schema/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['openapi'] == '3.0.0'

    def test_schema_has_info(self, member_client):
        """返回 info 字段"""
        data = extract_data(member_client.get('/api/v1/common/openapi/schema/'))
        assert 'info' in data
        assert 'title' in data['info']
        assert 'version' in data['info']

    def test_schema_has_paths(self, member_client):
        """返回 paths 字段且非空"""
        data = extract_data(member_client.get('/api/v1/common/openapi/schema/'))
        assert 'paths' in data
        assert isinstance(data['paths'], dict)
        assert len(data['paths']) > 0

    def test_schema_endpoints_count(self, member_client):
        """返回 endpoints_count"""
        data = extract_data(member_client.get('/api/v1/common/openapi/schema/'))
        assert 'endpoints_count' in data
        assert data['endpoints_count'] > 0

    def test_schema_path_has_methods(self, member_client):
        """至少一个路径包含 HTTP 方法"""
        data = extract_data(member_client.get('/api/v1/common/openapi/schema/'))
        has_method = any(
            methods for methods in data['paths'].values()
        )
        assert has_method


@pytest.mark.api
@pytest.mark.django_db
class TestAPIEndpointList:
    """API 端点列表测试"""

    def test_endpoints_requires_auth(self, api_client):
        """端点列表需认证"""
        resp = api_client.get('/api/v1/common/openapi/endpoints/')
        assert resp.status_code in (401, 403)

    def test_endpoints_returns_list(self, member_client):
        """返回端点列表"""
        resp = member_client.get('/api/v1/common/openapi/endpoints/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'endpoints' in data
        assert isinstance(data['endpoints'], list)
        assert data['total'] == len(data['endpoints'])

    def test_endpoints_only_api_paths(self, member_client):
        """仅返回 API 路径"""
        data = extract_data(member_client.get('/api/v1/common/openapi/endpoints/'))
        for ep in data['endpoints']:
            assert 'api' in ep['path']

    def test_endpoints_have_methods(self, member_client):
        """每个端点包含 methods 字段"""
        data = extract_data(member_client.get('/api/v1/common/openapi/endpoints/'))
        for ep in data['endpoints']:
            assert 'methods' in ep
            assert isinstance(ep['methods'], list)
            assert len(ep['methods']) > 0
