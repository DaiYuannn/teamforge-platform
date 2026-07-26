"""
驾驶舱路由
- /: 基础驾驶舱聚合数据
- timeline/: 统一时间线聚合
- competition-matrix/: 比赛矩阵
- competition-funnel/: 比赛晋级漏斗
- calendar/: 项目日历
- gantt/: 项目 Gantt 历程条
- custom/: N48 自定义看板（CRUD + set_default）
- weekly-report/: N53 智能周报
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import DashboardView, SystemInfoView
from .timeline_views import (
    TimelineEventView,
    CompetitionMatrixView,
    CompetitionFunnelView,
    ProjectCalendarView,
    ProjectGanttView,
    PublicPortalView,
)
from .search_views import GlobalSearchView
from .custom_dashboard_views import CustomDashboardViewSet
from .weekly_report_views import WeeklyReportView
from .portal_views import (
    PortalManagementView,
    PortalMemberConsentView,
    PortalPublicationView,
)

# N48: 自定义看板路由
custom_dashboard_router = DefaultRouter()
custom_dashboard_router.register(
    r'custom', CustomDashboardViewSet, basename='custom-dashboard'
)

urlpatterns = [
    # 驾驶舱聚合数据
    path('', DashboardView.as_view(), name='dashboard'),
    # P19: 系统信息
    path('system-info/', SystemInfoView.as_view(), name='system-info'),
    # P1: 统一时间线聚合
    path('timeline/', TimelineEventView.as_view(), name='timeline-events'),
    # P1: 比赛矩阵
    path('competition-matrix/', CompetitionMatrixView.as_view(), name='competition-matrix'),
    # P1: 比赛晋级漏斗
    path('competition-funnel/', CompetitionFunnelView.as_view(), name='competition-funnel'),
    # P1: 项目日历
    path('calendar/', ProjectCalendarView.as_view(), name='project-calendar'),
    # P1: 项目 Gantt 历程条
    path('gantt/', ProjectGanttView.as_view(), name='project-gantt'),
    # P2: 公共展示主页(无需认证)
    path('public-portal/', PublicPortalView.as_view(), name='public-portal'),
    path('public-portal/manage/', PortalManagementView.as_view(), name='public-portal-manage'),
    path(
        'public-portal/publications/<str:content_type>/<int:object_id>/',
        PortalPublicationView.as_view(),
        name='public-portal-publication',
    ),
    path(
        'public-portal/member-consent/',
        PortalMemberConsentView.as_view(),
        name='public-portal-member-consent',
    ),
    # M07: 全局搜索
    path('search/', GlobalSearchView.as_view(), name='global-search'),
    # N48: 自定义看板 CRUD + set_default
    path('', include(custom_dashboard_router.urls)),
    # N53: 智能周报
    path('weekly-report/', WeeklyReportView.as_view(), name='weekly-report'),
]
