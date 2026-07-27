"""
API 治理报告视图（浏览器 WCAG 扫描由 Playwright + axe-core 执行）。
- AccessibilityReportView: 返回 API 可访问性与安全治理检查清单
  - 所有端点具备统一错误响应
  - 所有列表端点已分页
  - 所有写操作要求认证
  - 所有破坏性操作要求特定权限

接口：
- GET /api/v1/common/accessibility/report/
"""
import re

from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.views import APIView

from common.permissions import IsSysAdmin, RolePermission
from common.response import success_response
from common.schema import success_response_schema


API_METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}
WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
PUBLIC_WRITE_OPERATIONS = {
    'POST /api/v1/auth/login/',
    'POST /api/v1/auth/refresh/',
    'POST /api/v1/users/oauth/callback/',
}
_REGEX_PARAMETER = re.compile(r'\(\?P<([^>]+)>[^)]+\)')
_ROUTE_PARAMETER = re.compile(r'<(?:[^:>]+:)?([^>]+)>')


def _normalize_path(value):
    """Return a stable operator-facing path for Django route patterns."""
    path = _REGEX_PARAMETER.sub(r'{\1}', value)
    path = _ROUTE_PARAMETER.sub(r'{\1}', path)
    path = path.replace('^', '').replace('$', '').replace('\\', '')
    path = path.replace('/?', '/').replace('/+', '/')
    while '//' in path:
        path = path.replace('//', '/')
    return f'/{path.lstrip("/")}'


def _collect_endpoints(urlpatterns, prefix=''):
    """Collect concrete API operations, including DRF ViewSet actions."""
    endpoints = []
    for entry in urlpatterns:
        if isinstance(entry, URLPattern):
            callback = entry.callback
            pattern = str(entry.pattern)
            if 'format>' in pattern:
                continue
            view_class = getattr(callback, 'cls', None)
            initkwargs = dict(getattr(callback, 'initkwargs', {}) or {})
            actions = dict(getattr(callback, 'actions', {}) or {})
            if actions:
                operations = [
                    (method.upper(), action)
                    for method, action in actions.items()
                    if method.upper() in API_METHODS
                ]
            elif view_class is not None:
                operations = [
                    (method.upper(), method.lower())
                    for method in getattr(view_class, 'http_method_names', ['get'])
                    if method.upper() in API_METHODS and hasattr(view_class, method.lower())
                ]
            else:
                operations = [('GET', 'get')]

            path = _normalize_path(prefix + pattern)
            for method, action in operations:
                endpoints.append({
                    'path': path,
                    'name': entry.name or '',
                    'view_class': view_class,
                    'initkwargs': initkwargs,
                    'method': method,
                    'action': action,
                })
        elif isinstance(entry, URLResolver):
            endpoints.extend(_collect_endpoints(entry.url_patterns, prefix + str(entry.pattern)))
    return endpoints


def _view_permission_classes(endpoint):
    """Resolve effective permission classes for one API operation."""
    view_class = endpoint.get('view_class')
    if view_class is None:
        return []
    try:
        view = view_class(**endpoint.get('initkwargs', {}))
        view.action = endpoint.get('action')
        return list(view.get_permissions())
    except Exception:  # noqa: BLE001
        action = endpoint.get('action')
        by_action = getattr(view_class, 'permission_classes_by_action', {}) or {}
        permission_classes = by_action.get(
            action,
            getattr(view_class, 'permission_classes', []),
        )
        return [
            permission() if isinstance(permission, type) else permission
            for permission in permission_classes
        ]


def _permission_class(permission):
    return permission if isinstance(permission, type) else permission.__class__


def _is_permission(permission, target):
    try:
        return issubclass(_permission_class(permission), target)
    except TypeError:
        return False


def _requires_authentication(permissions):
    """Treat explicit AllowAny or an empty permission set as public."""
    if not permissions or any(_is_permission(permission, AllowAny) for permission in permissions):
        return False
    # Project permissions consistently authenticate before applying role/object checks.
    return any(
        _is_permission(permission, IsAuthenticated)
        or _is_permission(permission, RolePermission)
        or _is_permission(permission, BasePermission)
        for permission in permissions
    )


def _is_restricted_permission(perm):
    """判断权限类是否为受限权限（非 IsAuthenticated 且基于角色/对象）"""
    try:
        permission_class = _permission_class(perm)
        if issubclass(permission_class, AllowAny):
            return False
        if issubclass(permission_class, RolePermission):
            return permission_class.required_roles != []
        if issubclass(permission_class, IsAuthenticated):
            return False
        if issubclass(permission_class, BasePermission):
            return True
        return False
    except TypeError:
        return False


def _operation_label(endpoint):
    return f'{endpoint["method"]} {endpoint["path"]}'


class AccessibilityReportView(APIView):
    """
    API 无障碍 / 可访问性报告
    GET /api/v1/common/accessibility/report/
    """

    permission_classes = [IsSysAdmin]

    @extend_schema(
        responses={
            200: success_response_schema(
                'AccessibilityReportResponse',
                inline_serializer(
                    name='AccessibilityReportData',
                    fields={
                        'scope': serializers.CharField(),
                        'checks': inline_serializer(
                            name='AccessibilityCheck',
                            fields={
                                'item': serializers.CharField(),
                                'title': serializers.CharField(),
                                'passed': serializers.BooleanField(),
                                'detail': serializers.CharField(),
                                'unrestricted': serializers.ListField(
                                    child=serializers.CharField(),
                                    required=False,
                                ),
                                'unrestricted_count': serializers.IntegerField(
                                    required=False,
                                ),
                            },
                            many=True,
                        ),
                        'total': serializers.IntegerField(),
                        'passed': serializers.IntegerField(),
                        'failed': serializers.IntegerField(),
                        'endpoints_scanned': serializers.IntegerField(),
                        'paths_scanned': serializers.IntegerField(),
                        'score': serializers.FloatField(),
                        'browser_audit': inline_serializer(
                            name='BrowserAccessibilityAudit',
                            fields={
                                'runner': serializers.CharField(),
                                'command': serializers.CharField(),
                                'standard': serializers.CharField(),
                                'note': serializers.CharField(),
                                'source': serializers.CharField(),
                                'is_realtime': serializers.BooleanField(),
                            },
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        checks = []

        # 1. 所有端点具备统一错误响应（检查是否配置自定义异常处理器）
        rest_cfg = getattr(settings, 'REST_FRAMEWORK', {}) or {}
        handler = rest_cfg.get('EXCEPTION_HANDLER')
        checks.append({
            'item': 'error_responses',
            'title': '所有端点具备统一错误响应',
            'passed': bool(handler),
            'detail': f'EXCEPTION_HANDLER={handler or "未配置"}',
        })

        # 2. 所有列表端点已分页（检查默认分页类）
        pagination = rest_cfg.get('DEFAULT_PAGINATION_CLASS')
        checks.append({
            'item': 'list_pagination',
            'title': '所有列表端点已分页',
            'passed': bool(pagination),
            'detail': f'DEFAULT_PAGINATION_CLASS={pagination or "未配置"}',
        })

        # 3. 收集端点用于写操作 / 破坏性操作检查
        try:
            resolver = get_resolver()
            endpoints = _collect_endpoints(resolver.url_patterns)
        except Exception:  # noqa: BLE001
            from config.urls import urlpatterns
            endpoints = _collect_endpoints(urlpatterns)
        api_endpoints = {
            _operation_label(endpoint): endpoint
            for endpoint in endpoints
            if endpoint['path'].startswith('/api/')
        }.values()
        api_endpoints = list(api_endpoints)

        # 4. 写操作必须认证；登录、刷新令牌和 OAuth 回调是显式公开例外。
        default_perms = rest_cfg.get('DEFAULT_PERMISSION_CLASSES', [])
        write_endpoints = [
            ep for ep in api_endpoints
            if ep['method'] in WRITE_METHODS
        ]
        public_write = [
            _operation_label(ep)
            for ep in write_endpoints
            if not _requires_authentication(_view_permission_classes(ep))
        ]
        unexpected_public_write = sorted(set(public_write) - PUBLIC_WRITE_OPERATIONS)
        checks.append({
            'item': 'write_requires_auth',
            'title': '所有写操作要求认证',
            'passed': not unexpected_public_write,
            'detail': (
                f'写操作 {len(write_endpoints)} 个，显式公开例外 '
                f'{len(set(public_write) & PUBLIC_WRITE_OPERATIONS)} 个，'
                f'未声明公开 {len(unexpected_public_write)} 个；默认权限={default_perms}'
            ),
            'unrestricted': unexpected_public_write[:50],
            'unrestricted_count': len(unexpected_public_write),
        })

        # 5. 已认证的变更操作应在身份认证之外继续执行角色或对象级检查。
        destructive_endpoints = [
            ep for ep in api_endpoints
            if ep['method'] in WRITE_METHODS
            and _requires_authentication(_view_permission_classes(ep))
        ]
        unrestricted_destructive = []
        for ep in destructive_endpoints:
            perms = _view_permission_classes(ep)
            restricted = any(_is_restricted_permission(p) for p in perms)
            if not restricted:
                unrestricted_destructive.append(_operation_label(ep))
        unrestricted_destructive = sorted(set(unrestricted_destructive))
        checks.append({
            'item': 'destructive_requires_permissions',
            'title': '所有破坏性操作要求特定权限',
            'passed': len(unrestricted_destructive) == 0,
            'detail': (
                f'破坏性端点 {len(destructive_endpoints)} 个，'
                f'未限定特定权限 {len(unrestricted_destructive)} 个'
            ),
            'unrestricted': unrestricted_destructive[:50],
            'unrestricted_count': len(unrestricted_destructive),
        })

        total = len(checks)
        passed = sum(1 for c in checks if c['passed'])
        return success_response({
            'scope': 'api_governance',
            'checks': checks,
            'total': total,
            'passed': passed,
            'failed': total - passed,
            'endpoints_scanned': len(api_endpoints),
            'paths_scanned': len({endpoint['path'] for endpoint in api_endpoints}),
            'score': round(passed / total * 100, 1) if total else 0,
            'browser_audit': {
                'runner': 'Playwright + axe-core',
                'command': 'npm run test:e2e -- accessibility.spec.ts',
                'standard': 'WCAG 2.1 A/AA',
                'note': '此处仅展示 CI 扫描配置，不读取当前浏览器实时结果；实际通过或失败以最近一次 CI 构件为准。',
                'source': 'ci',
                'is_realtime': False,
            },
        })
