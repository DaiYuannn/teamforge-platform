"""Standards-compliant OpenAPI schema and protected operator documentation."""
from __future__ import annotations

from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.utils import extend_schema, inline_serializer
from drf_spectacular.views import SpectacularAPIView
from rest_framework import serializers
from rest_framework.views import APIView

from common.permissions import IsSysAdmin
from common.response import success_response
from common.schema import success_response_schema


class OpenAPISchemaView(SpectacularAPIView):
    """Return the raw OpenAPI document so validators and SDK tools can consume it."""

    permission_classes = [IsSysAdmin]
    renderer_classes = [OpenApiJsonRenderer]


class APIEndpointListView(APIView):
    """Return an operator-friendly endpoint index derived from the same schema."""

    permission_classes = [IsSysAdmin]

    @extend_schema(
        responses={
            200: success_response_schema(
                'APIEndpointListResponse',
                inline_serializer(
                    name='APIEndpointListData',
                    fields={
                        'endpoints': inline_serializer(
                            name='APIEndpointSummary',
                            fields={
                                'path': serializers.CharField(),
                                'methods': serializers.ListField(
                                    child=serializers.CharField(),
                                ),
                                'operations': serializers.DictField(
                                    child=serializers.JSONField(),
                                ),
                            },
                            many=True,
                        ),
                        'total': serializers.IntegerField(),
                        'schema_url': serializers.URLField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        schema = SchemaGenerator().get_schema(request=request, public=True)
        endpoints = []
        for path, operations in sorted(schema.get('paths', {}).items()):
            methods = [
                method.upper()
                for method in operations
                if method.lower() in {'get', 'post', 'put', 'patch', 'delete'}
            ]
            if not methods:
                continue
            endpoints.append({
                'path': path,
                'methods': methods,
                'operations': {
                    method.upper(): {
                        'operation_id': operation.get('operationId', ''),
                        'summary': operation.get('summary', ''),
                        'tags': operation.get('tags', []),
                    }
                    for method, operation in operations.items()
                    if method.lower() in {'get', 'post', 'put', 'patch', 'delete'}
                },
            })
        return success_response({
            'endpoints': endpoints,
            'total': len(endpoints),
            'schema_url': request.build_absolute_uri('/api/v1/common/openapi/schema/'),
        })
