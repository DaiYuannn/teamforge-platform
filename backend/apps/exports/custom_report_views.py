"""自定义报表与定时报表 API。"""
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from common.permissions import IsInternalTeamMember
from common.response import error_response, success_response
from .custom_report_models import CustomReport
from .custom_report_serializers import (
    CustomReportSerializer,
    ScheduledReportExecutionSerializer,
    ScheduledReportSerializer,
)
from .scheduled_report_models import ScheduledReport
from .scheduled_report_service import (
    compute_next_run,
    execute_scheduled_report,
    schedule_scope_error,
)


class CustomReportViewSet(ModelViewSet):
    serializer_class = CustomReportSerializer
    permission_classes = [IsInternalTeamMember]
    queryset = CustomReport.objects.select_related('created_by').all()
    filterset_fields = ['report_type', 'is_scheduled', 'created_by']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.global_role in ('teacher', 'sys_admin'):
            return queryset
        return queryset.filter(created_by=self.request.user)

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
        instance = self.get_object()
        if (
            instance.created_by_id != request.user.id
            and request.user.global_role not in ('teacher', 'sys_admin')
        ):
            return error_response(message='只能修改自己创建的报表', code=403)
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.pop('partial', False),
        )
        serializer.is_valid(raise_exception=True)
        return success_response(
            CustomReportSerializer(serializer.save()).data,
            message='报表更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if (
            instance.created_by_id != request.user.id
            and request.user.global_role not in ('teacher', 'sys_admin')
        ):
            return error_response(message='只能删除自己创建的报表', code=403)
        instance.delete()
        return success_response(message='报表已删除')

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        report = self.get_object()
        return success_response(
            {
                'report': CustomReportSerializer(report).data,
                'generated_at': timezone.now().isoformat(),
                'data': _generate_report_data(report, user=request.user),
            },
            message='报表数据生成成功',
        )


def _choice_label(model, field_name, value):
    field = model._meta.get_field(field_name)
    return dict(field.flatchoices).get(value, value)


def _generate_report_data(report, *, user):
    """根据 CustomReport.config 生成可导出的汇总与分组数据。"""
    if (
        not user
        or not getattr(user, 'is_active', False)
        or getattr(user, 'membership_status', '') not in {'active', 'on_leave'}
    ):
        raise PermissionError('只有内部成员可以生成团队业务报表')
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
        if filters.get('project_id'):
            qs = qs.filter(project_id=filters['project_id'])
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])
        result['summary'] = {
            'total': qs.count(),
            'done': qs.filter(status=Task.Status.DONE).count(),
            'overdue': qs.filter(status=Task.Status.OVERDUE).count(),
            'doing': qs.filter(status=Task.Status.DOING).count(),
            'todo': qs.filter(status=Task.Status.TODO).count(),
        }
        if group_by == 'project':
            rows = qs.values('project__name').annotate(count=Count('id')).order_by('-count')
            result['groups'] = [
                {
                    'key': row['project__name'],
                    'label': row['project__name'] or '未分配',
                    'count': row['count'],
                }
                for row in rows
            ]
        else:
            rows = qs.values('status').annotate(count=Count('id')).order_by('status')
            result['groups'] = [
                {
                    'key': row['status'],
                    'label': _choice_label(Task, 'status', row['status']),
                    'count': row['count'],
                }
                for row in rows
            ]

    elif data_source == 'finance':
        from apps.finance.models import FinanceExpense

        qs = FinanceExpense.objects.all()
        if filters.get('project_id'):
            qs = qs.filter(project_id=filters['project_id'])
        if filters.get('category'):
            qs = qs.filter(category=filters['category'])
        total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        result['summary'] = {'total_amount': float(total), 'count': qs.count()}
        grouping = 'project__name' if group_by == 'project' else 'category'
        rows = qs.values(grouping).annotate(count=Count('id'), total=Sum('amount')).order_by('-total')
        result['groups'] = [
            {
                'key': row[grouping],
                'label': (
                    row[grouping]
                    if grouping == 'project__name'
                    else _choice_label(FinanceExpense, 'category', row[grouping])
                ),
                'count': row['count'],
                'total': float(row['total'] or 0),
            }
            for row in rows
        ]

    elif data_source == 'competition':
        from apps.competitions.models import Competition

        qs = Competition.objects.all()
        if filters.get('project_id'):
            qs = qs.filter(project_id=filters['project_id'])
        if filters.get('level'):
            qs = qs.filter(level=filters['level'])
        result['summary'] = {
            'total': qs.count(),
            'awarded': qs.filter(is_awarded=True).count(),
            'promoted': qs.filter(is_promoted=True).count(),
        }
        grouping = 'level' if group_by == 'level' else 'status'
        rows = qs.values(grouping).annotate(count=Count('id')).order_by(grouping)
        result['groups'] = [
            {
                'key': row[grouping],
                'label': _choice_label(Competition, grouping, row[grouping]),
                'count': row['count'],
            }
            for row in rows
        ]

    elif data_source == 'project':
        from apps.projects.models import Project

        qs = Project.objects.all()
        if filters.get('status'):
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
                {
                    'key': row['status'],
                    'label': _choice_label(Project, 'status', row['status']),
                    'count': row['count'],
                }
                for row in rows
            ]
        else:
            rows = qs.values('current_stage').annotate(count=Count('id')).order_by('current_stage')
            result['groups'] = [
                {
                    'key': row['current_stage'],
                    'label': f'第 {row["current_stage"]} 阶段',
                    'count': row['count'],
                }
                for row in rows
            ]
    else:
        result['summary'] = {'message': '未知数据源'}

    return result


class ScheduledReportViewSet(ModelViewSet):
    serializer_class = ScheduledReportSerializer
    permission_classes = [IsInternalTeamMember]
    queryset = (
        ScheduledReport.objects.select_related('report', 'created_by')
        .prefetch_related('recipients', 'executions')
        .all()
    )
    filterset_fields = ['frequency', 'file_format', 'is_active', 'report']
    ordering_fields = ['created_at', 'next_run', 'last_run']

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.global_role in ('teacher', 'sys_admin'):
            return queryset
        return queryset.filter(
            Q(created_by=user)
            | Q(created_by__isnull=True, report__created_by=user)
            | Q(recipients=user)
        ).distinct()

    @staticmethod
    def _can_manage(user, schedule):
        return (
            user.global_role in ('teacher', 'sys_admin')
            or schedule.created_by_id == user.id
            or (
                schedule.created_by_id is None
                and schedule.report.created_by_id == user.id
            )
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save(created_by=request.user)
        schedule.next_run = compute_next_run(schedule)
        schedule.save(update_fields=['next_run'])
        return success_response(
            ScheduledReportSerializer(schedule).data,
            message='定时报表创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage(request.user, instance):
            return error_response(
                message='只能修改自己创建的计划',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.pop('partial', False),
        )
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        schedule.next_run = compute_next_run(schedule) if schedule.is_active else None
        schedule.save(update_fields=['next_run'])
        return success_response(
            ScheduledReportSerializer(schedule).data,
            message='定时报表更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage(request.user, instance):
            return error_response(
                message='只能删除自己创建的计划',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return success_response(message='定时报表已删除')

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        schedule = self.get_object()
        if not self._can_manage(request.user, schedule):
            return error_response(
                message='只有计划创建人、老师或管理员可以立即运行',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        scope_error = schedule_scope_error(schedule)
        if scope_error:
            return error_response(message=scope_error)
        execution = execute_scheduled_report(schedule, user=request.user)
        return success_response(
            ScheduledReportExecutionSerializer(execution).data,
            message='报表已生成',
        )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        schedule = self.get_object()
        if not self._can_manage(request.user, schedule):
            return error_response(
                message='只有计划创建人、老师或管理员可以启用',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        scope_error = schedule_scope_error(schedule)
        if scope_error:
            return error_response(message=scope_error)
        schedule.is_active = True
        schedule.next_run = compute_next_run(schedule)
        schedule.save(update_fields=['is_active', 'next_run'])
        return success_response(ScheduledReportSerializer(schedule).data, message='定时报表已启用')

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        schedule = self.get_object()
        if not self._can_manage(request.user, schedule):
            return error_response(
                message='只有计划创建人、老师或管理员可以停用',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        schedule.is_active = False
        schedule.next_run = None
        schedule.save(update_fields=['is_active', 'next_run'])
        return success_response(ScheduledReportSerializer(schedule).data, message='定时报表已停用')

    @action(
        detail=True,
        methods=['get'],
        url_path=r'executions/(?P<execution_id>\d+)/download',
    )
    def download_execution(self, request, pk=None, execution_id=None):
        schedule = self.get_object()
        execution = schedule.executions.filter(pk=execution_id).first()
        if not execution or not execution.file:
            return error_response(message='报表文件不存在', code=404)
        return FileResponse(
            execution.file.open('rb'),
            as_attachment=True,
            filename=execution.file_name,
        )
