"""
自定义报表视图
- CustomReportViewSet: 自定义报表 CRUD + generate（根据 config 生成报表数据）
- ScheduledReportViewSet: 定时报表 CRUD + run_now（手动触发运行）
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from .custom_report_models import CustomReport
from .scheduled_report_models import ScheduledReport
from .custom_report_serializers import (
    CustomReportSerializer,
    ScheduledReportSerializer,
)


class CustomReportViewSet(ModelViewSet):
    """
    自定义报表管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 创建者/老师/管理员
    - generate: 根据 config 生成报表数据
    """

    serializer_class = CustomReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = CustomReport.objects.select_related('created_by').all()
    filterset_fields = ['report_type', 'is_scheduled', 'created_by']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(created_by=request.user)
        return success_response(
            CustomReportSerializer(report).data,
            message='报表创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        return success_response(
            CustomReportSerializer(report).data,
            message='报表更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(message='报表已删除')

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """
        生成报表数据
        POST /api/v1/exports/custom-reports/{id}/generate/
        根据 config 中的 data_source / filters / group_by / chart_type 聚合数据
        """
        report = self.get_object()
        data = _generate_report_data(report)
        return success_response(
            {
                'report': CustomReportSerializer(report).data,
                'generated_at': timezone.now().isoformat(),
                'data': data,
            },
            message='报表数据生成成功',
        )


def _generate_report_data(report):
    """
    根据 CustomReport.config 生成报表数据
    config 结构示例:
    {
        "data_source": "task" | "finance" | "project" | "competition",
        "filters": {"project_id": 1, "status": "done"},
        "group_by": "status" | "category" | "level" | "month",
        "chart_type": "bar" | "pie" | "line" | "table"
    }
    """
    config = report.config or {}
    data_source = config.get('data_source', 'project')
    filters = config.get('filters', {}) or {}
    group_by = config.get('group_by', '')
    chart_type = config.get('chart_type', 'table')

    result = {
        'data_source': data_source,
        'group_by': group_by,
        'chart_type': chart_type,
        'filters': filters,
        'summary': {},
        'groups': [],
    }

    if data_source == 'task':
        from apps.tasks.models import Task
        qs = Task.objects.all()
        if 'project_id' in filters:
            qs = qs.filter(project_id=filters['project_id'])
        if 'status' in filters:
            qs = qs.filter(status=filters['status'])
        result['summary'] = {
            'total': qs.count(),
            'done': qs.filter(status=Task.Status.DONE).count(),
            'overdue': qs.filter(status=Task.Status.OVERDUE).count(),
            'doing': qs.filter(status=Task.Status.DOING).count(),
            'todo': qs.filter(status=Task.Status.TODO).count(),
        }
        if group_by == 'status':
            rows = qs.values('status').annotate(count=Count('id')).order_by('status')
            result['groups'] = [
                {'key': r['status'], 'label': r['status'], 'count': r['count']}
                for r in rows
            ]
        elif group_by == 'project':
            rows = qs.values('project__name').annotate(count=Count('id')).order_by('-count')
            result['groups'] = [
                {'key': r['project__name'], 'label': r['project__name'], 'count': r['count']}
                for r in rows
            ]
        else:
            rows = qs.values('status').annotate(count=Count('id'))
            result['groups'] = [
                {'key': r['status'], 'label': r['status'], 'count': r['count']}
                for r in rows
            ]

    elif data_source == 'finance':
        from apps.finance.models import FinanceExpense
        qs = FinanceExpense.objects.all()
        if 'project_id' in filters:
            qs = qs.filter(project_id=filters['project_id'])
        if 'category' in filters:
            qs = qs.filter(category=filters['category'])
        total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        result['summary'] = {
            'total_amount': float(total),
            'count': qs.count(),
        }
        if group_by == 'category':
            rows = qs.values('category').annotate(
                count=Count('id'), total=Sum('amount')
            ).order_by('-total')
            result['groups'] = [
                {
                    'key': r['category'],
                    'label': r['category'],
                    'count': r['count'],
                    'total': float(r['total'] or 0),
                }
                for r in rows
            ]
        elif group_by == 'project':
            rows = qs.values('project__name').annotate(
                count=Count('id'), total=Sum('amount')
            ).order_by('-total')
            result['groups'] = [
                {
                    'key': r['project__name'],
                    'label': r['project__name'],
                    'count': r['count'],
                    'total': float(r['total'] or 0),
                }
                for r in rows
            ]
        else:
            rows = qs.values('category').annotate(
                count=Count('id'), total=Sum('amount')
            ).order_by('-total')
            result['groups'] = [
                {
                    'key': r['category'],
                    'label': r['category'],
                    'count': r['count'],
                    'total': float(r['total'] or 0),
                }
                for r in rows
            ]

    elif data_source == 'project':
        from apps.projects.models import Project
        qs = Project.objects.all()
        if 'status' in filters:
            qs = qs.filter(status=filters['status'])
        result['summary'] = {
            'total': qs.count(),
            'active': qs.filter(status=Project.Status.ACTIVE).count(),
            'closed': qs.filter(status=Project.Status.CLOSED).count(),
            'paused': qs.filter(status=Project.Status.PAUSED).count(),
        }
        if group_by == 'status':
            rows = qs.values('status').annotate(count=Count('id')).order_by('status')
            result['groups'] = [
                {'key': r['status'], 'label': r['status'], 'count': r['count']}
                for r in rows
            ]
        else:
            rows = qs.values('current_stage').annotate(count=Count('id')).order_by('current_stage')
            result['groups'] = [
                {'key': r['current_stage'], 'label': f'stage_{r["current_stage"]}', 'count': r['count']}
                for r in rows
            ]

    elif data_source == 'competition':
        from apps.competitions.models import Competition
        qs = Competition.objects.all()
        if 'project_id' in filters:
            qs = qs.filter(project_id=filters['project_id'])
        if 'level' in filters:
            qs = qs.filter(level=filters['level'])
        result['summary'] = {
            'total': qs.count(),
            'awarded': qs.filter(is_awarded=True).count(),
            'promoted': qs.filter(is_promoted=True).count(),
        }
        if group_by == 'level':
            rows = qs.values('level').annotate(count=Count('id')).order_by('level')
            result['groups'] = [
                {'key': r['level'], 'label': r['level'], 'count': r['count']}
                for r in rows
            ]
        else:
            rows = qs.values('status').annotate(count=Count('id')).order_by('status')
            result['groups'] = [
                {'key': r['status'], 'label': r['status'], 'count': r['count']}
                for r in rows
            ]
    else:
        result['summary'] = {'message': '未知数据源'}

    return result


class ScheduledReportViewSet(ModelViewSet):
    """
    定时报表管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 认证用户均可
    - run_now: 手动触发运行（更新 last_run，计算 next_run）
    - activate / deactivate: 启用/停用
    """

    serializer_class = ScheduledReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = ScheduledReport.objects.select_related('report').all()
    filterset_fields = ['frequency', 'is_active', 'report']
    ordering_fields = ['created_at', 'next_run']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        # 根据频率计算下次运行时间
        schedule.next_run = _compute_next_run(schedule.frequency)
        schedule.save(update_fields=['next_run'])
        return success_response(
            ScheduledReportSerializer(schedule).data,
            message='定时报表创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        # 若频率变更，重新计算 next_run
        if 'frequency' in (request.data or {}):
            schedule.next_run = _compute_next_run(schedule.frequency)
            schedule.save(update_fields=['next_run'])
        return success_response(
            ScheduledReportSerializer(schedule).data,
            message='定时报表更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(message='定时报表已删除')

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """
        手动触发运行
        POST /api/v1/exports/scheduled-reports/{id}/run_now/
        更新 last_run 为当前时间，并根据频率计算 next_run
        """
        schedule = self.get_object()
        now = timezone.now()
        schedule.last_run = now
        schedule.next_run = _compute_next_run(schedule.frequency, base=now)
        schedule.save(update_fields=['last_run', 'next_run'])
        return success_response(
            ScheduledReportSerializer(schedule).data,
            message='定时报表已手动运行',
        )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """启用定时报表"""
        schedule = self.get_object()
        schedule.is_active = True
        if not schedule.next_run:
            schedule.next_run = _compute_next_run(schedule.frequency)
        schedule.save(update_fields=['is_active', 'next_run'])
        return success_response(
            ScheduledReportSerializer(schedule).data,
            message='定时报表已启用',
        )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """停用定时报表"""
        schedule = self.get_object()
        schedule.is_active = False
        schedule.save(update_fields=['is_active'])
        return success_response(
            ScheduledReportSerializer(schedule).data,
            message='定时报表已停用',
        )


def _compute_next_run(frequency, base=None):
    """根据频率计算下次运行时间"""
    base = base or timezone.now()
    if frequency == ScheduledReport.Frequency.DAILY:
        return base + timedelta(days=1)
    elif frequency == ScheduledReport.Frequency.WEEKLY:
        return base + timedelta(weeks=1)
    elif frequency == ScheduledReport.Frequency.MONTHLY:
        # 粗略按 30 天计算
        return base + timedelta(days=30)
    return base + timedelta(days=1)
