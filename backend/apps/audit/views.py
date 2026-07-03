"""
审计日志视图
- OperationLogViewSet: 操作日志只读查询（list/retrieve）+ 模块统计 + 最近日志
权限：老师或管理员（IsTeacherOrAdmin）
"""
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import action
from rest_framework.viewsets import ReadOnlyModelViewSet

from common.response import success_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsTeacherOrAdmin
from .models import OperationLog
from .serializers import OperationLogSerializer, OperationLogListSerializer


class OperationLogViewSet(MultiSerializerMixin, MultiPermissionMixin, ReadOnlyModelViewSet):
    """
    操作日志 ViewSet（只读）
    - list: 操作日志列表，支持按 module(object_type)、operator、operation_type、时间范围筛选
    - retrieve: 查看操作日志详情
    - module_stats: 按模块统计操作数
    - recent: 最近 N 条操作日志
    权限：老师或管理员
    """
    queryset = OperationLog.objects.select_related('operator').all()

    serializer_classes_by_action = {
        'list': OperationLogListSerializer,
        'retrieve': OperationLogSerializer,
    }

    permission_classes_by_action = {
        'list': [IsTeacherOrAdmin],
        'retrieve': [IsTeacherOrAdmin],
        'module_stats': [IsTeacherOrAdmin],
        'recent': [IsTeacherOrAdmin],
    }

    # 默认权限
    permission_classes = [IsTeacherOrAdmin]

    filterset_fields = ['module', 'operator', 'operation_type', 'is_success']
    search_fields = ['description', 'request_path', 'object_type']
    ordering_fields = ['created_at', 'response_status']

    def get_queryset(self):
        """支持按时间范围、模块名、操作类型、操作人筛选"""
        queryset = super().get_queryset()

        # 按 module（object_type）筛选
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module=module)

        # 按 operator（操作人 ID）筛选
        operator = self.request.query_params.get('operator')
        if operator:
            queryset = queryset.filter(operator_id=operator)

        # 按 operation_type（操作类型）筛选
        operation_type = self.request.query_params.get('operation_type')
        if operation_type:
            queryset = queryset.filter(operation_type=operation_type)

        # 按时间范围筛选
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset

    def list(self, request, *args, **kwargs):
        """操作日志列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """操作日志详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def module_stats(self, request):
        """
        按模块统计操作数
        GET /api/v1/audit/logs/module_stats/
        可选参数: days（统计最近 N 天的数据，默认 30）
        """
        days = request.query_params.get('days', 30)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 30

        # 统计最近 N 天的数据
        start_time = timezone.now() - timedelta(days=days)
        queryset = self.get_queryset().filter(created_at__gte=start_time)

        # 按模块分组统计
        stats = queryset.values('module').annotate(
            total=Count('id'),
            success_count=Count('id', filter=Q(is_success=True)),
            fail_count=Count('id', filter=Q(is_success=False)),
        ).order_by('-total')

        # 按操作类型统计
        type_stats = queryset.values('operation_type').annotate(
            total=Count('id')
        ).order_by('-total')

        result = {
            'days': days,
            'module_stats': list(stats),
            'operation_type_stats': list(type_stats),
            'total': queryset.count(),
        }
        return success_response(result)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        最近 N 条操作日志
        GET /api/v1/audit/logs/recent/
        可选参数: limit（条数，默认 20，最大 100）
        """
        limit = request.query_params.get('limit', 20)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 20
        # 限制最大 100 条
        limit = min(max(limit, 1), 100)

        queryset = self.get_queryset()[:limit]
        serializer = OperationLogListSerializer(queryset, many=True)
        return success_response(serializer.data)
