"""
经费视图
关键：经费明细和票据对内部成员公开，外部协作者与已离队账号隔离
- FinanceBudgetViewSet: 经费总表 CRUD
- FinanceExpenseViewSet: 经费明细 CRUD（含票据上传）
- FinanceReceiptViewSet: 票据管理
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import (
    IsInternalTeamMember,
    IsProjectLeaderOrTeacherOrAdmin,
)
from common.project_access import scope_project_queryset, user_can_access_project
from .models import (
    FinanceBudget,
    FinanceExpense,
    FinanceIncome,
    FinanceInternalTransfer,
    FinancePayment,
    FinanceReceipt,
)
from .permissions import (
    can_manage_finance,
    can_pay_finance,
    can_review_expense,
)
from .serializers import (
    AllocationReplaceSerializer,
    FinanceBudgetSerializer,
    FinanceExpenseSerializer, FinanceExpenseListSerializer,
    FinanceIncomeSerializer,
    FinanceInternalTransferSerializer,
    FinancePaymentSerializer,
    FinanceReceiptSerializer,
    IncomeStageSerializer,
    PaymentFailureSerializer,
    PaymentProofSerializer,
    ReimbursementReviewSerializer, ReimbursementPaymentSerializer,
)
from .services import (
    complete_internal_transfer,
    complete_payment,
    fail_payment,
    notify_finance_change,
    recalculate_project_budget,
    record_finance_event,
    replace_allocations,
    set_income_stage,
    sync_expense_payment_status,
)


def _validation_message(exc):
    if hasattr(exc, 'message_dict'):
        return exc.message_dict
    messages = getattr(exc, 'messages', None)
    return messages[0] if messages else str(exc)


def _receipt_project(receipt_or_data):
    expense = getattr(receipt_or_data, 'expense', None)
    income = getattr(receipt_or_data, 'income', None)
    payment = getattr(receipt_or_data, 'payment', None)
    transfer = getattr(receipt_or_data, 'internal_transfer', None)
    if expense:
        return expense.project
    if income:
        return income.project
    if payment:
        return payment.expense.project
    if transfer:
        return transfer.project
    return None


class FinanceBudgetViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    经费总表 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 项目负责人/老师/管理员
    """
    queryset = FinanceBudget.objects.all().order_by('-updated_at')

    serializer_classes_by_action = {
        'list': FinanceBudgetSerializer,
        'retrieve': FinanceBudgetSerializer,
        'create': FinanceBudgetSerializer,
        'update': FinanceBudgetSerializer,
        'partial_update': FinanceBudgetSerializer,
    }

    permission_classes_by_action = {
        'list': [IsInternalTeamMember],
        'retrieve': [IsInternalTeamMember],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
    }

    filterset_fields = ['project', 'status', 'period']
    search_fields = ['project__name']
    ordering_fields = ['updated_at', 'used_amount']

    def get_queryset(self):
        return scope_project_queryset(
            super().get_queryset(),
            self.request.user,
            project_lookup='project',
        )

    def create(self, request, *args, **kwargs):
        """创建经费总表"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        budget = serializer.save()
        budget = recalculate_project_budget(budget.project_id) or budget
        return success_response(
            FinanceBudgetSerializer(budget).data,
            message='经费总表创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新经费总表"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        budget = serializer.save()
        budget = recalculate_project_budget(budget.project_id) or budget
        return success_response(FinanceBudgetSerializer(budget).data, message='经费总表更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除经费总表"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='经费总表删除成功')


class FinanceExpenseViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    经费明细 ViewSet
    关键：经费明细对所有认证用户开放读取
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 项目负责人/老师/管理员
    """
    queryset = (
        FinanceExpense.objects.all()
        .select_related(
            'project',
            'competition_entry',
            'competition_entry__event',
            'spender',
            'payee',
            'reviewer',
            'applied_by',
            'paid_by',
        )
        .prefetch_related(
            'receipts',
            'payments',
            'payments__receipts',
            'allocations',
            'allocations__competition_entry',
            'allocations__competition_entry__event',
            'allocations__competition_entry__project',
        )
        .order_by('-expense_date', '-created_at')
    )

    serializer_classes_by_action = {
        'list': FinanceExpenseListSerializer,
        'retrieve': FinanceExpenseSerializer,
        'create': FinanceExpenseSerializer,
        'update': FinanceExpenseSerializer,
        'partial_update': FinanceExpenseSerializer,
        'submit_reimbursement': FinanceExpenseSerializer,
        'review_reimbursement': ReimbursementReviewSerializer,
        'mark_paid': ReimbursementPaymentSerializer,
        'set_allocations': AllocationReplaceSerializer,
    }

    permission_classes_by_action = {
        'list': [IsInternalTeamMember],
        'retrieve': [IsInternalTeamMember],
        'create': [IsInternalTeamMember],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
        'submit_reimbursement': [IsInternalTeamMember],
        'review_reimbursement': [IsProjectLeaderOrTeacherOrAdmin],
        'mark_paid': [IsInternalTeamMember],
        'set_allocations': [IsInternalTeamMember],
    }

    filterset_fields = [
        'project', 'competition_entry', 'category', 'spender', 'payee',
        'expense_date', 'reimbursement_status',
    ]
    search_fields = [
        'title', 'purpose', 'project__name',
        'competition_entry__entry_name',
        'competition_entry__event__name',
    ]
    ordering_fields = [
        'created_at', 'updated_at', 'title', 'amount', 'expense_date',
    ]

    def get_queryset(self):
        return scope_project_queryset(
            super().get_queryset(),
            self.request.user,
            project_lookup='project',
        )

    def create(self, request, *args, **kwargs):
        """创建经费明细"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data['project']
        is_finance_manager = can_manage_finance(request.user, project)
        if not is_finance_manager:
            from apps.projects.models import ProjectMember
            is_project_member = ProjectMember.objects.filter(
                project=project,
                user=request.user,
                status=ProjectMember.Status.ACTIVE,
            ).exists()
            if not is_project_member:
                return error_response(
                    message='只能登记自己参与项目的支出',
                    code=1003,
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            # 普通成员只能以本人作为经办人，避免替他人发起报销。
            serializer.validated_data['spender'] = request.user
            serializer.validated_data['payee'] = request.user
        elif not serializer.validated_data.get('spender'):
            serializer.validated_data['spender'] = request.user
        if not serializer.validated_data.get('payee'):
            serializer.validated_data['payee'] = serializer.validated_data.get(
                'spender',
                request.user,
            )
        expense = serializer.save()
        record_finance_event(
            project=expense.project,
            event_type='expense_created',
            actor=request.user,
            expense=expense,
            amount=expense.amount,
            to_status=expense.reimbursement_status,
            description='登记成员垫付/项目支出',
        )
        notify_finance_change(
            expense.project,
            title=f'新增支出：{expense.title}',
            content=(
                f'项目「{expense.project.name}」新增支出 {expense.amount} 元，'
                f'当前报销状态为{expense.get_reimbursement_status_display()}。'
            ),
            sender=request.user,
            ref_type='finance_expense',
            ref_id=expense.id,
        )
        return success_response(
            FinanceExpenseSerializer(
                expense,
                context={'request': request},
            ).data,
            message='经费明细创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新经费明细"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        locked_fields = {'project', 'competition_entry', 'amount', 'spender', 'payee'}
        if (
            instance.reimbursement_status
            not in {
                FinanceExpense.ReimbursementStatus.DRAFT,
                FinanceExpense.ReimbursementStatus.REJECTED,
            }
            and locked_fields.intersection(request.data.keys())
        ):
            return error_response(
                message='报销进入审核或付款流程后不能修改归属、金额或收付款人',
                code=2505,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        changed_fields = sorted(serializer.validated_data)
        expense = serializer.save()
        record_finance_event(
            project=expense.project,
            event_type='expense_updated',
            actor=request.user,
            expense=expense,
            amount=expense.amount,
            to_status=expense.reimbursement_status,
            description='更新支出登记信息',
            metadata={'changed_fields': changed_fields},
        )
        notify_finance_change(
            expense.project,
            title=f'支出已更新：{expense.title}',
            content=f'项目「{expense.project.name}」的支出记录已更新。',
            sender=request.user,
            ref_type='finance_expense',
            ref_id=expense.id,
        )
        return success_response(
            FinanceExpenseSerializer(
                expense,
                context={'request': request},
            ).data,
            message='经费明细更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除经费明细（软删除，移入回收站）"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        record_finance_event(
            project=instance.project,
            event_type='expense_archived',
            actor=request.user,
            expense=instance,
            amount=instance.amount,
            from_status=instance.reimbursement_status,
            description='支出移入回收站',
        )
        self.perform_destroy(instance)
        notify_finance_change(
            instance.project,
            title=f'支出已移入回收站：{instance.title}',
            content=f'项目「{instance.project.name}」的一笔支出已移入回收站，预算汇总已自动更新。',
            sender=request.user,
            ref_type='finance_expense',
            ref_id=instance.id,
        )
        return success_response(message='经费明细已移入回收站')

    def perform_destroy(self, instance):
        """软删除而非物理删除，可通过回收站恢复"""
        instance.soft_delete(getattr(self.request, 'user', None))

    @action(detail=True, methods=['post'])
    def submit_reimbursement(self, request, pk=None):
        """由经办人或财务管理者提交/重新提交报销。"""
        expense = self.get_object()
        can_submit = (
            can_manage_finance(request.user, expense.project)
            or expense.spender_id == request.user.id
        )
        if not can_submit:
            return error_response(
                message='仅经办人、项目负责人、老师或管理员可提交该报销',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        has_source_document = expense.receipts.filter(
            attachment_type__in=[
                FinanceReceipt.AttachmentType.INVOICE,
                FinanceReceipt.AttachmentType.ORIGINAL_RECEIPT,
            ],
        ).exists()
        if not has_source_document:
            return error_response(
                message='提交报销前必须上传发票或原始票据',
                code=2506,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if not expense.payee_id:
            expense.payee_id = expense.spender_id or request.user.id
            expense.save(update_fields=['payee'])
        from_status = expense.reimbursement_status
        try:
            expense.submit_reimbursement(request.user)
        except ValueError as exc:
            return error_response(message=str(exc))
        notify_finance_change(
            expense.project,
            title=f'报销待审核：{expense.title}',
            content=f'{request.user.name} 提交了 {expense.amount} 元报销，请及时审核。',
            sender=request.user,
            ref_type='finance_expense',
            ref_id=expense.id,
        )
        record_finance_event(
            project=expense.project,
            event_type='reimbursement_submitted',
            actor=request.user,
            expense=expense,
            from_status=from_status,
            to_status=expense.reimbursement_status,
            amount=expense.amount,
            description='票据已提交，额度进入待审核预留',
        )
        return success_response(
            FinanceExpenseSerializer(
                expense,
                context={'request': request},
            ).data,
            message='报销申请已提交',
        )

    @action(detail=True, methods=['post'])
    def review_reimbursement(self, request, pk=None):
        """项目负责人、老师或管理员审核报销。"""
        expense = self.get_object()
        self.check_object_permissions(request, expense)
        if not can_review_expense(request.user, expense):
            return error_response(
                message='申请人、经办人或收款人不能审核自己的报销',
                code=2507,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from_status = expense.reimbursement_status
        try:
            expense.review_reimbursement(
                request.user,
                serializer.validated_data['approved'],
                serializer.validated_data.get('opinion', ''),
            )
        except ValueError as exc:
            return error_response(message=str(exc))
        notify_finance_change(
            expense.project,
            title=f'报销{expense.get_reimbursement_status_display()}：{expense.title}',
            content=(
                f'{expense.amount} 元报销已由 {request.user.name} 审核，'
                f'结果：{expense.get_reimbursement_status_display()}。'
            ),
            sender=request.user,
            ref_type='finance_expense',
            ref_id=expense.id,
        )
        record_finance_event(
            project=expense.project,
            event_type=(
                'reimbursement_approved'
                if serializer.validated_data['approved']
                else 'reimbursement_rejected'
            ),
            actor=request.user,
            expense=expense,
            from_status=from_status,
            to_status=expense.reimbursement_status,
            amount=expense.amount,
            description=serializer.validated_data.get('opinion', ''),
        )
        return success_response(
            FinanceExpenseSerializer(
                expense,
                context={'request': request},
            ).data,
            message='报销审核完成',
        )

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """老师、系统管理员或明确的项目财务经办人登记付款。"""
        expense = self.get_object()
        can_mark_paid = can_pay_finance(request.user, expense.project)
        if not can_mark_paid:
            return error_response(
                message='仅老师、系统管理员或明确授权的财务经办人可登记付款',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient = (
            serializer.validated_data.get('recipient')
            or expense.payee
            or expense.spender
        )
        amount = serializer.validated_data.get(
            'amount',
            expense.remaining_payable,
        )
        try:
            with transaction.atomic():
                payment = FinancePayment.objects.create(
                    expense=expense,
                    recipient=recipient,
                    amount=amount,
                    status=FinancePayment.Status.PENDING_PROOF,
                    payment_method=serializer.validated_data['payment_method'],
                    payment_reference=serializer.validated_data.get(
                        'payment_reference',
                        '',
                    ),
                    paid_by=request.user,
                )
                payment, expense = complete_payment(
                    payment,
                    proof_file=serializer.validated_data['proof_file'],
                    actor=request.user,
                )
        except (ValueError, DjangoValidationError) as exc:
            return error_response(message=_validation_message(exc))
        notify_finance_change(
            expense.project,
            title=f'报销已付款：{expense.title}',
            content=(
                f'{payment.amount} 元报销付款已登记，付款方式：'
                f'{payment.payment_method}。'
            ),
            sender=request.user,
            ref_type='finance_expense',
            ref_id=expense.id,
        )
        return success_response(
            FinanceExpenseSerializer(
                expense,
                context={'request': request},
            ).data,
            message='付款登记完成',
        )

    @action(detail=True, methods=['post'])
    def set_allocations(self, request, pk=None):
        """原子替换一笔项目公共支出的比赛/参赛队分摊。"""
        expense = self.get_object()
        if not can_manage_finance(request.user, expense.project):
            return error_response(
                message='无权维护该支出的比赛分摊',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            replace_allocations(
                expense,
                serializer.validated_data['allocations'],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            return error_response(message=_validation_message(exc))
        expense.refresh_from_db()
        return success_response(
            FinanceExpenseSerializer(
                expense,
                context={'request': request},
            ).data,
            message='支出分摊已更新',
        )


class FinanceIncomeViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """收入流水 CRUD；读取向登录成员开放，写操作限财务管理角色。"""

    queryset = (
        FinanceIncome.objects.all()
        .select_related(
            'project',
            'competition_entry',
            'competition_entry__event',
            'recorded_by',
        )
        .prefetch_related(
            'receipts',
            'allocations',
            'allocations__competition_entry',
            'allocations__competition_entry__event',
            'allocations__competition_entry__project',
        )
    )
    serializer_class = FinanceIncomeSerializer
    serializer_classes_by_action = {
        'list': FinanceIncomeSerializer,
        'retrieve': FinanceIncomeSerializer,
        'create': FinanceIncomeSerializer,
        'update': FinanceIncomeSerializer,
        'partial_update': FinanceIncomeSerializer,
        'set_allocations': AllocationReplaceSerializer,
        'set_stage': IncomeStageSerializer,
    }
    permission_classes_by_action = {
        'list': [IsInternalTeamMember],
        'retrieve': [IsInternalTeamMember],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
        'set_allocations': [IsInternalTeamMember],
        'set_stage': [IsInternalTeamMember],
    }
    filterset_fields = [
        'project', 'competition_entry', 'income_type', 'stage', 'income_date',
    ]
    search_fields = [
        'title', 'source', 'reference_number', 'project__name',
        'competition_entry__entry_name',
        'competition_entry__event__name',
    ]
    ordering_fields = ['income_date', 'amount', 'created_at', 'updated_at']

    def get_queryset(self):
        return scope_project_queryset(
            super().get_queryset(),
            self.request.user,
            project_lookup='project',
        )

    def perform_create(self, serializer):
        income = serializer.save(recorded_by=self.request.user)
        record_finance_event(
            project=income.project,
            event_type='income_created',
            actor=self.request.user,
            income=income,
            amount=income.amount,
            to_status=income.stage,
            description='登记项目收入/奖金阶段',
        )
        for receipt in income.receipts.all():
            record_finance_event(
                project=income.project,
                event_type='attachment_uploaded',
                actor=self.request.user,
                income=income,
                description=f'上传{receipt.get_attachment_type_display()}',
                metadata={'receipt_id': receipt.id},
            )
        notify_finance_change(
            income.project,
            title=f'新增收入：{income.title}',
            content=f'项目「{income.project.name}」新增收入 {income.amount} 元，预算汇总已更新。',
            sender=self.request.user,
            ref_type='finance_income',
            ref_id=income.id,
        )

    def perform_update(self, serializer):
        changed_fields = sorted(serializer.validated_data)
        income = serializer.save()
        record_finance_event(
            project=income.project,
            event_type='income_updated',
            actor=self.request.user,
            income=income,
            amount=income.amount,
            to_status=income.stage,
            description='更新收入登记信息',
            metadata={'changed_fields': changed_fields},
        )
        notify_finance_change(
            income.project,
            title=f'收入已更新：{income.title}',
            content=f'项目「{income.project.name}」的收入流水已更新，预算汇总已同步。',
            sender=self.request.user,
            ref_type='finance_income',
            ref_id=income.id,
        )

    @action(detail=True, methods=['post'])
    def set_stage(self, request, pk=None):
        income = self.get_object()
        if not can_manage_finance(request.user, income.project):
            return error_response(
                message='无权变更该收入阶段',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            income = set_income_stage(
                income,
                stage=serializer.validated_data['stage'],
                actor=request.user,
                proof_file=serializer.validated_data.get('proof_file'),
            )
        except DjangoValidationError as exc:
            return error_response(message=_validation_message(exc))
        return success_response(
            FinanceIncomeSerializer(
                income,
                context={'request': request},
            ).data,
            message='收入阶段已更新',
        )

    @action(detail=True, methods=['post'])
    def set_allocations(self, request, pk=None):
        income = self.get_object()
        if not can_manage_finance(request.user, income.project):
            return error_response(
                message='无权维护该收入的比赛分摊',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            replace_allocations(
                income,
                serializer.validated_data['allocations'],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            return error_response(message=_validation_message(exc))
        income.refresh_from_db()
        return success_response(
            FinanceIncomeSerializer(
                income,
                context={'request': request},
            ).data,
            message='收入分摊已更新',
        )

    def perform_destroy(self, instance):
        project = instance.project
        title = instance.title
        income_id = instance.id
        is_last_income = not FinanceIncome.objects.filter(
            project=project,
        ).exclude(pk=income_id).exists()
        record_finance_event(
            project=project,
            event_type='income_deleted',
            actor=self.request.user,
            income=instance,
            amount=instance.amount,
            from_status=instance.stage,
            description=f'删除收入：{title}',
        )
        instance.delete()
        if is_last_income:
            # Once a project has adopted the income ledger, deleting its final
            # row must not leave the previous cached income in FinanceBudget.
            FinanceBudget.objects.filter(project=project).update(
                bonus_amount=0,
                other_income=0,
            )
            recalculate_project_budget(project.id)
        notify_finance_change(
            project,
            title=f'收入已删除：{title}',
            content=f'项目「{project.name}」的收入流水已删除，预算汇总已同步。',
            sender=self.request.user,
            ref_type='finance_income',
            ref_id=income_id,
        )


class FinanceReceiptViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    票据管理 ViewSet
    关键：票据对所有认证用户开放读取
    - list/retrieve: 所有认证用户可查看
    - create/destroy: 项目负责人/老师/管理员
    """
    queryset = (
        FinanceReceipt.objects.all()
        .select_related(
            'expense__project',
            'income__project',
            'payment__expense__project',
            'internal_transfer__project',
            'uploaded_by',
        )
        .order_by('-created_at')
    )
    # Evidence ownership and files are immutable; corrections use delete/re-upload
    # while the parent record is still a draft.
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    serializer_classes_by_action = {
        'list': FinanceReceiptSerializer,
        'retrieve': FinanceReceiptSerializer,
        'create': FinanceReceiptSerializer,
    }

    permission_classes_by_action = {
        'list': [IsInternalTeamMember],
        'retrieve': [IsInternalTeamMember],
        'create': [IsInternalTeamMember],
        'destroy': [IsInternalTeamMember],
    }

    filterset_fields = [
        'expense', 'income', 'payment', 'internal_transfer',
        'attachment_type', 'uploaded_by',
    ]
    search_fields = [
        'expense__title', 'income__title',
        'payment__expense__title', 'internal_transfer__note',
    ]

    def get_queryset(self):
        from apps.projects.models import Project

        visible_project_ids = scope_project_queryset(
            Project.objects.all(),
            self.request.user,
            project_lookup='',
        ).values_list('id', flat=True)
        return super().get_queryset().filter(
            Q(expense__project_id__in=visible_project_ids)
            | Q(income__project_id__in=visible_project_ids)
            | Q(payment__expense__project_id__in=visible_project_ids)
            | Q(internal_transfer__project_id__in=visible_project_ids)
        ).distinct()

    def create(self, request, *args, **kwargs):
        """上传票据"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = _receipt_project(
            type('ReceiptOwner', (), serializer.validated_data)()
        )
        if project is None or not user_can_access_project(request.user, project):
            return error_response(
                message='无权访问该票据所属项目',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        expense = serializer.validated_data.get('expense')
        is_finance_manager = can_manage_finance(request.user, project)
        can_upload_own_expense = bool(
            expense
            and request.user.id in {expense.spender_id, expense.payee_id}
        )
        if not is_finance_manager and not can_upload_own_expense:
            return error_response(
                message='只能为本人经办的支出上传票据',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if (
            not is_finance_manager
            and expense
            and expense.reimbursement_status
            not in [
                FinanceExpense.ReimbursementStatus.DRAFT,
                FinanceExpense.ReimbursementStatus.REJECTED,
            ]
        ):
            return error_response(
                message='报销已进入审核或付款流程，不能继续上传票据',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        # 自动设置上传人
        receipt = serializer.save(uploaded_by=request.user)
        record_finance_event(
            project=project,
            event_type='attachment_uploaded',
            actor=request.user,
            expense=receipt.expense,
            income=receipt.income,
            payment=receipt.payment,
            internal_transfer=receipt.internal_transfer,
            description=f'上传{receipt.get_attachment_type_display()}',
            metadata={'receipt_id': receipt.id},
        )
        return success_response(
            FinanceReceiptSerializer(receipt).data,
            message='票据上传成功',
            http_status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """删除票据"""
        instance = self.get_object()
        expense = instance.expense
        project = _receipt_project(instance)
        if (
            instance.payment_id
            and instance.payment.status == FinancePayment.Status.COMPLETED
        ):
            return error_response(
                message='已完成付款的转账凭证属于审计依据，不能删除',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            instance.internal_transfer_id
            and instance.internal_transfer.status
            == FinanceInternalTransfer.Status.COMPLETED
        ):
            return error_response(
                message='已完成内部转移的凭证属于审计依据，不能删除',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            instance.income_id
            and instance.income.stage == FinanceIncome.Stage.RECEIVED
            and instance.attachment_type
            == FinanceReceipt.AttachmentType.INCOME_PROOF
        ):
            return error_response(
                message='已到账收入的到账凭证属于审计依据，不能删除',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            expense is not None
            and expense.reimbursement_status
            not in {
                FinanceExpense.ReimbursementStatus.DRAFT,
                FinanceExpense.ReimbursementStatus.REJECTED,
            }
            and instance.attachment_type
            in {
                FinanceReceipt.AttachmentType.INVOICE,
                FinanceReceipt.AttachmentType.ORIGINAL_RECEIPT,
            }
        ):
            return error_response(
                message='报销提交后的原始票据属于审计依据，不能删除',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        is_finance_manager = can_manage_finance(request.user, project)
        can_delete_own_draft = (
            expense is not None
            and instance.uploaded_by_id == request.user.id
            and request.user.id in {expense.spender_id, expense.payee_id}
            and expense.reimbursement_status
            in [
                FinanceExpense.ReimbursementStatus.DRAFT,
                FinanceExpense.ReimbursementStatus.REJECTED,
            ]
        )
        if not (is_finance_manager or can_delete_own_draft):
            return error_response(
                message='只能删除本人草稿票据或由财务管理角色处理',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        # 删除物理文件
        if instance.file:
            instance.file.delete(save=False)
        record_finance_event(
            project=project,
            event_type='attachment_deleted',
            actor=request.user,
            expense=instance.expense,
            income=instance.income,
            payment=instance.payment,
            internal_transfer=instance.internal_transfer,
            description=f'删除{instance.get_attachment_type_display()}',
            metadata={'receipt_id': instance.id},
        )
        instance.delete()
        return success_response(message='票据删除成功')


class FinancePaymentViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """Independent, optionally partial reimbursement payments."""

    queryset = (
        FinancePayment.objects.all()
        .select_related(
            'expense',
            'expense__project',
            'expense__payee',
            'recipient',
            'paid_by',
        )
        .prefetch_related('receipts')
    )
    serializer_class = FinancePaymentSerializer
    serializer_classes_by_action = {
        'list': FinancePaymentSerializer,
        'retrieve': FinancePaymentSerializer,
        'create': FinancePaymentSerializer,
        'update': FinancePaymentSerializer,
        'partial_update': FinancePaymentSerializer,
        'complete': PaymentProofSerializer,
        'fail': PaymentFailureSerializer,
    }
    permission_classes_by_action = {
        'list': [IsInternalTeamMember],
        'retrieve': [IsInternalTeamMember],
        'create': [IsInternalTeamMember],
        'update': [IsInternalTeamMember],
        'partial_update': [IsInternalTeamMember],
        'destroy': [IsInternalTeamMember],
        'complete': [IsInternalTeamMember],
        'fail': [IsInternalTeamMember],
        'reverse': [IsInternalTeamMember],
    }
    filterset_fields = [
        'expense', 'expense__project', 'recipient', 'status', 'paid_by',
    ]
    ordering_fields = ['amount', 'paid_at', 'created_at', 'updated_at']

    def get_queryset(self):
        return scope_project_queryset(
            super().get_queryset(),
            self.request.user,
            project_lookup='expense__project',
        )

    def create(self, request, *args, **kwargs):
        try:
            expense = scope_project_queryset(
                FinanceExpense.objects.all(),
                request.user,
                project_lookup='project',
            ).filter(
                pk=request.data.get('expense'),
            ).select_related('project').first()
        except (TypeError, ValueError, DjangoValidationError):
            expense = None
        if expense is None:
            return error_response(message='报销申请不存在或无权访问')
        if not can_pay_finance(request.user, expense.project):
            return error_response(
                message='仅经费经办人或操作老师可登记付款',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = serializer.save()
        except DjangoValidationError as exc:
            return error_response(message=_validation_message(exc))
        return success_response(
            FinancePaymentSerializer(
                payment,
                context={'request': request},
            ).data,
            message='付款记录已创建',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        payment = self.get_object()
        if not can_pay_finance(request.user, payment.expense.project):
            return error_response(
                message='无权修改该付款记录',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(
            payment,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        changed_fields = sorted(serializer.validated_data)
        payment = serializer.save()
        record_finance_event(
            project=payment.expense.project,
            event_type='payment_updated',
            actor=request.user,
            expense=payment.expense,
            payment=payment,
            amount=payment.amount,
            to_status=payment.status,
            description='更新待付款登记信息',
            metadata={'changed_fields': changed_fields},
        )
        return success_response(
            FinancePaymentSerializer(
                payment,
                context={'request': request},
            ).data,
            message='付款记录已更新',
        )

    def destroy(self, request, *args, **kwargs):
        payment = self.get_object()
        if not can_pay_finance(request.user, payment.expense.project):
            return error_response(
                message='无权删除该付款记录',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if payment.status == FinancePayment.Status.COMPLETED:
            return error_response(
                message='已完成付款不可删除，请使用冲正',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        expense_id = payment.expense_id
        record_finance_event(
            project=payment.expense.project,
            event_type='payment_deleted',
            actor=request.user,
            expense=payment.expense,
            payment=payment,
            amount=payment.amount,
            from_status=payment.status,
            description='删除未完成付款记录',
        )
        payment.delete()
        sync_expense_payment_status(expense_id)
        return success_response(message='付款记录已删除')

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        payment = self.get_object()
        if not can_pay_finance(request.user, payment.expense.project):
            return error_response(
                message='无权完成该付款',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reference = serializer.validated_data.get('payment_reference')
        payment_date = serializer.validated_data.get('payment_date')
        try:
            with transaction.atomic():
                if reference is not None:
                    payment.payment_reference = reference
                if payment_date is not None:
                    payment.paid_at = payment_date
                if reference is not None or payment_date is not None:
                    payment.save(update_fields=[
                        'payment_reference',
                        'paid_at',
                        'updated_at',
                    ])
                payment, _ = complete_payment(
                    payment,
                    proof_file=serializer.validated_data['proof_file'],
                    actor=request.user,
                )
        except DjangoValidationError as exc:
            return error_response(message=_validation_message(exc))
        return success_response(
            FinancePaymentSerializer(
                payment,
                context={'request': request},
            ).data,
            message='付款凭证已归档并计入实际支出',
        )

    @action(detail=True, methods=['post'])
    def fail(self, request, pk=None):
        payment = self.get_object()
        if not can_pay_finance(request.user, payment.expense.project):
            return error_response(
                message='无权登记付款异常',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment, _ = fail_payment(
                payment,
                reason=serializer.validated_data['failure_reason'],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            return error_response(message=_validation_message(exc))
        return success_response(
            FinancePaymentSerializer(
                payment,
                context={'request': request},
            ).data,
            message='付款异常已登记',
        )

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        payment = self.get_object()
        if not can_pay_finance(request.user, payment.expense.project):
            return error_response(
                message='无权冲正该付款',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if payment.status != FinancePayment.Status.COMPLETED:
            return error_response(message='仅已完成付款可以冲正')
        reason = str(request.data.get('reason', '') or '').strip()
        if not reason:
            return error_response(message='冲正必须填写原因')
        from_status = payment.status
        payment.status = FinancePayment.Status.REVERSED
        payment.failure_reason = reason
        payment.save(update_fields=['status', 'failure_reason', 'updated_at'])
        sync_expense_payment_status(payment.expense_id)
        record_finance_event(
            project=payment.expense.project,
            event_type='payment_reversed',
            actor=request.user,
            expense=payment.expense,
            payment=payment,
            from_status=from_status,
            to_status=payment.status,
            amount=payment.amount,
            description=reason,
        )
        return success_response(
            FinancePaymentSerializer(
                payment,
                context={'request': request},
            ).data,
            message='付款已冲正',
        )


class FinanceInternalTransferViewSet(
    MultiSerializerMixin,
    MultiPermissionMixin,
    ModelViewSet,
):
    """Internal movements are traceable but never double-counted as cash flow."""

    queryset = (
        FinanceInternalTransfer.objects.all()
        .select_related(
            'project',
            'competition_entry',
            'competition_entry__event',
            'from_user',
            'to_user',
            'recorded_by',
        )
        .prefetch_related('receipts')
    )
    serializer_class = FinanceInternalTransferSerializer
    serializer_classes_by_action = {
        'list': FinanceInternalTransferSerializer,
        'retrieve': FinanceInternalTransferSerializer,
        'create': FinanceInternalTransferSerializer,
        'update': FinanceInternalTransferSerializer,
        'partial_update': FinanceInternalTransferSerializer,
        'complete': PaymentProofSerializer,
        'fail': PaymentFailureSerializer,
    }
    permission_classes_by_action = {
        action_name: [IsInternalTeamMember]
        for action_name in (
            'list', 'retrieve', 'create', 'update', 'partial_update',
            'destroy', 'complete', 'fail',
        )
    }
    filterset_fields = [
        'project', 'competition_entry', 'from_user', 'to_user',
        'status', 'recorded_by',
    ]
    ordering_fields = ['amount', 'transferred_at', 'created_at', 'updated_at']

    def get_queryset(self):
        return scope_project_queryset(
            super().get_queryset(),
            self.request.user,
            project_lookup='project',
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data['project']
        if not can_pay_finance(request.user, project):
            return error_response(
                message='仅经费经办人或操作老师可登记内部转移',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        try:
            transfer = serializer.save()
        except DjangoValidationError as exc:
            return error_response(message=_validation_message(exc))
        return success_response(
            FinanceInternalTransferSerializer(
                transfer,
                context={'request': request},
            ).data,
            message='内部资金转移已登记',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        transfer = self.get_object()
        if not can_pay_finance(request.user, transfer.project):
            return error_response(
                message='无权修改该内部转移',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(
            transfer,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        target_project = serializer.validated_data.get(
            'project',
            transfer.project,
        )
        if not can_pay_finance(request.user, target_project):
            return error_response(
                message='无权将内部转移改到目标项目',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        changed_fields = sorted(serializer.validated_data)
        transfer = serializer.save()
        record_finance_event(
            project=transfer.project,
            event_type='internal_transfer_updated',
            actor=request.user,
            internal_transfer=transfer,
            amount=transfer.amount,
            to_status=transfer.status,
            description='更新内部资金转移信息',
            metadata={'changed_fields': changed_fields},
        )
        return success_response(
            FinanceInternalTransferSerializer(
                transfer,
                context={'request': request},
            ).data,
            message='内部转移已更新',
        )

    def destroy(self, request, *args, **kwargs):
        transfer = self.get_object()
        if not can_pay_finance(request.user, transfer.project):
            return error_response(
                message='无权删除该内部转移',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if transfer.status == FinanceInternalTransfer.Status.COMPLETED:
            return error_response(message='已完成内部转移不可删除')
        record_finance_event(
            project=transfer.project,
            event_type='internal_transfer_deleted',
            actor=request.user,
            internal_transfer=transfer,
            amount=transfer.amount,
            from_status=transfer.status,
            description='删除未完成内部资金转移',
        )
        transfer.delete()
        return success_response(message='内部转移已删除')

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        transfer = self.get_object()
        if not can_pay_finance(request.user, transfer.project):
            return error_response(
                message='无权完成该内部转移',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reference = serializer.validated_data.get('payment_reference')
        transfer_date = serializer.validated_data.get('transfer_date')
        try:
            with transaction.atomic():
                if reference is not None:
                    transfer.payment_reference = reference
                if transfer_date is not None:
                    transfer.transferred_at = transfer_date
                if reference is not None or transfer_date is not None:
                    transfer.save(update_fields=[
                        'payment_reference',
                        'transferred_at',
                        'updated_at',
                    ])
                transfer = complete_internal_transfer(
                    transfer,
                    proof_file=serializer.validated_data['proof_file'],
                    actor=request.user,
                )
        except DjangoValidationError as exc:
            return error_response(message=_validation_message(exc))
        return success_response(
            FinanceInternalTransferSerializer(
                transfer,
                context={'request': request},
            ).data,
            message='内部转移凭证已归档',
        )

    @action(detail=True, methods=['post'])
    def fail(self, request, pk=None):
        transfer = self.get_object()
        if not can_pay_finance(request.user, transfer.project):
            return error_response(
                message='无权登记内部转移异常',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if transfer.status == FinanceInternalTransfer.Status.COMPLETED:
            return error_response(message='已完成内部转移不能标记异常')
        from_status = transfer.status
        transfer.status = FinanceInternalTransfer.Status.FAILED
        transfer.failure_reason = serializer.validated_data['failure_reason']
        transfer.recorded_by = request.user
        transfer.save()
        record_finance_event(
            project=transfer.project,
            event_type='internal_transfer_failed',
            actor=request.user,
            internal_transfer=transfer,
            from_status=from_status,
            to_status=transfer.status,
            amount=transfer.amount,
            description=transfer.failure_reason,
        )
        return success_response(
            FinanceInternalTransferSerializer(
                transfer,
                context={'request': request},
            ).data,
            message='内部转移异常已登记',
        )
