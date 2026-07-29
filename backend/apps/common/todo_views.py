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
                    'workflow_approval',
                    'contribution_review', 'ip_todo',
                    'finance_review', 'finance_payment',
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
                                'flow_id': serializers.IntegerField(required=False),
                                'flow_name': serializers.CharField(required=False),
                                'current_step_name': serializers.CharField(required=False),
                                'reviewer_ids': serializers.ListField(
                                    child=serializers.IntegerField(),
                                    required=False,
                                ),
                                'reviewer_roles': serializers.ListField(
                                    child=serializers.CharField(),
                                    required=False,
                                ),
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

        # 3. 待审批敏感资料申请（按小团队实际审批范围）
        if not filter_type or filter_type == 'approval':
            todos.extend(self._collect_sensitive_approvals(user))

        # 4. 通用审批流：只给真正轮到的明确审批人一张卡。
        if not filter_type or filter_type == 'workflow_approval':
            todos.extend(self._collect_workflow_approvals(user))

        # 5. 待审核贡献：只发给明确分派的审核人；系统管理员保留兜底。
        if not filter_type or filter_type == 'contribution_review':
            todos.extend(self._collect_contribution_reviews(user))

        # 6. 知识产权流程待办
        if not filter_type or filter_type == 'ip_todo':
            todos.extend(self._collect_ip_todos(user))

        # 7. 经费流程待办。只按项目负责人/显式财务权限路由，
        # 不把所有老师都广播为经费审核人。
        if not filter_type or filter_type in ('finance_review', 'finance_payment'):
            todos.extend(self._collect_finance_todos(user, filter_type))

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
        from apps.sensitive.permissions import (
            can_review_sensitive_request,
            sensitive_review_team_ids,
        )

        todos = []
        review_filter = Q(
            sensitive_data__team_id__in=sensitive_review_team_ids(user),
        )
        if (
            user.global_role == 'sens_approver'
            and user.membership_status in {'active', 'on_leave'}
        ):
            review_filter |= Q(sensitive_data__team__isnull=True)
        # If the same business request is already wrapped by a generic
        # ApprovalRequest, the workflow card is the single source of truth.
        from .approval_models import ApprovalRequest

        linked_access_ids = set()
        for metadata in ApprovalRequest.objects.filter(
            status=ApprovalRequest.Status.PENDING,
            flow__flow_type='sensitive',
        ).values_list('metadata', flat=True):
            if isinstance(metadata, dict) and metadata.get('access_request_id'):
                linked_access_ids.add(metadata['access_request_id'])

        qs = SensitiveAccessRequest.objects.filter(
            review_filter,
            status=SensitiveAccessRequest.Status.PENDING,
        ).exclude(
            applicant=user,
        ).exclude(
            id__in=linked_access_ids,
        ).select_related('sensitive_data', 'sensitive_data__team', 'applicant')

        for req in qs:
            if not can_review_sensitive_request(user, req):
                continue
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

    def _collect_workflow_approvals(self, user):
        """Collect generic approval requests assigned to this exact reviewer."""
        from .approval_models import ApprovalRequest
        from .approval_services import (
            approval_reviewer_details,
            approval_step,
            should_receive_approval_todo,
        )

        todos = []
        queryset = ApprovalRequest.objects.filter(
            status=ApprovalRequest.Status.PENDING,
        ).exclude(
            applicant=user,
        ).select_related(
            'flow',
            'applicant',
        ).order_by('created_at', 'id')
        for approval_request in queryset:
            if not should_receive_approval_todo(user, approval_request):
                continue
            step = approval_step(approval_request)
            current_step_name = str(
                step.get('name')
                or f'第 {approval_request.current_step + 1} 级审批'
            )
            reviewer_details = approval_reviewer_details(approval_request)
            todos.append({
                'id': approval_request.id,
                'type': 'workflow_approval',
                'title': (
                    f'待审批：{approval_request.title}'
                    f'（{approval_request.applicant.name}）'
                ),
                'url': (
                    '/admin/platform-capabilities'
                    f'?tab=approvals&request_id={approval_request.id}'
                ),
                'route_name': 'PlatformCapabilities',
                'route_params': {},
                'route_query': {
                    'tab': 'approvals',
                    'request_id': approval_request.id,
                },
                'priority': 'high',
                'due_date': (
                    approval_request.created_at.isoformat()
                    if approval_request.created_at else None
                ),
                'applicant_id': approval_request.applicant_id,
                'flow_id': approval_request.flow_id,
                'flow_name': approval_request.flow.name,
                'current_step_name': current_step_name,
                'reviewer_ids': reviewer_details['reviewer_ids'],
                'reviewer_roles': reviewer_details['reviewer_roles'],
                'status': approval_request.status,
                'status_display': approval_request.get_status_display(),
            })
        return todos

    def _collect_contribution_reviews(self, user):
        """采集待审核的贡献记录"""
        from apps.contributions.models import Contribution

        todos = []
        qs = Contribution.objects.filter(
            status=Contribution.Status.PENDING,
        ).select_related('user', 'project')
        if user.global_role != 'sys_admin':
            from apps.projects.models import ProjectMember

            qs = qs.filter(
                Q(reviewer=user)
                | Q(
                    reviewer__isnull=True,
                    project__leader=user,
                )
                | Q(
                    reviewer__isnull=True,
                    project__members__user=user,
                    project__members__role_in_project=(
                        ProjectMember.RoleInProject.LEADER
                    ),
                    project__members__status=ProjectMember.Status.ACTIVE,
                )
            ).exclude(
                user=user,
            ).exclude(
                filled_by=user,
            ).distinct()

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

    def _collect_finance_todos(self, user, filter_type=''):
        """采集待审核报销与待打款事项，并沿用经费模块的项目级权限。"""
        from apps.finance.models import FinanceExpense
        from common.permissions import user_has_custom_permission
        from common.project_access import has_active_project_leadership

        todos = []
        queryset = (
            FinanceExpense.objects.filter(
                reimbursement_status__in=[
                    FinanceExpense.ReimbursementStatus.PENDING,
                    FinanceExpense.ReimbursementStatus.APPROVED,
                ],
            )
            .select_related('project', 'spender', 'applied_by')
            .order_by('applied_at', 'created_at')
        )
        for expense in queryset:
            can_manage_project = user_has_custom_permission(
                user,
                'finance.manage',
                project_id=expense.project_id,
            )
            if expense.reimbursement_status == FinanceExpense.ReimbursementStatus.PENDING:
                item_type = 'finance_review'
                is_assignee = (
                    expense.project.leader_id == user.id
                    or has_active_project_leadership(user, expense.project)
                    or can_manage_project
                )
                title = f'待审核报销：{expense.title}（{expense.amount} 元）'
                priority = 'high'
                due_at = expense.applied_at or expense.created_at
            else:
                item_type = 'finance_payment'
                is_assignee = (
                    user.global_role == 'sys_admin'
                    or can_manage_project
                )
                title = f'待登记打款：{expense.title}（{expense.amount} 元）'
                priority = 'medium'
                due_at = expense.reviewed_at or expense.created_at

            if not is_assignee or (filter_type and filter_type != item_type):
                continue
            todos.append({
                'id': expense.id,
                'type': item_type,
                'title': title,
                'url': (
                    f'/finance?project_id={expense.project_id}'
                    f'&expense_id={expense.id}&action={item_type}'
                ),
                'route_name': 'FinanceOverview',
                'route_params': {},
                'route_query': {
                    'project_id': expense.project_id,
                    'expense_id': expense.id,
                    'action': item_type,
                },
                'priority': priority,
                'due_date': due_at.isoformat() if due_at else None,
                'project_id': expense.project_id,
                'project_name': expense.project.name,
                'status': expense.reimbursement_status,
                'status_display': expense.get_reimbursement_status_display(),
            })
        return todos
