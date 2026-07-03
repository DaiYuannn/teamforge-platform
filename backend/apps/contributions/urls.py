"""
贡献度路由
- contributions: 贡献记录
- rankings: 成员排名
- objections: 排名异议
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ContributionViewSet,
    MemberRankingViewSet,
    RankingObjectionViewSet,
)

router = DefaultRouter()
router.register(r'contributions', ContributionViewSet, basename='contribution')
router.register(r'rankings', MemberRankingViewSet, basename='ranking')
router.register(r'objections', RankingObjectionViewSet, basename='ranking-objection')

urlpatterns = [
    path('', include(router.urls)),
]
