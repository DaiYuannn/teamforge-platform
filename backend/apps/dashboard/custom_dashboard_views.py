"""
自定义看板视图
- CustomDashboardViewSet: 看板 CRUD + set_default（设为默认）
每个用户只能管理自己的看板；默认看板全局唯一（同一用户仅一条）
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

from common.response import success_response, error_response
from .custom_dashboard_models import CustomDashboard
from .custom_dashboard_serializers import CustomDashboardSerializer


class CustomDashboardViewSet(ModelViewSet):
    """
    自定义看板管理 ViewSet
    - list/retrieve/create/update/destroy: 仅操作当前用户的看板
    - set_default: 设为默认看板（取消该用户其他默认）
    """

    serializer_class = CustomDashboardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """仅返回当前用户的看板"""
        if getattr(self, 'swagger_fake_view', False):
            return CustomDashboard.objects.none()
        return CustomDashboard.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _ensure_single_default(self, user, exclude_id=None):
        """确保同一用户仅有一条默认看板"""
        qs = CustomDashboard.objects.filter(user=user, is_default=True)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        qs.update(is_default=False)

    def create(self, request, *args, **kwargs):
        """创建看板"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dashboard = serializer.save(user=request.user)
        if dashboard.is_default:
            self._ensure_single_default(request.user, exclude_id=dashboard.id)
        return success_response(
            CustomDashboardSerializer(dashboard).data,
            message='看板创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新看板"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        dashboard = serializer.save()
        if dashboard.is_default:
            self._ensure_single_default(request.user, exclude_id=dashboard.id)
        return success_response(
            CustomDashboardSerializer(dashboard).data,
            message='看板更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除看板"""
        instance = self.get_object()
        instance.delete()
        return success_response(message='看板已删除')

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        设为默认看板
        POST /api/v1/dashboard/custom/{id}/set_default/
        """
        dashboard = self.get_object()
        self._ensure_single_default(request.user, exclude_id=dashboard.id)
        dashboard.is_default = True
        dashboard.save(update_fields=['is_default', 'updated_at'])
        return success_response(
            CustomDashboardSerializer(dashboard).data,
            message='已设为默认看板',
        )

    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        获取当前用户的默认看板
        GET /api/v1/dashboard/custom/default/
        """
        dashboard = CustomDashboard.objects.filter(
            user=request.user, is_default=True
        ).first()
        if not dashboard:
            return error_response(message='未找到默认看板', code=1004)
        return success_response(
            CustomDashboardSerializer(dashboard).data,
            message='success',
        )

    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        dashboard = self.get_object()
        config = dashboard.config or {}
        widgets = config.get('widgets') or ['signals', 'priority']
        project_id = config.get('project_id')
        range_days = {'week': 7, 'month': 30, 'quarter': 90}.get(
            config.get('date_range'), 30,
        )
        since = timezone.now() - timedelta(days=range_days)
        payload = {}
        for widget in widgets:
            if not isinstance(widget, str):
                continue
            builder = getattr(self, f'_build_{widget}', None)
            if builder:
                payload[widget] = builder(project_id=project_id, since=since)
        return success_response({
            'dashboard': CustomDashboardSerializer(dashboard).data,
            'generated_at': timezone.now().isoformat(),
            'widgets': payload,
        })

    @staticmethod
    def _build_signals(*, project_id, since):
        from apps.projects.models import Project
        from apps.tasks.models import Task
        from apps.users.models import User

        projects = Project.objects.all()
        tasks = Task.objects.all()
        if project_id:
            projects = projects.filter(pk=project_id)
            tasks = tasks.filter(project_id=project_id)
        return {
            'metrics': [
                {'label': 'Projects', 'value': projects.count(), 'route': '/projects'},
                {'label': 'Active projects', 'value': projects.filter(status='active').count(), 'route': '/projects?status=active'},
                {'label': 'Pending tasks', 'value': tasks.exclude(status='done').count(), 'route': '/tasks'},
                {'label': 'Active members', 'value': User.objects.filter(is_active=True).count(), 'route': '/members'},
            ],
        }

    @staticmethod
    def _build_priority(*, project_id, since):
        from apps.tasks.models import Task

        tasks = Task.objects.exclude(status=Task.Status.DONE).select_related(
            'project', 'assignee',
        )
        if project_id:
            tasks = tasks.filter(project_id=project_id)
        tasks = tasks.order_by('deadline', '-priority')[:20]
        return {
            'total': tasks.count(),
            'items': [{
                'id': task.id,
                'title': task.title,
                'project_name': task.project.name,
                'assignee_name': task.assignee.name if task.assignee else '',
                'status': task.status,
                'deadline': task.deadline.isoformat() if task.deadline else None,
                'route': f'/tasks?task={task.id}',
            } for task in tasks],
        }

    @staticmethod
    def _build_delivery(*, project_id, since):
        from apps.projects.models import Project

        projects = Project.objects.annotate(task_count=Count('tasks')).order_by(
            '-updated_at',
        )
        if project_id:
            projects = projects.filter(pk=project_id)
        return {
            'items': [{
                'id': project.id,
                'name': project.name,
                'code': project.code,
                'stage': project.get_current_stage_display(),
                'status': project.get_status_display(),
                'task_count': project.task_count,
                'updated_at': project.updated_at.isoformat(),
                'route': f'/projects/{project.id}',
            } for project in projects[:20]],
        }

    @staticmethod
    def _build_business(*, project_id, since):
        from apps.competitions.models import Competition
        from apps.finance.models import FinanceExpense
        from apps.intellectual_property.models import IntellectualPropertyApplication

        expenses = FinanceExpense.objects.filter(expense_date__gte=since.date())
        competitions = Competition.objects.all()
        applications = IntellectualPropertyApplication.objects.all()
        if project_id:
            expenses = expenses.filter(project_id=project_id)
            competitions = competitions.filter(project_id=project_id)
            applications = applications.filter(related_project_id=project_id)
        total = expenses.aggregate(value=Sum('amount'))['value'] or 0
        return {
            'metrics': [
                {'label': 'Period expense', 'value': float(total), 'format': 'currency', 'route': '/finance'},
                {'label': 'Competitions', 'value': competitions.count(), 'route': '/competitions'},
                {'label': 'Awarded', 'value': competitions.filter(is_awarded=True).count(), 'route': '/competitions'},
                {'label': 'IP applications', 'value': applications.count(), 'route': '/intellectual-property'},
            ],
        }
