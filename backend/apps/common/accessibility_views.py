"""
无障碍 / API 可访问性报告视图（N61）
- AccessibilityReportView: 返回 API 无障碍检查清单
  - 所有端点具备统一错误响应
  - 所有列表端点已分页
  - 所有写操作要求认证
  - 所有破坏性操作要求特定权限

接口：
- GET /api/v1/common/accessibility/report/
"""
from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.views import APIView

from common.permissions import RolePermission
from common.response import success_response


WRITE_METHODS = {'POST', 'PUT', 'PATCH'}
DESTRUCTIVE_METHODS = {'DELETE', 'POST', 'PUT', 'PATCH'}


def _collect_endpoints(urlpatterns, prefix=''):
    """递归收集端点（路径 + 方法 + 视图类）"""
    endpoints = []
    for entry in urlpatterns:
        if isinstance(entry, URLPattern):
            cls = getattr(entry.callback, 'cls', None)
            method_names = getattr(cls, 'http_method_names', ['get']) if cls else ['get']
            methods = [m.upper() for m in method_names if cls is None or hasattr(cls, m)]
            endpoints.append({
                'path': prefix + str(entry.pattern),
                'name': entry.name or '',
                'view_class': cls,
                'methods': methods or ['GET'],
            })
        elif isinstance(entry, URLResolver):
            endpoints.extend(_collect_endpoints(entry.url_patterns, prefix + str(entry.pattern)))
    return endpoints


def _view_permission_classes(view_class):
    """获取视图类的权限类列表"""
    if view_class is None:
        return []
    perms = getattr(view_class, 'permission_classes', [])
    # permission_classes 可能是列表/元组
    return list(perms)


def _is_restricted_permission(perm):
    """判断权限类是否为受限权限（非 IsAuthenticated 且基于角色/对象）"""
    try:
        if isinstance(perm, type):
            if issubclass(perm, RolePermission):
                return perm.required_roles != []  # 明确限定角色
            if issubclass(perm, BasePermission) and perm is not IsAuthenticated:
                return True
        return False
    except TypeError:
        return False


class AccessibilityReportView(APIView):
    """
    API 无障碍 / 可访问性报告
    GET /api/v1/common/accessibility/report/
    """

    permission_classes = [IsAuthenticated]

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
        api_endpoints = [ep for ep in endpoints if 'api' in ep['path']]

        # 4. 所有写操作要求认证（默认权限类为 IsAuthenticated）
        default_perms = rest_cfg.get('DEFAULT_PERMISSION_CLASSES', [])
        write_requires_auth = any(
            'IsAuthenticated' in str(p) for p in default_perms
        )
        # 同时扫描是否存在未显式覆盖权限的写端点（启发式：默认即可）
        write_endpoints = [
            ep for ep in api_endpoints
            if set(ep['methods']) & WRITE_METHODS
        ]
        checks.append({
            'item': 'write_requires_auth',
            'title': '所有写操作要求认证',
            'passed': write_requires_auth,
            'detail': f'写端点 {len(write_endpoints)} 个，默认权限={default_perms}',
        })

        # 5. 所有破坏性操作要求特定权限
        destructive_endpoints = [
            ep for ep in api_endpoints
            if set(ep['methods']) & DESTRUCTIVE_METHODS
        ]
        unrestricted_destructive = []
        for ep in destructive_endpoints:
            perms = _view_permission_classes(ep['view_class'])
            # 启发式：若权限仅含 IsAuthenticated（或为空且默认仅 IsAuthenticated），视为未限定特定权限
            restricted = any(_is_restricted_permission(p) for p in perms)
            if not restricted:
                unrestricted_destructive.append(ep['path'])
        checks.append({
            'item': 'destructive_requires_permissions',
            'title': '所有破坏性操作要求特定权限',
            'passed': len(unrestricted_destructive) == 0,
            'detail': (
                f'破坏性端点 {len(destructive_endpoints)} 个，'
                f'未限定特定权限 {len(unrestricted_destructive)} 个'
            ),
            'unrestricted': unrestricted_destructive[:20],
        })

        total = len(checks)
        passed = sum(1 for c in checks if c['passed'])
        return success_response({
            'checks': checks,
            'total': total,
            'passed': passed,
            'failed': total - passed,
            'endpoints_scanned': len(api_endpoints),
            'score': round(passed / total * 100, 1) if total else 0,
        })
