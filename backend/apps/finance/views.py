"""
经费视图
关键：经费明细和票据对所有认证用户可见（权限 IsAuthenticated 即可读取）
- FinanceBudgetViewSet: 经费总表 CRUD
- FinanceExpenseViewSet: 经费明细 CRUD（含票据上传）
- FinanceReceiptViewSet: 票据管理
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from .models import FinanceBudget, FinanceExpense, FinanceReceipt
from .serializers import (
    FinanceBudgetSerializer,
    FinanceExpenseSerializer, FinanceExpenseListSerializer,
    FinanceReceiptSerializer,
)


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
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
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
    queryset = FinanceExpense.objects.all().order_by('-expense_date', '-created_at')

    serializer_classes_by_action = {
        'list': FinanceExpenseListSerializer,
        'retrieve': FinanceExpenseSerializer,
        'create': FinanceExpenseSerializer,
        'update': FinanceExpenseSerializer,
        'partial_update': FinanceExpenseSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
    }

    filterset_fields = ['project', 'category', 'spender', 'expense_date']
    search_fields = ['title', 'purpose', 'project__name']
    ordering_fields = ['expense_date', 'amount', 'created_at']

    def create(self, request, *args, **kwargs):
        """创建经费明细"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 自动设置经办人为当前用户（如未指定）
        if not serializer.validated_data.get('spender'):
            serializer.validated_data['spender'] = request.user
        expense = serializer.save()
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
        return success_response(FinanceExpenseSerializer(expense).data, message='经费明细更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除经费明细"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='经费明细删除成功')


class FinanceReceiptViewSet(MultiSerializerMixin, ModelViewSet):
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
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
    }

    filterset_fields = ['expense', 'uploaded_by']
    search_fields = ['expense__title']

    def create(self, request, *args, **kwargs):
        """上传票据"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
        self.check_object_permissions(request, instance)
        # 删除物理文件
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()
        return success_response(message='票据删除成功')
