"""
外部平台集成路由
- /api/v1/integrations/external-platforms/   外部平台 CRUD
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .external_views import ExternalPlatformViewSet

external_router = DefaultRouter()
external_router.register(r'', ExternalPlatformViewSet, basename='external-platform')

urlpatterns = [
    path('', include(external_router.urls)),
]
