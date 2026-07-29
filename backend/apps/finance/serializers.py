"""Finance serializers for the project/competition-entry traceable ledger."""

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.competitions.models import Competition
from .models import (
    FinanceBudget,
    FinanceExpense,
    FinanceExpenseAllocation,
    FinanceIncome,
    FinanceIncomeAllocation,
    FinanceInternalTransfer,
    FinanceLedgerEvent,
    FinancePayment,
    FinanceReceipt,
)
from .permissions import can_manage_finance, can_pay_finance, can_review_expense
from .services import (
    complete_internal_transfer,
    complete_payment,
    fail_payment,
    record_finance_event,
)


def _raise_drf_validation(exc):
    if hasattr(exc, 'message_dict'):
        raise serializers.ValidationError(exc.message_dict)
    raise serializers.ValidationError(
        getattr(exc, 'messages', None) or str(exc)
    )


class FinanceExpenseAllocationSerializer(serializers.ModelSerializer):
    competition_entry_name = serializers.CharField(
        source='competition_entry.entry_name',
        read_only=True,
        default='',
    )
    event = serializers.IntegerField(
        source='competition_entry.event_id',
        read_only=True,
    )
    event_name = serializers.CharField(
        source='competition_entry.event.name',
        read_only=True,
        default='',
    )
    event_edition = serializers.CharField(
        source='competition_entry.event.edition',
        read_only=True,
        default='',
    )
    project = serializers.IntegerField(
        source='competition_entry.project_id',
        read_only=True,
    )
    project_name = serializers.CharField(
        source='competition_entry.project.name',
        read_only=True,
    )

    class Meta:
        model = FinanceExpenseAllocation
        fields = (
            'id', 'competition_entry', 'competition_entry_name',
            'event', 'event_name', 'event_edition',
            'project', 'project_name',
            'amount', 'note', 'created_at',
        )
        read_only_fields = fields


class FinanceIncomeAllocationSerializer(serializers.ModelSerializer):
    competition_entry_name = serializers.CharField(
        source='competition_entry.entry_name',
        read_only=True,
        default='',
    )
    event = serializers.IntegerField(
        source='competition_entry.event_id',
        read_only=True,
    )
    event_name = serializers.CharField(
        source='competition_entry.event.name',
        read_only=True,
        default='',
    )
    event_edition = serializers.CharField(
        source='competition_entry.event.edition',
        read_only=True,
        default='',
    )
    project = serializers.IntegerField(
        source='competition_entry.project_id',
        read_only=True,
    )
    project_name = serializers.CharField(
        source='competition_entry.project.name',
        read_only=True,
    )

    class Meta:
        model = FinanceIncomeAllocation
        fields = (
            'id', 'competition_entry', 'competition_entry_name',
            'event', 'event_name', 'event_edition',
            'project', 'project_name',
            'amount', 'note', 'created_at',
        )
        read_only_fields = fields


class AllocationItemSerializer(serializers.Serializer):
    competition_entry = serializers.PrimaryKeyRelatedField(
        queryset=Competition.objects.select_related(
            'project__leader',
            'event__organization',
        ),
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('分摊金额必须大于 0')
        return value


class AllocationReplaceSerializer(serializers.Serializer):
    allocations = AllocationItemSerializer(many=True, allow_empty=True)


class FinanceReceiptSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(
        source='uploaded_by.name',
        read_only=True,
        default='',
    )
    attachment_type_display = serializers.CharField(
        source='get_attachment_type_display',
        read_only=True,
    )

    class Meta:
        model = FinanceReceipt
        fields = (
            'id', 'expense', 'income', 'payment', 'internal_transfer',
            'attachment_type', 'attachment_type_display',
            'file', 'uploaded_by', 'uploaded_by_name', 'created_at',
        )
        read_only_fields = ('id', 'uploaded_by', 'created_at')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        owners = [
            attrs.get('expense'),
            attrs.get('income'),
            attrs.get('payment'),
            attrs.get('internal_transfer'),
        ]
        if self.instance:
            owners = [
                attrs.get('expense', self.instance.expense),
                attrs.get('income', self.instance.income),
                attrs.get('payment', self.instance.payment),
                attrs.get(
                    'internal_transfer',
                    self.instance.internal_transfer,
                ),
            ]
        if sum(owner is not None for owner in owners) != 1:
            raise serializers.ValidationError(
                '附件必须且只能关联一项资金记录'
            )
        attachment_type = attrs.get(
            'attachment_type',
            getattr(self.instance, 'attachment_type', None),
        )
        if owners[2] and attachment_type != FinanceReceipt.AttachmentType.PAYMENT_PROOF:
            raise serializers.ValidationError({
                'attachment_type': '付款附件必须使用付款回单类型',
            })
        if owners[1] and attachment_type != FinanceReceipt.AttachmentType.INCOME_PROOF:
            raise serializers.ValidationError({
                'attachment_type': '收入附件必须使用到账凭证类型',
            })
        if owners[3] and attachment_type != FinanceReceipt.AttachmentType.TRANSFER_PROOF:
            raise serializers.ValidationError({
                'attachment_type': '内部转移附件必须使用内部转账凭证类型',
            })
        return attrs


class FinancePaymentSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(
        source='recipient.name',
        read_only=True,
        default='',
    )
    paid_by_name = serializers.CharField(
        source='paid_by.name',
        read_only=True,
        default='',
    )
    expense_title = serializers.CharField(
        source='expense.title',
        read_only=True,
    )
    project = serializers.IntegerField(
        source='expense.project_id',
        read_only=True,
    )
    project_name = serializers.CharField(
        source='expense.project.name',
        read_only=True,
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
    )
    receipts = FinanceReceiptSerializer(many=True, read_only=True)
    proof_file = serializers.FileField(write_only=True, required=False)
    payment_date = serializers.DateTimeField(write_only=True, required=False)
    can_complete = serializers.SerializerMethodField()
    can_fail = serializers.SerializerMethodField()

    class Meta:
        model = FinancePayment
        fields = (
            'id', 'expense', 'expense_title', 'project', 'project_name',
            'recipient', 'recipient_name', 'amount',
            'status', 'status_display',
            'payment_method', 'payment_reference',
            'paid_by', 'paid_by_name', 'paid_at',
            'failure_reason', 'receipts', 'proof_file',
            'payment_date',
            'can_complete', 'can_fail', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'paid_by', 'paid_at', 'created_at', 'updated_at',
        )

    def get_can_complete(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and obj.status not in {
                FinancePayment.Status.COMPLETED,
                FinancePayment.Status.REVERSED,
            }
            and can_pay_finance(request.user, obj.expense.project)
        )

    def get_can_fail(self, obj):
        return self.get_can_complete(obj)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance
        expense = attrs.get('expense', getattr(instance, 'expense', None))
        if expense is None:
            return attrs
        if instance and instance.status in {
            FinancePayment.Status.COMPLETED,
            FinancePayment.Status.REVERSED,
        }:
            raise serializers.ValidationError('已完成或已冲正付款不可直接编辑')
        if (
            instance
            and 'expense' in attrs
            and attrs['expense'].id != instance.expense_id
        ):
            raise serializers.ValidationError({
                'expense': '付款记录创建后不能更换报销申请',
            })
        if (
            instance
            and 'status' in attrs
            and attrs['status'] != instance.status
        ):
            raise serializers.ValidationError({
                'status': '付款状态请使用 complete/fail 动作变更',
            })
        if expense.reimbursement_status not in {
            FinanceExpense.ReimbursementStatus.APPROVED,
            FinanceExpense.ReimbursementStatus.PARTIALLY_PAID,
            FinanceExpense.ReimbursementStatus.PAYMENT_EXCEPTION,
        }:
            raise serializers.ValidationError(
                '仅已审核、部分支付或付款异常的报销可登记付款'
            )
        recipient = attrs.get(
            'recipient',
            getattr(instance, 'recipient', None) or expense.payee or expense.spender,
        )
        if recipient is None:
            raise serializers.ValidationError({'recipient': '必须选择收款人'})
        if expense.payee_id and recipient.id != expense.payee_id:
            raise serializers.ValidationError({
                'recipient': '付款收款人必须与报销收款人一致',
            })
        attrs['recipient'] = recipient
        amount = attrs.get('amount', getattr(instance, 'amount', ZERO))
        completed_other = expense.paid_amount
        if instance and instance.status == FinancePayment.Status.COMPLETED:
            completed_other -= instance.amount
        if completed_other + amount > expense.amount:
            raise serializers.ValidationError({
                'amount': '累计付款金额不能超过报销申请金额',
            })
        desired_status = attrs.get(
            'status',
            getattr(instance, 'status', FinancePayment.Status.PENDING_PROOF),
        )
        proof_file = attrs.get('proof_file')
        if desired_status == FinancePayment.Status.COMPLETED and not proof_file:
            raise serializers.ValidationError({
                'proof_file': '登记已付款必须上传转账凭证',
            })
        if (
            desired_status == FinancePayment.Status.FAILED
            and not str(attrs.get('failure_reason', '') or '').strip()
        ):
            raise serializers.ValidationError({
                'failure_reason': '付款异常必须填写原因',
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        proof_file = validated_data.pop('proof_file', None)
        payment_date = validated_data.pop('payment_date', None)
        desired_status = validated_data.pop(
            'status',
            FinancePayment.Status.PENDING_PROOF,
        )
        request = self.context['request']
        payment = FinancePayment.objects.create(
            **validated_data,
            status=FinancePayment.Status.PENDING_PROOF,
            paid_by=request.user,
            paid_at=payment_date,
        )
        record_finance_event(
            project=payment.expense.project,
            event_type='payment_created',
            actor=request.user,
            expense=payment.expense,
            payment=payment,
            amount=payment.amount,
            to_status=payment.status,
            description='付款已登记，尚未归档付款凭证',
        )
        if desired_status == FinancePayment.Status.COMPLETED:
            payment, _ = complete_payment(
                payment,
                proof_file=proof_file,
                actor=request.user,
            )
        elif desired_status == FinancePayment.Status.FAILED:
            payment, _ = fail_payment(
                payment,
                reason=validated_data.get('failure_reason', ''),
                actor=request.user,
            )
        return payment


ZERO = Decimal('0')


class FinanceExpenseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    competition_entry_name = serializers.CharField(
        source='competition_entry.entry_name',
        read_only=True,
        default='',
    )
    event = serializers.IntegerField(
        source='competition_entry.event_id',
        read_only=True,
        allow_null=True,
    )
    event_name = serializers.CharField(
        source='competition_entry.event.name',
        read_only=True,
        default='',
    )
    event_edition = serializers.CharField(
        source='competition_entry.event.edition',
        read_only=True,
        default='',
    )
    spender_name = serializers.CharField(source='spender.name', read_only=True, default='')
    payee_name = serializers.CharField(source='payee.name', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default='')
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    reimbursement_status_display = serializers.CharField(
        source='get_reimbursement_status_display',
        read_only=True,
    )
    applied_by_name = serializers.CharField(source='applied_by.name', read_only=True, default='')
    paid_by_name = serializers.CharField(source='paid_by.name', read_only=True, default='')
    receipts = FinanceReceiptSerializer(many=True, read_only=True)
    payments = FinancePaymentSerializer(many=True, read_only=True)
    allocations = FinanceExpenseAllocationSerializer(many=True, read_only=True)
    scope = serializers.CharField(source='fund_scope', read_only=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_payable = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    can_manage = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    can_pay = serializers.SerializerMethodField()

    class Meta:
        model = FinanceExpense
        fields = (
            'id', 'project', 'project_name',
            'competition_entry', 'competition_entry_name',
            'event', 'event_name', 'event_edition',
            'scope', 'title', 'amount',
            'spender', 'spender_name', 'payee', 'payee_name', 'expense_date',
            'category', 'category_display', 'purpose',
            'reviewer', 'reviewer_name', 'receipts', 'payments', 'allocations',
            'reimbursement_status', 'reimbursement_status_display',
            'applied_by', 'applied_by_name', 'applied_at',
            'reviewed_at', 'review_opinion',
            'paid_by', 'paid_by_name', 'paid_at',
            'payment_method', 'payment_reference',
            'paid_amount', 'remaining_payable',
            'can_manage', 'can_review', 'can_pay',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'reimbursement_status',
            'applied_by', 'applied_at',
            'reviewer', 'reviewed_at', 'review_opinion',
            'paid_by', 'paid_at', 'payment_method', 'payment_reference',
            'created_at', 'updated_at',
        )

    def get_can_manage(self, obj):
        request = self.context.get('request')
        return bool(request and can_manage_finance(request.user, obj.project))

    def get_can_review(self, obj):
        request = self.context.get('request')
        return bool(request and can_review_expense(request.user, obj))

    def get_can_pay(self, obj):
        request = self.context.get('request')
        return bool(request and can_pay_finance(request.user, obj.project))

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('支出金额必须大于 0')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get('project', getattr(self.instance, 'project', None))
        entry = attrs.get(
            'competition_entry',
            getattr(self.instance, 'competition_entry', None),
        )
        if entry and project and entry.project_id != project.id:
            raise serializers.ValidationError({
                'competition_entry': '参赛条目必须属于所选项目',
            })
        if (
            entry
            and self.instance
            and self.instance.allocations.exists()
        ):
            raise serializers.ValidationError({
                'competition_entry': '已有分摊的支出不能直接关联参赛条目',
            })
        if self.instance and self.instance.allocations.exists():
            if (
                project
                and project.id != self.instance.project_id
            ):
                raise serializers.ValidationError({
                    'project': '已有分摊的支出需先清空分摊后才能更换锚点项目',
                })
            amount = attrs.get('amount', self.instance.amount)
            allocated_total = sum(
                (
                    allocation.amount
                    for allocation in self.instance.allocations.all()
                ),
                ZERO,
            )
            if amount != allocated_total:
                raise serializers.ValidationError({
                    'amount': '支出金额必须与现有分摊合计一致，请先更新分摊',
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        if not validated_data.get('payee'):
            validated_data['payee'] = validated_data.get('spender')
        return super().create(validated_data)


class FinanceExpenseListSerializer(FinanceExpenseSerializer):
    class Meta(FinanceExpenseSerializer.Meta):
        read_only_fields = FinanceExpenseSerializer.Meta.fields


class FinanceBudgetSerializer(serializers.ModelSerializer):
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
    project_name = serializers.CharField(source='project.name', read_only=True)
    competition_entry_name = serializers.CharField(
        source='competition_entry.entry_name',
        read_only=True,
        default='',
    )
    event = serializers.IntegerField(
        source='competition_entry.event_id',
        read_only=True,
        allow_null=True,
    )
    event_name = serializers.CharField(
        source='competition_entry.event.name',
        read_only=True,
        default='',
    )
    event_edition = serializers.CharField(
        source='competition_entry.event.edition',
        read_only=True,
        default='',
    )
    income_type_display = serializers.CharField(source='get_income_type_display', read_only=True)
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True, default='')
    receipts = FinanceReceiptSerializer(many=True, read_only=True)
    allocations = FinanceIncomeAllocationSerializer(many=True, read_only=True)
    scope = serializers.CharField(source='fund_scope', read_only=True)
    proof_file = serializers.FileField(write_only=True, required=False)
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = FinanceIncome
        fields = (
            'id', 'project', 'project_name',
            'competition_entry', 'competition_entry_name',
            'event', 'event_name', 'event_edition',
            'scope', 'title', 'amount',
            'income_type', 'income_type_display',
            'stage', 'stage_display', 'income_date',
            'confirmed_at', 'received_at',
            'source', 'reference_number', 'note',
            'receipts', 'allocations', 'proof_file',
            'recorded_by', 'recorded_by_name', 'can_manage',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'recorded_by', 'confirmed_at', 'received_at',
            'created_at', 'updated_at',
        )

    def get_can_manage(self, obj):
        request = self.context.get('request')
        return bool(request and can_manage_finance(request.user, obj.project))

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('收入金额必须大于 0')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get('project', getattr(self.instance, 'project', None))
        entry = attrs.get(
            'competition_entry',
            getattr(self.instance, 'competition_entry', None),
        )
        if entry and project and entry.project_id != project.id:
            raise serializers.ValidationError({
                'competition_entry': '参赛条目必须属于所选项目',
            })
        if entry and self.instance and self.instance.allocations.exists():
            raise serializers.ValidationError({
                'competition_entry': '已有分摊的收入不能直接关联参赛条目',
            })
        if self.instance and self.instance.allocations.exists():
            if (
                project
                and project.id != self.instance.project_id
            ):
                raise serializers.ValidationError({
                    'project': '已有分摊的收入需先清空分摊后才能更换锚点项目',
                })
            amount = attrs.get('amount', self.instance.amount)
            allocated_total = sum(
                (
                    allocation.amount
                    for allocation in self.instance.allocations.all()
                ),
                ZERO,
            )
            if amount != allocated_total:
                raise serializers.ValidationError({
                    'amount': '收入金额必须与现有分摊合计一致，请先更新分摊',
                })
        if self.instance and 'stage' in attrs and attrs['stage'] != self.instance.stage:
            raise serializers.ValidationError({
                'stage': '收入阶段请使用 set_stage 动作变更',
            })
        if not self.instance:
            income_type = attrs.get('income_type', FinanceIncome.IncomeType.OTHER)
            if income_type == FinanceIncome.IncomeType.BONUS and 'stage' not in attrs:
                attrs['stage'] = FinanceIncome.Stage.EXPECTED
            stage = attrs.get('stage', FinanceIncome.Stage.RECEIVED)
            if (
                income_type == FinanceIncome.IncomeType.BONUS
                and stage == FinanceIncome.Stage.RECEIVED
                and not attrs.get('proof_file')
            ):
                raise serializers.ValidationError({
                    'proof_file': '奖金到账必须上传到账凭证',
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        proof_file = validated_data.pop('proof_file', None)
        income = super().create(validated_data)
        now = income.created_at
        updates = {}
        if income.stage in {
            FinanceIncome.Stage.CONFIRMED,
            FinanceIncome.Stage.RECEIVED,
        }:
            updates['confirmed_at'] = now
        if income.stage == FinanceIncome.Stage.RECEIVED:
            updates['received_at'] = now
        if updates:
            FinanceIncome.objects.filter(pk=income.pk).update(**updates)
            income.refresh_from_db()
        if proof_file:
            FinanceReceipt.objects.create(
                income=income,
                attachment_type=FinanceReceipt.AttachmentType.INCOME_PROOF,
                file=proof_file,
                uploaded_by=self.context['request'].user,
            )
        return income


class FinanceInternalTransferSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    competition_entry_name = serializers.CharField(
        source='competition_entry.entry_name',
        read_only=True,
        default='',
    )
    event = serializers.IntegerField(
        source='competition_entry.event_id',
        read_only=True,
        allow_null=True,
    )
    event_name = serializers.CharField(
        source='competition_entry.event.name',
        read_only=True,
        default='',
    )
    event_edition = serializers.CharField(
        source='competition_entry.event.edition',
        read_only=True,
        default='',
    )
    from_user_name = serializers.CharField(source='from_user.name', read_only=True, default='')
    to_user_name = serializers.CharField(source='to_user.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    receipts = FinanceReceiptSerializer(many=True, read_only=True)
    proof_file = serializers.FileField(write_only=True, required=False)
    transfer_date = serializers.DateTimeField(write_only=True, required=False)
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = FinanceInternalTransfer
        fields = (
            'id', 'project', 'project_name',
            'competition_entry', 'competition_entry_name',
            'event', 'event_name', 'event_edition',
            'from_user', 'from_user_name', 'to_user', 'to_user_name',
            'source_label', 'amount', 'status', 'status_display',
            'payment_method', 'payment_reference', 'transferred_at',
            'failure_reason', 'note', 'receipts', 'proof_file',
            'transfer_date',
            'recorded_by', 'recorded_by_name', 'can_manage',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'recorded_by', 'transferred_at',
            'created_at', 'updated_at',
        )

    def get_can_manage(self, obj):
        request = self.context.get('request')
        return bool(request and can_pay_finance(request.user, obj.project))

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get('project', getattr(self.instance, 'project', None))
        entry = attrs.get(
            'competition_entry',
            getattr(self.instance, 'competition_entry', None),
        )
        if entry and project and entry.project_id != project.id:
            raise serializers.ValidationError({
                'competition_entry': '参赛条目必须属于所选项目',
            })
        from_user = attrs.get('from_user', getattr(self.instance, 'from_user', None))
        to_user = attrs.get('to_user', getattr(self.instance, 'to_user', None))
        source_label = str(
            attrs.get('source_label', getattr(self.instance, 'source_label', ''))
            or ''
        ).strip()
        if from_user and to_user and from_user.id == to_user.id:
            raise serializers.ValidationError({'to_user': '转出人与转入人不能相同'})
        if not from_user and not source_label:
            raise serializers.ValidationError({'source_label': '外部转入必须填写资金来源'})
        desired_status = attrs.get(
            'status',
            getattr(self.instance, 'status', FinanceInternalTransfer.Status.PENDING_PROOF),
        )
        if (
            self.instance
            and 'status' in attrs
            and attrs['status'] != self.instance.status
        ):
            raise serializers.ValidationError({
                'status': '转移状态请使用 complete/fail 动作变更',
            })
        if desired_status == FinanceInternalTransfer.Status.COMPLETED and not attrs.get('proof_file'):
            raise serializers.ValidationError({
                'proof_file': '内部转移完成必须上传转账凭证',
            })
        if (
            desired_status == FinanceInternalTransfer.Status.FAILED
            and not str(attrs.get('failure_reason', '') or '').strip()
        ):
            raise serializers.ValidationError({'failure_reason': '转移异常必须填写原因'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        proof_file = validated_data.pop('proof_file', None)
        transfer_date = validated_data.pop('transfer_date', None)
        desired_status = validated_data.pop(
            'status',
            FinanceInternalTransfer.Status.PENDING_PROOF,
        )
        request = self.context['request']
        transfer = FinanceInternalTransfer.objects.create(
            **validated_data,
            status=FinanceInternalTransfer.Status.PENDING_PROOF,
            recorded_by=request.user,
            transferred_at=transfer_date,
        )
        record_finance_event(
            project=transfer.project,
            event_type='internal_transfer_created',
            actor=request.user,
            internal_transfer=transfer,
            amount=transfer.amount,
            to_status=transfer.status,
            description='登记内部资金转移；不计入项目收入或支出',
        )
        if desired_status == FinanceInternalTransfer.Status.COMPLETED:
            transfer = complete_internal_transfer(
                transfer,
                proof_file=proof_file,
                actor=request.user,
            )
        elif desired_status == FinanceInternalTransfer.Status.FAILED:
            transfer.status = FinanceInternalTransfer.Status.FAILED
            transfer.failure_reason = validated_data.get('failure_reason', '')
            transfer.full_clean()
            transfer.save()
            record_finance_event(
                project=transfer.project,
                event_type='internal_transfer_failed',
                actor=request.user,
                internal_transfer=transfer,
                from_status=FinanceInternalTransfer.Status.PENDING_PROOF,
                to_status=transfer.status,
                amount=transfer.amount,
                description=transfer.failure_reason,
            )
        return transfer


class FinanceLedgerEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.name', read_only=True, default='')
    operator_name = serializers.CharField(
        source='actor.name',
        read_only=True,
        default='',
    )
    occurred_at = serializers.DateTimeField(source='created_at', read_only=True)
    title = serializers.SerializerMethodField()
    action_display = serializers.SerializerMethodField()

    EVENT_TITLES = {
        'expense_created': '支出已登记',
        'expense_updated': '支出已更新',
        'expense_archived': '支出已归档',
        'attachment_uploaded': '附件已上传',
        'attachment_deleted': '草稿附件已删除',
        'reimbursement_submitted': '报销已提交',
        'reimbursement_approved': '报销审核通过',
        'reimbursement_rejected': '报销已驳回',
        'payment_created': '付款已登记',
        'payment_updated': '付款已更新',
        'payment_deleted': '待付款记录已删除',
        'payment_completed': '付款凭证已归档',
        'payment_failed': '付款异常',
        'payment_reversed': '付款已冲销',
        'income_created': '收入已登记',
        'income_updated': '收入已更新',
        'income_deleted': '收入已删除',
        'income_stage_changed': '收入阶段已更新',
        'allocation_updated': '资金分摊已更新',
        'internal_transfer_created': '内部转移已登记',
        'internal_transfer_updated': '内部转移已更新',
        'internal_transfer_deleted': '内部转移已删除',
        'internal_transfer_completed': '内部转移凭证已归档',
        'internal_transfer_failed': '内部转移异常',
    }

    def get_title(self, obj):
        return self.EVENT_TITLES.get(
            obj.event_type,
            obj.event_type.replace('_', ' '),
        )

    def get_action_display(self, obj):
        return self.get_title(obj)

    class Meta:
        model = FinanceLedgerEvent
        fields = (
            'id', 'project', 'expense', 'income', 'payment',
            'internal_transfer', 'event_type',
            'title', 'action_display',
            'actor', 'actor_name', 'operator_name',
            'from_status', 'to_status',
            'amount', 'description', 'metadata',
            'created_at', 'occurred_at',
        )
        read_only_fields = fields


class ReimbursementReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    opinion = serializers.CharField(required=False, allow_blank=True, default='')


class ReimbursementPaymentSerializer(serializers.Serializer):
    recipient = serializers.PrimaryKeyRelatedField(
        queryset=FinancePayment._meta.get_field('recipient').remote_field.model.objects.all(),
        required=False,
        allow_null=True,
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
    )
    payment_method = serializers.CharField(max_length=50)
    payment_reference = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default='',
    )
    proof_file = serializers.FileField(required=True)


class PaymentProofSerializer(serializers.Serializer):
    proof_file = serializers.FileField(required=True)
    payment_reference = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )
    payment_date = serializers.DateTimeField(required=False)
    transfer_date = serializers.DateTimeField(required=False)


class PaymentFailureSerializer(serializers.Serializer):
    failure_reason = serializers.CharField()


class IncomeStageSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=FinanceIncome.Stage.choices)
    proof_file = serializers.FileField(required=False)
