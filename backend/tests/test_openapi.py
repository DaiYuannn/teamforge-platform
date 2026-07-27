"""
N60: OpenAPI Schema 测试
- GET /api/v1/common/openapi/schema/
- GET /api/v1/common/openapi/endpoints/
"""
import pytest
from rest_framework import serializers
from rest_framework.generics import GenericAPIView

from common.mixins import MultiSerializerMixin


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

    def test_schema_returns_openapi_version(self, admin_client):
        """返回 openapi 版本字段"""
        resp = admin_client.get('/api/v1/common/openapi/schema/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['openapi'].startswith('3.0.')

    def test_schema_has_info(self, admin_client):
        """返回 info 字段"""
        data = extract_data(admin_client.get('/api/v1/common/openapi/schema/'))
        assert 'info' in data
        assert 'title' in data['info']
        assert 'version' in data['info']

    def test_schema_has_paths(self, admin_client):
        """返回 paths 字段且非空"""
        data = extract_data(admin_client.get('/api/v1/common/openapi/schema/'))
        assert 'paths' in data
        assert isinstance(data['paths'], dict)
        assert len(data['paths']) > 0

    def test_schema_endpoints_count(self, admin_client):
        """返回 endpoints_count"""
        data = extract_data(admin_client.get('/api/v1/common/openapi/schema/'))
        assert len(data['paths']) > 0

    def test_schema_path_has_methods(self, admin_client):
        """至少一个路径包含 HTTP 方法"""
        data = extract_data(admin_client.get('/api/v1/common/openapi/schema/'))
        has_method = any(
            methods for methods in data['paths'].values()
        )
        assert has_method

    def test_schema_contains_components_and_operation_ids(self, admin_client):
        data = extract_data(admin_client.get('/api/v1/common/openapi/schema/'))
        assert isinstance(data.get('components'), dict)
        operations = [
            operation
            for path_item in data['paths'].values()
            for method, operation in path_item.items()
            if method in {'get', 'post', 'put', 'patch', 'delete'}
        ]
        assert operations
        assert all(operation.get('operationId') for operation in operations)
        operation_ids = [operation['operationId'] for operation in operations]
        assert len(operation_ids) == len(set(operation_ids))

    def test_schema_keeps_api_views_and_enum_names_stable(self, admin_client):
        data = extract_data(admin_client.get('/api/v1/common/openapi/schema/'))

        assert {
            '/api/v1/common/backup/',
            '/api/v1/dashboard/',
            '/api/v1/files/{id}/office-preview/',
            '/api/v1/notifications/sse/',
            '/api/v1/projects/health-score/',
        }.issubset(data['paths'])
        schemas = data['components']['schemas']
        assert 'ProjectStatusEnum' in schemas
        assert 'TaskStatusEnum' in schemas
        assert 'FileLevelEnum' in schemas
        assert 'ScheduledReportStatusEnum' in schemas

    def test_schema_describes_scoped_jwt_as_http_bearer(self, admin_client):
        data = extract_data(admin_client.get('/api/v1/common/openapi/schema/'))
        security_schemes = data['components']['securitySchemes']

        assert security_schemes['bearerAuth'] == {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
        assert {'bearerAuth': []} in data['paths']['/api/v1/projects/']['get']['security']


class TestMultiSerializerMixin:
    class ListSerializer(serializers.Serializer):
        name = serializers.CharField()

    class DetailSerializer(serializers.Serializer):
        name = serializers.CharField()
        description = serializers.CharField()

    class View(MultiSerializerMixin, GenericAPIView):
        serializer_classes_by_action = {
            'list': None,
            'retrieve': None,
        }

    def setup_method(self):
        self.View.serializer_classes_by_action = {
            'list': self.ListSerializer,
            'retrieve': self.DetailSerializer,
        }

    def test_falls_back_to_retrieve_serializer_without_action(self):
        view = self.View()

        assert view.get_serializer_class() is self.DetailSerializer

    def test_falls_back_to_retrieve_serializer_for_unmapped_custom_action(self):
        view = self.View()
        view.action = 'archive'

        assert view.get_serializer_class() is self.DetailSerializer

    def test_schema_probe_does_not_fetch_ip_application_object(self):
        from apps.intellectual_property.serializers import IPApplicationDetailSerializer
        from apps.intellectual_property.views import IPApplicationViewSet

        view = IPApplicationViewSet()
        view.action = 'retrieve'
        view.swagger_fake_view = True

        assert view.get_serializer_class() is IPApplicationDetailSerializer


@pytest.mark.api
@pytest.mark.django_db
class TestAPIEndpointList:
    """API 端点列表测试"""

    def test_endpoints_requires_auth(self, api_client):
        """端点列表需认证"""
        resp = api_client.get('/api/v1/common/openapi/endpoints/')
        assert resp.status_code in (401, 403)

    def test_endpoints_teacher_blocked(self, teacher_client):
        resp = teacher_client.get('/api/v1/common/openapi/endpoints/')
        assert resp.status_code == 403

    def test_schema_teacher_blocked(self, teacher_client):
        resp = teacher_client.get('/api/v1/common/openapi/schema/')
        assert resp.status_code == 403

    def test_endpoints_returns_list(self, admin_client):
        """返回端点列表"""
        resp = admin_client.get('/api/v1/common/openapi/endpoints/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'endpoints' in data
        assert isinstance(data['endpoints'], list)
        assert data['total'] == len(data['endpoints'])

    def test_endpoints_only_api_paths(self, admin_client):
        """仅返回 API 路径"""
        data = extract_data(admin_client.get('/api/v1/common/openapi/endpoints/'))
        for ep in data['endpoints']:
            assert 'api' in ep['path']

    def test_endpoints_have_methods(self, admin_client):
        """每个端点的方法与操作元数据一一对应。"""
        data = extract_data(admin_client.get('/api/v1/common/openapi/endpoints/'))
        for ep in data['endpoints']:
            assert 'methods' in ep
            assert isinstance(ep['methods'], list)
            assert len(ep['methods']) > 0
            assert set(ep['operations']) == set(ep['methods'])
            for operation in ep['operations'].values():
                assert {
                    'operation_id',
                    'summary',
                    'tags',
                }.issubset(operation)
                assert operation['operation_id']
                assert isinstance(operation['summary'], str)
                assert isinstance(operation['tags'], list)

    def test_member_blocked(self, member_client):
        """普通成员不可枚举系统端点。"""
        resp = member_client.get('/api/v1/common/openapi/endpoints/')
        assert resp.status_code == 403
