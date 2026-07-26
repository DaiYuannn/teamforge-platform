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

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import (
    IsInternalTeamMember,
    IsProjectLeaderOrTeacherOrAdmin,
    IsTeacherOrAdmin,
)
from .models import FinanceBudget, FinanceExpense, FinanceIncome, FinanceReceipt
from .serializers import (
    FinanceBudgetSerializer,
    FinanceExpenseSerializer, FinanceExpenseListSerializer,
    FinanceIncomeSerializer,
    FinanceReceiptSerializer,
    ReimbursementReviewSerializer, ReimbursementPaymentSerializer,
)
from .services import notify_finance_change


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

    def create(self, request, *args, **kwargs):
        """创建经费总表"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        budget = serializer.save()
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
        .select_related('project', 'spender', 'reviewer', 'applied_by', 'paid_by')
        .prefetch_related('receipts')
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
        'mark_paid': [IsTeacherOrAdmin],
    }

    filterset_fields = [
        'project', 'category', 'spender', 'expense_date', 'reimbursement_status',
    ]
    search_fields = ['title', 'purpose', 'project__name']
    ordering_fields = [
        'created_at', 'updated_at', 'title', 'amount', 'expense_date',
    ]

    def create(self, request, *args, **kwargs):
        """创建经费明细"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data['project']
        is_finance_manager = (
            request.user.global_role in ['teacher', 'sys_admin']
            or project.leader_id == request.user.id
        )
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
        elif not serializer.validated_data.get('spender'):
            serializer.validated_data['spender'] = request.user
        expense = serializer.save()
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
            FinanceExpenseSerializer(expense).data,
            message='经费明细创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新经费明细"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        notify_finance_change(
            expense.project,
            title=f'支出已更新：{expense.title}',
            content=f'项目「{expense.project.name}」的支出记录已更新。',
            sender=request.user,
            ref_type='finance_expense',
            ref_id=expense.id,
        )
        return success_response(FinanceExpenseSerializer(expense).data, message='经费明细更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除经费明细（软删除，移入回收站）"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
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
            request.user.global_role in ['teacher', 'sys_admin']
            or expense.project.leader_id == request.user.id
            or expense.spender_id == request.user.id
        )
        if not can_submit:
            return error_response(
                message='仅经办人、项目负责人、老师或管理员可提交该报销',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
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
        return success_response(
            FinanceExpenseSerializer(expense).data,
            message='报销申请已提交',
        )

    @action(detail=True, methods=['post'])
    def review_reimbursement(self, request, pk=None):
        """项目负责人、老师或管理员审核报销。"""
        expense = self.get_object()
        self.check_object_permissions(request, expense)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
        return success_response(
            FinanceExpenseSerializer(expense).data,
            message='报销审核完成',
        )

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """老师或管理员登记付款。"""
        expense = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            expense.mark_paid(
                request.user,
                serializer.validated_data['payment_method'],
                serializer.validated_data.get('payment_reference', ''),
            )
        except ValueError as exc:
            return error_response(message=str(exc))
        notify_finance_change(
            expense.project,
            title=f'报销已付款：{expense.title}',
            content=(
                f'{expense.amount} 元报销已付款，付款方式：'
                f'{expense.payment_method}。'
            ),
            sender=request.user,
            ref_type='finance_expense',
            ref_id=expense.id,
        )
        return success_response(
            FinanceExpenseSerializer(expense).data,
            message='付款登记完成',
        )


class FinanceIncomeViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """收入流水 CRUD；读取向登录成员开放，写操作限财务管理角色。"""

    queryset = FinanceIncome.objects.all().select_related('project', 'recorded_by')
    serializer_class = FinanceIncomeSerializer
    serializer_classes_by_action = {
        'list': FinanceIncomeSerializer,
        'retrieve': FinanceIncomeSerializer,
        'create': FinanceIncomeSerializer,
        'update': FinanceIncomeSerializer,
        'partial_update': FinanceIncomeSerializer,
    }
    permission_classes_by_action = {
        'list': [IsInternalTeamMember],
        'retrieve': [IsInternalTeamMember],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
    }
    filterset_fields = ['project', 'income_type', 'income_date']
    search_fields = ['title', 'source', 'reference_number', 'project__name']
    ordering_fields = ['income_date', 'amount', 'created_at', 'updated_at']

    def perform_create(self, serializer):
        income = serializer.save(recorded_by=self.request.user)
        notify_finance_change(
            income.project,
            title=f'新增收入：{income.title}',
            content=f'项目「{income.project.name}」新增收入 {income.amount} 元，预算汇总已更新。',
            sender=self.request.user,
            ref_type='finance_income',
            ref_id=income.id,
        )

    def perform_update(self, serializer):
        income = serializer.save()
        notify_finance_change(
            income.project,
            title=f'收入已更新：{income.title}',
            content=f'项目「{income.project.name}」的收入流水已更新，预算汇总已同步。',
            sender=self.request.user,
            ref_type='finance_income',
            ref_id=income.id,
        )

    def perform_destroy(self, instance):
        project = instance.project
        title = instance.title
        income_id = instance.id
        instance.delete()
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
    queryset = FinanceReceipt.objects.all().order_by('-created_at')

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

    filterset_fields = ['expense', 'uploaded_by']
    search_fields = ['expense__title']

    def create(self, request, *args, **kwargs):
        """上传票据"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = serializer.validated_data['expense']
        is_finance_manager = (
            request.user.global_role in ['teacher', 'sys_admin']
            or expense.project.leader_id == request.user.id
        )
        if not is_finance_manager and expense.spender_id != request.user.id:
            return error_response(
                message='只能为本人经办的支出上传票据',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if (
            not is_finance_manager
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
        return success_response(
            FinanceReceiptSerializer(receipt).data,
            message='票据上传成功',
            http_status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """删除票据"""
        instance = self.get_object()
        expense = instance.expense
        is_finance_manager = (
            request.user.global_role in ['teacher', 'sys_admin']
            or expense.project.leader_id == request.user.id
        )
        can_delete_own_draft = (
            instance.uploaded_by_id == request.user.id
            and expense.spender_id == request.user.id
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
        instance.delete()
        return success_response(message='票据删除成功')
