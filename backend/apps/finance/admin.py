"""finance 应用的 Django Admin 配置"""
from django.contrib import admin

from .models import FinanceBudget, FinanceExpense, FinanceReceipt


@admin.register(FinanceBudget)
class FinanceBudgetAdmin(admin.ModelAdmin):
    """经费总表管理后台"""
    list_display = (
        'id', 'project', 'bonus_amount', 'other_income',
        'used_amount', 'pending_reimbursement', 'status', 'period', 'updated_at',
    )
    list_filter = ('status', 'period')
    search_fields = ('project__name',)
    raw_id_fields = ('project',)


@admin.register(FinanceExpense)
class FinanceExpenseAdmin(admin.ModelAdmin):
    """经费明细管理后台"""
    list_display = (
        'id', 'project', 'title', 'amount', 'spender',
        'expense_date', 'category', 'reviewer', 'created_at',
    )
    list_filter = ('category', 'expense_date')
    search_fields = ('title', 'purpose', 'project__name')
    raw_id_fields = ('project', 'spender', 'reviewer')


@admin.register(FinanceReceipt)
class FinanceReceiptAdmin(admin.ModelAdmin):
    """票据管理后台"""
    list_display = ('id', 'expense', 'file', 'uploaded_by', 'created_at')
    search_fields = ('expense__title',)
    raw_id_fields = ('expense', 'uploaded_by')
