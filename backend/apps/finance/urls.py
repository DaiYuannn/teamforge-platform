"""
经费路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FinanceBudgetViewSet, FinanceExpenseViewSet, FinanceReceiptViewSet
from .alert_views import FinanceAlertView
from .trend_views import FinanceTrendView
from .ocr_views import OCRReceiptView

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'budgets', FinanceBudgetViewSet, basename='finance-budget')
router.register(r'expenses', FinanceExpenseViewSet, basename='finance-expense')
router.register(r'receipts', FinanceReceiptViewSet, basename='finance-receipt')

urlpatterns = [
    # 经费预警
    path('alerts/', FinanceAlertView.as_view(), name='finance-alert'),
    # 经费趋势分析
    path('trends/', FinanceTrendView.as_view(), name='finance-trend'),
    # OCR 票据识别
    path('ocr/recognize/', OCRReceiptView.as_view(), name='finance-ocr-recognize'),
    path('', include(router.urls)),
]
