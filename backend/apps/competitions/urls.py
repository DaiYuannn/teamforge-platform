"""
比赛路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CompetitionEventViewSet, CompetitionViewSet
from .statistics_views import CompetitionStatisticsView
from .timeline_views import CompetitionTimelineView
from .comparison_views import CompetitionComparisonView

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'', CompetitionViewSet, basename='competition')
event_router = DefaultRouter()
event_router.register(r'', CompetitionEventViewSet, basename='competition-event')

urlpatterns = [
    path('events/', include(event_router.urls)),
    # 比赛统计
    path('statistics/', CompetitionStatisticsView.as_view(), name='competition-statistics'),
    # 比赛时间线
    path('timeline/', CompetitionTimelineView.as_view(), name='competition-timeline'),
    # 比赛对比
    path('comparison/', CompetitionComparisonView.as_view(), name='competition-comparison'),
    path('', include(router.urls)),
]
