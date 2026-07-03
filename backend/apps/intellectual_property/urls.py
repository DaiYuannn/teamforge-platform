"""
知识产权管理路由
- applications: 知识产权申请
- contributors: 责任分工
- returns: 退回记录
- materials: 材料版本
- objections: 异议
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    IPApplicationViewSet,
    IPContributorViewSet,
    IPReturnRecordViewSet,
    IPMaterialVersionViewSet,
    IPObjectionViewSet,
)

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'applications', IPApplicationViewSet, basename='ip-applications')
router.register(r'contributors', IPContributorViewSet, basename='ip-contributors')
router.register(r'returns', IPReturnRecordViewSet, basename='ip-returns')
router.register(r'materials', IPMaterialVersionViewSet, basename='ip-materials')
router.register(r'objections', IPObjectionViewSet, basename='ip-objections')

urlpatterns = [
    path('', include(router.urls)),
]
