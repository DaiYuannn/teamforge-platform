"""
贡献度路由
- contributions: 贡献记录
- rankings: 成员排名
- objections: 排名异议
- statistics: 贡献度统计
- leaderboard: 贡献度排行榜
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ContributionViewSet,
    ProjectContributionReviewerViewSet,
    MemberRankingViewSet,
    RankingObjectionViewSet,
)
from .statistics_views import ContributionStatisticsView
from .leaderboard_views import ContributionLeaderboardView

router = DefaultRouter()
router.register(r'contributions', ContributionViewSet, basename='contribution')
router.register(
    r'project-reviewers',
    ProjectContributionReviewerViewSet,
    basename='project-contribution-reviewer',
)
router.register(r'rankings', MemberRankingViewSet, basename='ranking')
router.register(r'objections', RankingObjectionViewSet, basename='ranking-objection')

urlpatterns = [
    # 贡献度统计
    path('statistics/', ContributionStatisticsView.as_view(), name='contribution-statistics'),
    # 贡献度排行榜
    path('leaderboard/', ContributionLeaderboardView.as_view(), name='contribution-leaderboard'),
    path('', include(router.urls)),
]
