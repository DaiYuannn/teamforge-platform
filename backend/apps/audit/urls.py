"""
审计日志路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OperationLogViewSet

router = DefaultRouter()
router.register(r'operation-logs', OperationLogViewSet, basename='operation-log')

urlpatterns = [
    path('', include(router.urls)),
]
