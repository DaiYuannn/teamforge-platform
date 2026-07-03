"""
敏感资料路由（架构预留）
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SensitiveDataViewSet, SensitiveAccessRequestViewSet

router = DefaultRouter()
router.register(r'data', SensitiveDataViewSet, basename='sensitive-data')
router.register(r'requests', SensitiveAccessRequestViewSet, basename='sensitive-request')

urlpatterns = [
    path('', include(router.urls)),
]
