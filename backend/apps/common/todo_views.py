"""
统一待办视图（N08）
聚合多来源待办事项，返回统一的待办列表：
- 待处理任务（分配给当前用户且未完成/未取消）
- 逾期任务（分配给当前用户且已逾期）
- 待审批敏感资料申请（当前用户为审批人角色时）
- 待审核贡献记录（当前用户为老师/管理员时）

返回统一结构：type / title / url / priority / due_date / id
"""
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response
from common.schema import success_response_schema


# 任务状态：已完成 / 已取消 视为已结束，不再计入待办
_TASK_DONE_STATUSES = ('done', 'cancelled')

# 优先级排序权重（值越大越紧急）
_PRIORITY_WEIGHT = {
    'urgent': 4,
    'high': 3,
    'medium': 2,
    'low': 1,
}


class UnifiedTodoView(APIView):
    """统一待办列表"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=[
                    'task', 'overdue_task', 'approval',
                    'contribution_review', 'ip_todo',
                ],
                required=False,
            ),
        ],
        responses={
            200: success_response_schema(
                'UnifiedTodoResponse',
                inline_serializer(
                    name='UnifiedTodoData',
                    fields={
                        'count': serializers.IntegerField(),
                        'results': inline_serializer(
                            name='UnifiedTodoItem',
                            many=True,
                            fields={
                                'id': serializers.IntegerField(),
                                'type': serializers.CharField(),
                                'title': serializers.CharField(),
                                'url': serializers.CharField(),
                                'route_name': serializers.CharField(),
                                'route_params': serializers.JSONField(),
                                'route_query': serializers.JSONField(),
                                'priority': serializers.CharField(),
                                'due_date': serializers.DateTimeField(allow_null=True),
                                'project_id': serializers.IntegerField(
                                    required=False, allow_null=True,
                                ),
                                'project_name': serializers.CharField(required=False),
                                'task_role': serializers.CharField(required=False),
                                'applicant_id': serializers.IntegerField(required=False),
                                'status': serializers.CharField(required=False),
                                'status_display': serializers.CharField(required=False),
                            },
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        """获取当前用户的统一待办列表"""
        user = request.user
        todos = []

        # 查询参数 type 用于按类型筛选
        filter_type = request.query_params.get('type', '').strip()

        # 1. 待处理任务 + 2. 逾期任务
        if not filter_type or filter_type in ('task', 'overdue_task'):
            todos.extend(self._collect_tasks(user, filter_type))

        # 3. 待审批敏感资料申请（审批人角色）
        if not filter_type or filter_type == 'approval':
            if user.global_role in ('sens_approver', 'teacher', 'sys_admin'):
                todos.extend(self._collect_sensitive_approvals(user))

        # 4. 待审核贡献：老师/管理员看全部，负责人看自己负责项目。
        if not filter_type or filter_type == 'contribution_review':
            if user.global_role in ('teacher', 'sys_admin') or user.led_projects.exists():
                todos.extend(self._collect_contribution_reviews(user))

        # 5. 知识产权流程待办
        if not filter_type or filter_type == 'ip_todo':
            todos.extend(self._collect_ip_todos(user))

        # 按优先级降序、截止时间升序排序
        todos.sort(
            key=lambda t: (
                -_PRIORITY_WEIGHT.get(t.get('priority'), 0),
                t.get('due_date') or '9999-12-31T23:59:59',
            )
        )

        return success_response({
            'count': len(todos),
            'results': todos,
        })

    # ------------------------------------------------------------------
    # 各来源采集方法
    # ------------------------------------------------------------------

    def _collect_tasks(self, user, filter_type=''):
        """采集待处理任务与逾期任务"""
        from apps.tasks.models import Task

        todos = []
        qs = (
            Task.objects.filter(
                Q(assignee=user)
                | Q(collaborators=user)
                | Q(reviewer=user, status=Task.Status.PENDING_REVIEW)
            )
            .exclude(status__in=_TASK_DONE_STATUSES)
            .select_related('project')
            .distinct()
        )

        for task in qs:
            is_overdue = task.is_overdue
            item_type = 'overdue_task' if is_overdue else 'task'
            # 如果指定了筛选类型，跳过不匹配的
            if filter_type and item_type != filter_type:
                continue
            todos.append({
                'id': task.id,
                'type': item_type,
                'title': task.title,
                'url': (
                    f'/tasks?project_id={task.project_id}'
                    f'&task_id={task.id}'
                ),
                'route_name': 'TaskList',
                'route_params': {},
                'route_query': {
                    'project_id': task.project_id,
                    'task_id': task.id,
                },
                'priority': task.priority,
                'due_date': task.deadline.isoformat() if task.deadline else None,
                'project_id': task.project_id,
                'project_name': task.project.name,
                'task_role': (
                    'reviewer'
                    if task.reviewer_id == user.id
                    and task.status == Task.Status.PENDING_REVIEW
                    else 'assignee'
                    if task.assignee_id == user.id
                    else 'collaborator'
                ),
            })
        return todos

    def _collect_sensitive_approvals(self, user):
        """采集待审批的敏感资料访问申请"""
        from apps.sensitive.models import SensitiveAccessRequest

        todos = []
        qs = SensitiveAccessRequest.objects.filter(
            status=SensitiveAccessRequest.Status.PENDING,
        ).select_related('sensitive_data', 'applicant')

        for req in qs:
            todos.append({
                'id': req.id,
                'type': 'approval',
                'title': f'待审批：{req.applicant.name} 申请访问 {req.sensitive_data.title}',
                'url': f'/sensitive/pending?request_id={req.id}',
                'route_name': 'SensitivePending',
                'route_params': {},
                'route_query': {'request_id': req.id},
                'priority': 'high',
                'due_date': req.created_at.isoformat() if req.created_at else None,
                'applicant_id': req.applicant_id,
            })
        return todos

    def _collect_contribution_reviews(self, user):
        """采集待审核的贡献记录"""
        from apps.contributions.models import Contribution

        todos = []
        qs = Contribution.objects.filter(
            status=Contribution.Status.PENDING,
        ).select_related('user', 'project')
        if user.global_role not in ('teacher', 'sys_admin'):
            qs = qs.filter(project__leader=user)

        for contrib in qs:
            todos.append({
                'id': contrib.id,
                'type': 'contribution_review',
                'title': f'待审核贡献：{contrib.user.name} - {contrib.get_contribution_type_display()}',
                'url': (
                    f'/contributions/pending?project_id={contrib.project_id}'
                    f'&contribution_id={contrib.id}'
                ),
                'route_name': 'PendingContributions',
                'route_params': {},
                'route_query': {
                    'project_id': contrib.project_id,
                    'contribution_id': contrib.id,
                },
                'priority': 'medium',
                'due_date': contrib.created_at.isoformat() if contrib.created_at else None,
                'project_id': contrib.project_id,
            })
        return todos

    def _collect_ip_todos(self, user):
        """采集当前用户真正需要处理的知识产权流程事项。"""
        from apps.intellectual_property.permissions import accessible_ip_applications

        queryset = accessible_ip_applications(user)
        conditions = (
            Q(main_writer=user, status='writing')
            | Q(project_reviewer=user, status='leader_review')
            | Q(related_project__leader=user, status='leader_review')
            | Q(teacher_confirmer=user, status='teacher_confirm')
            | Q(applicant_executor=user, status__in=['returned', 'modifying'])
            | Q(main_writer=user, status__in=['returned', 'modifying'])
        )
        if user.global_role in ('teacher', 'sys_admin'):
            conditions |= Q(
                status__in=['teacher_confirm', 'research_office_review'],
            )

        todos = []
        for application in (
            queryset.filter(conditions)
            .select_related('related_project')
            .distinct()
        ):
            high_priority = application.status in {
                'leader_review', 'teacher_confirm', 'returned',
            }
            todos.append({
                'id': application.id,
                'type': 'ip_todo',
                'title': f'知识产权待办：{application.title}',
                'url': f'/intellectual-property/{application.id}',
                'route_name': 'IPApplicationDetail',
                'route_params': {'id': application.id},
                'route_query': {},
                'priority': 'high' if high_priority else 'medium',
                'due_date': None,
                'project_id': application.related_project_id,
                'project_name': (
                    application.related_project.name
                    if application.related_project_id else ''
                ),
                'status': application.status,
                'status_display': application.get_status_display(),
            })
        return todos
