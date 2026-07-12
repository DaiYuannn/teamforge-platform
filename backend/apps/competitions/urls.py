"""
比赛路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CompetitionViewSet
from .statistics_views import CompetitionStatisticsView
from .timeline_views import CompetitionTimelineView
from .comparison_views import CompetitionComparisonView

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'', CompetitionViewSet, basename='competition')

urlpatterns = [
    # 比赛统计
    path('statistics/', CompetitionStatisticsView.as_view(), name='competition-statistics'),
    # 比赛时间线
    path('timeline/', CompetitionTimelineView.as_view(), name='competition-timeline'),
    # 比赛对比
    path('comparison/', CompetitionComparisonView.as_view(), name='competition-comparison'),
    path('', include(router.urls)),
]
