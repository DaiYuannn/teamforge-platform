"""
经费路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FinanceBudgetViewSet, FinanceExpenseViewSet, FinanceReceiptViewSet

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'budgets', FinanceBudgetViewSet, basename='finance-budget')
router.register(r'expenses', FinanceExpenseViewSet, basename='finance-expense')
router.register(r'receipts', FinanceReceiptViewSet, basename='finance-receipt')

urlpatterns = [
    path('', include(router.urls)),
]
