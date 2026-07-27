"""
Open API 文档视图
- APIDocsView: 返回 API 文档信息（端点数量、Schema URL 等）

接口：
- GET /api/v1/common/api-docs/
"""
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from common.permissions import IsTeacherOrAdmin
from common.response import success_response
from common.schema import success_response_schema

# 文档元信息
API_INFO = {
    'title': '团队管理软件 API',
    'version': '2.1.0',
    'description': '团队管理软件后端 OpenAPI 文档信息',
    'schema_url': '/api/v1/common/openapi/schema/',
    'endpoint_index_url': '/api/v1/common/openapi/endpoints/',
}


class APIDocsView(APIView):
    """
    Open API 文档信息
    GET /api/v1/common/api-docs/
    """

    permission_classes = [IsTeacherOrAdmin]

    @extend_schema(
        responses={
            200: success_response_schema(
                'APIDocsResponse',
                inline_serializer(
                    name='APIDocsData',
                    fields={
                        'title': serializers.CharField(),
                        'version': serializers.CharField(),
                        'description': serializers.CharField(),
                        'endpoint_count': serializers.IntegerField(),
                        'schema_url': serializers.CharField(),
                        'endpoint_index_url': serializers.CharField(),
                    },
                ),
            ),
        },
    )
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
            'endpoint_index_url': API_INFO['endpoint_index_url'],
        })
