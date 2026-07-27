"""OpenAPI Schema 路由（N60）"""
from django.urls import path

from .openapi_views import (
    APIEndpointListView,
    OpenAPISchemaView,
)

urlpatterns = [
    path('schema/', OpenAPISchemaView.as_view(), name='openapi-schema'),
    path('endpoints/', APIEndpointListView.as_view(), name='api-endpoint-list'),
]
