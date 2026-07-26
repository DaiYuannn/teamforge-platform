"""
OpenAPI Schema 视图（N60）
- OpenAPISchemaView: 返回基于已注册 URL 模式生成的简易 JSON Schema
- APIEndpointListView: 返回所有 API 端点列表（路径 + 方法）

说明：项目未安装 drf_spectacular / drf-yasg，此处提供轻量自实现，
扫描 config.urls 中注册的全部路由，聚合端点与方法。
"""
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.views import APIView

from common.permissions import IsTeacherOrAdmin
from common.response import success_response


def _normalize_path(prefix, pattern):
    """拼接完整路径，清理多余斜杠"""
    full = prefix + str(pattern)
    return full


def _methods_for_callback(callback):
    """根据视图回调推断支持的 HTTP 方法"""
    cls = getattr(callback, 'cls', None)
    if cls is not None:
        # 类视图 / ViewSet
        method_names = getattr(cls, 'http_method_names', ['get'])
        methods = [m.upper() for m in method_names if hasattr(cls, m)]
        if not methods:
            methods = ['GET']
        return methods
    # 函数视图
    return ['GET']


def _collect_endpoints(urlpatterns, prefix=''):
    """递归收集所有端点（路径 + 方法 + 视图名）"""
    endpoints = []
    for entry in urlpatterns:
        if isinstance(entry, URLPattern):
            full = _normalize_path(prefix, entry.pattern)
            callback = entry.callback
            methods = _methods_for_callback(callback)
            view_name = ''
            cls = getattr(callback, 'cls', None)
            if cls is not None:
                view_name = cls.__name__
            else:
                view_name = getattr(callback, '__name__', '')
            endpoints.append({
                'path': full,
                'name': entry.name or '',
                'methods': methods,
                'view': view_name,
            })
        elif isinstance(entry, URLResolver):
            sub_prefix = _normalize_path(prefix, entry.pattern)
            endpoints.extend(_collect_endpoints(entry.url_patterns, sub_prefix))
    return endpoints


def _get_all_endpoints():
    """获取全部已注册端点"""
    try:
        resolver = get_resolver()
        return _collect_endpoints(resolver.url_patterns)
    except Exception:  # noqa: BLE001
        from config.urls import urlpatterns
        return _collect_endpoints(urlpatterns)


def _build_schema(endpoints):
    """构建简易 JSON Schema"""
    paths = {}
    for ep in endpoints:
        path = ep['path']
        paths.setdefault(path, {})
        for method in ep['methods']:
            method_lower = method.lower()
            if method_lower in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
                paths[path][method_lower] = {
                    'summary': ep['name'] or ep['view'],
                    'operationId': f"{method_lower}_{ep['name'] or ep['view']}".replace('-', '_'),
                }
    return {
        'openapi': '3.0.0',
        'info': {
            'title': '团队管理软件 API',
            'version': '2.0.0',
            'description': '由 apps/common/openapi_views 自动生成的简易 OpenAPI Schema',
        },
        'paths': paths,
    }


class OpenAPISchemaView(APIView):
    """
    OpenAPI Schema
    GET /api/v1/common/openapi/schema/
    返回基于已注册路由生成的简易 OpenAPI 3.0 JSON Schema
    """

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        endpoints = _get_all_endpoints()
        schema = _build_schema(endpoints)
        schema['endpoints_count'] = len(endpoints)
        return success_response(schema)


class APIEndpointListView(APIView):
    """
    API 端点列表
    GET /api/v1/common/openapi/endpoints/
    返回所有 API 端点（路径 + 方法 + 视图名）
    """

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        endpoints = _get_all_endpoints()
        # 过滤仅 API 路径
        api_endpoints = [ep for ep in endpoints if 'api' in ep['path']]
        return success_response({
            'endpoints': api_endpoints,
            'total': len(api_endpoints),
        })
