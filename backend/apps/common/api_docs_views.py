"""
Open API 文档视图
- APIDocsView: 返回 API 文档信息（端点数量、Schema URL 等）

接口：
- GET /api/v1/common/api-docs/
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response

# 文档元信息
API_INFO = {
    'title': '团队管理软件 API',
    'version': '2.0.0',
    'description': '团队管理软件后端 OpenAPI 文档信息',
    'schema_url': '/api/schema/',
    'docs_url': '/api/docs/',
    'redoc_url': '/api/redoc/',
}


class APIDocsView(APIView):
    """
    Open API 文档信息
    GET /api/v1/common/api-docs/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 统计已注册的 URL 端点数量（API 路径）
        from config.urls import urlpatterns as top_urls

        def _count_urls(urlpatterns, prefix=''):
            total = 0
            endpoints = []
            for entry in urlpatterns:
                try:
                    pattern = entry.pattern
                except AttributeError:
                    continue
                if hasattr(entry, 'url_patterns'):
                    sub_total, sub_eps = _count_urls(entry.url_patterns, prefix + str(pattern))
                    total += sub_total
                    endpoints.extend(sub_eps)
                else:
                    full = prefix + str(pattern)
                    # 统计所有 API 路径端点
                    if 'api' in full or 'api' in prefix:
                        total += 1
                        endpoints.append(full)
            return total, endpoints

        endpoint_count, _ = _count_urls(top_urls)

        return success_response({
            'title': API_INFO['title'],
            'version': API_INFO['version'],
            'description': API_INFO['description'],
            'endpoint_count': endpoint_count,
            'schema_url': API_INFO['schema_url'],
            'docs_url': API_INFO['docs_url'],
            'redoc_url': API_INFO['redoc_url'],
        })
