"""
数据导出路由（架构预留）
- N49: 自定义报表 CRUD + generate
- N50: 定时报表 CRUD + run_now/activate/deactivate
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ExportView, ExportTemplateView
from .report_views import ProjectReportView
from .custom_report_views import CustomReportViewSet, ScheduledReportViewSet

# N49/N50: 自定义报表 & 定时报表路由
exports_router = DefaultRouter()
exports_router.register(
    r'custom-reports', CustomReportViewSet, basename='custom-report'
)
exports_router.register(
    r'scheduled-reports', ScheduledReportViewSet, basename='scheduled-report'
)

urlpatterns = [
    # 导出数据
    path('', ExportView.as_view(), name='export'),
    # 下载导入模板
    path('template/', ExportTemplateView.as_view(), name='export-template'),
    # 项目完整报告导出（Word）
    path('project-report/<int:project_id>/', ProjectReportView.as_view(), name='project-report'),
    # N49: 自定义报表 & N50: 定时报表
    path('', include(exports_router.urls)),
]
