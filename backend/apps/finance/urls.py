"""
经费路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FinanceBudgetViewSet,
    FinanceExpenseViewSet,
    FinanceIncomeViewSet,
    FinanceInternalTransferViewSet,
    FinancePaymentViewSet,
    FinanceReceiptViewSet,
)
from .alert_views import FinanceAlertView
from .trend_views import FinanceTrendView
from .ocr_views import OCRReceiptView
from .trace_views import (
    FinanceFundTodoView,
    FinanceTimelineView,
    FinanceTraceabilityDetailView,
    FinanceTraceabilitySummaryView,
)

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'budgets', FinanceBudgetViewSet, basename='finance-budget')
router.register(r'expenses', FinanceExpenseViewSet, basename='finance-expense')
router.register(r'incomes', FinanceIncomeViewSet, basename='finance-income')
router.register(r'receipts', FinanceReceiptViewSet, basename='finance-receipt')
router.register(r'payments', FinancePaymentViewSet, basename='finance-payment')
router.register(
    r'transfers',
    FinanceInternalTransferViewSet,
    basename='finance-transfer',
)

urlpatterns = [
    # 经费预警
    path('alerts/', FinanceAlertView.as_view(), name='finance-alert'),
    # 经费趋势分析
    path('trends/', FinanceTrendView.as_view(), name='finance-trend'),
    # OCR 票据识别
    path('ocr/recognize/', OCRReceiptView.as_view(), name='finance-ocr-recognize'),
    path(
        'traceability/summary/',
        FinanceTraceabilitySummaryView.as_view(),
        name='finance-traceability-summary',
    ),
    path(
        'traceability/detail/',
        FinanceTraceabilityDetailView.as_view(),
        name='finance-traceability-detail',
    ),
    path(
        'traceability/timeline/',
        FinanceTimelineView.as_view(),
        name='finance-traceability-timeline',
    ),
    path('fund-todos/', FinanceFundTodoView.as_view(), name='finance-fund-todos'),
    path('', include(router.urls)),
]
