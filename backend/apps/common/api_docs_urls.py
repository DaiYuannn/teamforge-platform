"""Open API 文档路由"""
from django.urls import path

from .api_docs_views import APIDocsView

urlpatterns = [
    path('', APIDocsView.as_view(), name='api-docs'),
]
