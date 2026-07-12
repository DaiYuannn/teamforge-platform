"""
成员工作量分析视图
- MemberWorkloadView: 返回每个成员的工作量
  - 任务数
  - 预估工时
  - 项目数
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response
from .models import User


class MemberWorkloadView(APIView):
    """
    成员工作量视图
    GET /api/v1/users/workload/
    返回每个成员的任务数、预估工时、项目数
    预估工时根据任务优先级估算：urgent=16h, high=8h, medium=4h, low=2h
    支持按 user 筛选单个成员
    """
    permission_classes = [IsAuthenticated]

    # 优先级对应的预估工时
    PRIORITY_HOURS = {
        'urgent': 16,
        'high': 8,
        'medium': 4,
        'low': 2,
    }

    def get(self, request):
        from apps.tasks.models import Task
        from apps.projects.models import ProjectMember

        params = request.query_params
        user_id = params.get('user')

        users = User.objects.all().order_by('-date_joined')
        if user_id:
            users = users.filter(id=user_id)

        result = []
        for user in users:
            # 任务数（指派给该用户 + 协作者，去重）
            assigned_task_ids = set(
                Task.objects.filter(assignee=user).values_list('id', flat=True)
            )
            collaborative_task_ids = set(
                user.collaborating_tasks.values_list('id', flat=True)
            )
            total_task_ids = assigned_task_ids | collaborative_task_ids
            task_count = len(total_task_ids)

            # 未完成任务数
            pending_task_count = Task.objects.filter(
                id__in=total_task_ids
            ).exclude(
                status__in=[Task.Status.DONE, Task.Status.CANCELLED]
            ).count()

            # 预估工时：根据优先级统计
            tasks = Task.objects.filter(id__in=total_task_ids).exclude(
                status__in=[Task.Status.DONE, Task.Status.CANCELLED]
            )
            estimated_hours = 0
            for task in tasks:
                estimated_hours += self.PRIORITY_HOURS.get(task.priority, 4)

            # 项目数
            project_count = ProjectMember.objects.filter(user=user).count()

            result.append({
                'user_id': user.id,
                'user_name': user.name,
                'email': user.email,
                'task_count': task_count,
                'pending_task_count': pending_task_count,
                'estimated_hours': estimated_hours,
                'project_count': project_count,
            })

        return success_response(result, message='成员工作量查询成功')
