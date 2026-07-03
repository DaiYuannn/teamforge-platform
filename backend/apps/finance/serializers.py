"""
经费序列化器
"""
from rest_framework import serializers

from .models import FinanceBudget, FinanceExpense, FinanceReceipt


class FinanceReceiptSerializer(serializers.ModelSerializer):
    """票据序列化器"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True, default='')

    class Meta:
        model = FinanceReceipt
        fields = ('id', 'expense', 'file', 'uploaded_by', 'uploaded_by_name', 'created_at')
        read_only_fields = ('id', 'uploaded_by', 'created_at')


class FinanceExpenseSerializer(serializers.ModelSerializer):
    """经费明细序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    spender_name = serializers.CharField(source='spender.name', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default='')
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    receipts = FinanceReceiptSerializer(many=True, read_only=True)

    class Meta:
        model = FinanceExpense
        fields = (
            'id', 'project', 'project_name', 'title', 'amount',
            'spender', 'spender_name', 'expense_date',
            'category', 'category_display', 'purpose',
            'reviewer', 'reviewer_name', 'receipts',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class FinanceExpenseListSerializer(serializers.ModelSerializer):
    """经费明细列表精简序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    spender_name = serializers.CharField(source='spender.name', read_only=True, default='')
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = FinanceExpense
        fields = (
            'id', 'project', 'project_name', 'title', 'amount',
            'spender_name', 'expense_date', 'category', 'category_display',
            'created_at',
        )
        read_only_fields = fields


class FinanceBudgetSerializer(serializers.ModelSerializer):
    """经费总表序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = FinanceBudget
        fields = (
            'id', 'project', 'project_name',
            'bonus_amount', 'other_income', 'used_amount',
            'pending_reimbursement', 'remaining_amount', 'total_income',
            'status', 'status_display', 'period', 'updated_at',
        )
        read_only_fields = ('id', 'updated_at')
