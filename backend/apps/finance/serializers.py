"""
经费序列化器
"""
from rest_framework import serializers

from .models import FinanceBudget, FinanceExpense, FinanceIncome, FinanceReceipt


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
    reimbursement_status_display = serializers.CharField(
        source='get_reimbursement_status_display', read_only=True
    )
    applied_by_name = serializers.CharField(source='applied_by.name', read_only=True, default='')
    paid_by_name = serializers.CharField(source='paid_by.name', read_only=True, default='')
    receipts = FinanceReceiptSerializer(many=True, read_only=True)

    class Meta:
        model = FinanceExpense
        fields = (
            'id', 'project', 'project_name', 'title', 'amount',
            'spender', 'spender_name', 'expense_date',
            'category', 'category_display', 'purpose',
            'reviewer', 'reviewer_name', 'receipts',
            'reimbursement_status', 'reimbursement_status_display',
            'applied_by', 'applied_by_name', 'applied_at',
            'reviewed_at', 'review_opinion',
            'paid_by', 'paid_by_name', 'paid_at',
            'payment_method', 'payment_reference',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'reimbursement_status',
            'applied_by', 'applied_at',
            'reviewed_at', 'review_opinion',
            'paid_by', 'paid_at', 'payment_method', 'payment_reference',
            'created_at', 'updated_at',
        )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('支出金额必须大于 0')
        return value


class FinanceExpenseListSerializer(serializers.ModelSerializer):
    """经费明细列表精简序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    spender_name = serializers.CharField(source='spender.name', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default='')
    applied_by_name = serializers.CharField(source='applied_by.name', read_only=True, default='')
    paid_by_name = serializers.CharField(source='paid_by.name', read_only=True, default='')
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    reimbursement_status_display = serializers.CharField(
        source='get_reimbursement_status_display', read_only=True
    )
    receipts = FinanceReceiptSerializer(many=True, read_only=True)

    class Meta:
        model = FinanceExpense
        fields = (
            'id', 'project', 'project_name', 'title', 'amount',
            'spender', 'spender_name', 'expense_date', 'category', 'category_display',
            'reimbursement_status', 'reimbursement_status_display',
            'applied_by', 'applied_by_name', 'applied_at',
            'reviewer', 'reviewer_name', 'reviewed_at', 'review_opinion',
            'paid_by', 'paid_by_name', 'paid_at',
            'payment_method', 'payment_reference',
            'receipts',
            'created_at',
        )
        read_only_fields = fields


class FinanceBudgetSerializer(serializers.ModelSerializer):
    """经费总表序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    committed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    budget_basis = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    available_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = FinanceBudget
        fields = (
            'id', 'project', 'project_name',
            'bonus_amount', 'other_income', 'planned_amount', 'used_amount',
            'pending_reimbursement', 'committed_amount',
            'remaining_amount', 'available_amount', 'budget_basis', 'total_income',
            'status', 'status_display', 'period', 'updated_at',
        )
        read_only_fields = ('id', 'updated_at')

    def validate_planned_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('核定预算上限不能为负数')
        return value


class FinanceIncomeSerializer(serializers.ModelSerializer):
    """收入流水序列化器。"""

    project_name = serializers.CharField(source='project.name', read_only=True)
    income_type_display = serializers.CharField(source='get_income_type_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True, default='')

    class Meta:
        model = FinanceIncome
        fields = (
            'id', 'project', 'project_name', 'title', 'amount',
            'income_type', 'income_type_display', 'income_date',
            'source', 'reference_number', 'note',
            'recorded_by', 'recorded_by_name', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'recorded_by', 'created_at', 'updated_at')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('收入金额必须大于 0')
        return value


class ReimbursementReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    opinion = serializers.CharField(required=False, allow_blank=True, default='')


class ReimbursementPaymentSerializer(serializers.Serializer):
    payment_method = serializers.CharField(max_length=50)
    payment_reference = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=''
    )
