"""
数据导出路由（架构预留）
"""
from django.urls import path

from .views import ExportView, ExportTemplateView

urlpatterns = [
    # 导出数据
    path('', ExportView.as_view(), name='export'),
    # 下载导入模板
    path('template/', ExportTemplateView.as_view(), name='export-template'),
]
