"""
N61: 无障碍 / API 可访问性报告测试
- GET /api/v1/common/accessibility/report/
"""
import pytest
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter
from rest_framework.viewsets import ViewSet

from common.mixins import MultiPermissionMixin
from common.permissions import IsSysAdmin
from apps.common.accessibility_views import (
    _collect_endpoints,
    _is_restricted_permission,
    _operation_label,
    _view_permission_classes,
)


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestAccessibilityReport:
    """无障碍报告测试"""

    def test_report_requires_auth(self, api_client):
        """报告需认证"""
        resp = api_client.get('/api/v1/common/accessibility/report/')
        assert resp.status_code in (401, 403)

    def test_report_rejects_teacher(self, teacher_client):
        resp = teacher_client.get('/api/v1/common/accessibility/report/')
        assert resp.status_code == 403

    def test_report_returns_checks(self, admin_client):
        """返回检查清单"""
        resp = admin_client.get('/api/v1/common/accessibility/report/')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert 'checks' in data
        assert isinstance(data['checks'], list)
        assert len(data['checks']) >= 4

    def test_includes_error_responses_check(self, admin_client):
        """包含统一错误响应检查"""
        data = extract_data(admin_client.get('/api/v1/common/accessibility/report/'))
        items = [c['item'] for c in data['checks']]
        assert 'error_responses' in items

    def test_includes_list_pagination_check(self, admin_client):
        """包含列表分页检查"""
        data = extract_data(admin_client.get('/api/v1/common/accessibility/report/'))
        items = [c['item'] for c in data['checks']]
        assert 'list_pagination' in items

    def test_includes_write_requires_auth_check(self, admin_client):
        """包含写操作认证检查"""
        data = extract_data(admin_client.get('/api/v1/common/accessibility/report/'))
        items = [c['item'] for c in data['checks']]
        assert 'write_requires_auth' in items

    def test_includes_destructive_requires_permissions_check(self, admin_client):
        """包含破坏性操作权限检查"""
        data = extract_data(admin_client.get('/api/v1/common/accessibility/report/'))
        items = [c['item'] for c in data['checks']]
        assert 'destructive_requires_permissions' in items

    def test_each_check_has_passed_field(self, admin_client):
        """每项检查包含 passed 字段"""
        data = extract_data(admin_client.get('/api/v1/common/accessibility/report/'))
        for check in data['checks']:
            assert 'passed' in check
            assert isinstance(check['passed'], bool)

    def test_report_returns_score(self, admin_client):
        """返回可访问性评分"""
        data = extract_data(admin_client.get('/api/v1/common/accessibility/report/'))
        assert 'score' in data
        assert 0 <= data['score'] <= 100
        assert data['passed'] + data['failed'] == data['total']

    def test_report_includes_scan_counts_and_browser_audit(self, admin_client):
        data = extract_data(admin_client.get('/api/v1/common/accessibility/report/'))
        assert data['scope'] == 'api_governance'
        assert data['paths_scanned'] > 0
        assert data['endpoints_scanned'] >= data['paths_scanned']
        governed_checks = {
            check['item']: check
            for check in data['checks']
            if check['item'] in {
                'write_requires_auth',
                'destructive_requires_permissions',
            }
        }
        assert set(governed_checks) == {
            'write_requires_auth',
            'destructive_requires_permissions',
        }
        assert all(
            isinstance(check['unrestricted_count'], int)
            for check in governed_checks.values()
        )
        assert data['browser_audit']['runner'] == 'Playwright + axe-core'
        assert data['browser_audit']['standard'] == 'WCAG 2.1 A/AA'
        assert data['browser_audit']['source'] == 'ci'
        assert data['browser_audit']['is_realtime'] is False


class TestEndpointCollection:
    class RoutedViewSet(MultiPermissionMixin, ViewSet):
        permission_classes = [IsAuthenticated]
        permission_classes_by_action = {
            'create': [AllowAny],
            'update': [IsSysAdmin],
            'destroy': [IsSysAdmin],
        }

        def list(self, request):
            return Response()

        def create(self, request):
            return Response()

        def update(self, request, pk=None):
            return Response()

        def destroy(self, request, pk=None):
            return Response()

    def setup_method(self):
        router = SimpleRouter()
        router.register('records', self.RoutedViewSet, basename='record')
        self.endpoints = _collect_endpoints(router.urls, prefix='api/v1/')
        self.by_operation = {
            _operation_label(endpoint): endpoint
            for endpoint in self.endpoints
        }

    def test_collects_viewset_list_create_update_and_destroy_actions(self):
        assert set(self.by_operation) == {
            'GET /api/v1/records/',
            'POST /api/v1/records/',
            'PUT /api/v1/records/{pk}/',
            'DELETE /api/v1/records/{pk}/',
        }
        assert {
            label: endpoint['action']
            for label, endpoint in self.by_operation.items()
        } == {
            'GET /api/v1/records/': 'list',
            'POST /api/v1/records/': 'create',
            'PUT /api/v1/records/{pk}/': 'update',
            'DELETE /api/v1/records/{pk}/': 'destroy',
        }

    def test_resolves_action_level_allow_any_permission(self):
        create_permissions = _view_permission_classes(
            self.by_operation['POST /api/v1/records/'],
        )
        list_permissions = _view_permission_classes(
            self.by_operation['GET /api/v1/records/'],
        )

        assert len(create_permissions) == 1
        assert isinstance(create_permissions[0], AllowAny)
        assert len(list_permissions) == 1
        assert isinstance(list_permissions[0], IsAuthenticated)

    @pytest.mark.parametrize('permission', [AllowAny, AllowAny()])
    def test_allow_any_is_not_restricted(self, permission):
        assert _is_restricted_permission(permission) is False
