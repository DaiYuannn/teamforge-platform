"""
统一待办视图（N08）
聚合多来源待办事项，返回统一的待办列表：
- 待处理任务（分配给当前用户且未完成/未取消）
- 逾期任务（分配给当前用户且已逾期）
- 待审批敏感资料申请（当前用户为审批人角色时）
- 待审核贡献记录（当前用户为老师/管理员时）

返回统一结构：type / title / url / priority / due_date / id
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response


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
            if user.global_role in ('sens_approver', 'sys_admin'):
                todos.extend(self._collect_sensitive_approvals(user))

        # 4. 待审核贡献记录（老师/管理员）
        if not filter_type or filter_type == 'contribution_review':
            if user.global_role in ('teacher', 'sys_admin'):
                todos.extend(self._collect_contribution_reviews(user))

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
        qs = Task.objects.filter(
            assignee=user,
        ).exclude(status__in=_TASK_DONE_STATUSES).select_related('project')

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
                'url': f'/api/v1/tasks/{task.id}/',
                'priority': task.priority,
                'due_date': task.deadline.isoformat() if task.deadline else None,
                'project_id': task.project_id,
                'project_name': task.project.name,
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
                'url': f'/api/v1/sensitive/requests/{req.id}/',
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

        for contrib in qs:
            todos.append({
                'id': contrib.id,
                'type': 'contribution_review',
                'title': f'待审核贡献：{contrib.user.name} - {contrib.get_contribution_type_display()}',
                'url': f'/api/v1/contributions/contributions/{contrib.id}/',
                'priority': 'medium',
                'due_date': contrib.created_at.isoformat() if contrib.created_at else None,
                'project_id': contrib.project_id,
            })
        return todos
