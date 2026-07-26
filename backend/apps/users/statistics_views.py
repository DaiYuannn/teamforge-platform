"""
成员统计分析视图
- MemberStatisticsView: 返回每个成员的统计信息
  - 任务完成率
  - 项目参与数
  - 贡献得分
  - 出勤率
"""
from decimal import Decimal

from django.db.models import Sum, Q
from rest_framework.views import APIView

from common.permissions import IsInternalTeamMember
from common.response import success_response
from common.mixins import MultiSerializerMixin
from .models import User


class MemberStatisticsView(APIView):
    """
    成员统计视图
    GET /api/v1/users/statistics/
    返回每个成员的综合统计：任务完成率、项目参与数、贡献得分、出勤率
    支持按 user 筛选单个成员
    """
    permission_classes = [IsInternalTeamMember]

    def get(self, request):
        from apps.tasks.models import Task
        from apps.projects.models import ProjectMember
        from apps.contributions.models import Contribution

        params = request.query_params
        user_id = params.get('user')

        users = User.objects.all().order_by('-date_joined')
        if user_id:
            users = users.filter(id=user_id)

        result = []
        for user in users:
            # 任务统计（作为指派人 + 协作者）
            assigned_tasks = Task.objects.filter(assignee=user)
            collaborative_task_ids = user.collaborating_tasks.values_list('id', flat=True)
            total_task_ids = set(assigned_tasks.values_list('id', flat=True)) | set(
                collaborative_task_ids
            )
            total_tasks = len(total_task_ids)
            completed_tasks = Task.objects.filter(
                id__in=total_task_ids, status=Task.Status.DONE
            ).count()

            # 任务完成率
            if total_tasks > 0:
                task_completion_rate = round(completed_tasks / total_tasks * 100, 2)
            else:
                task_completion_rate = 0.0

            # 项目参与数
            project_count = ProjectMember.objects.filter(user=user).count()

            # 贡献得分（已通过贡献的权重之和）
            contrib_sum = Contribution.objects.filter(
                user=user, status=Contribution.Status.APPROVED
            ).aggregate(total=Sum('weight'))
            contribution_score = float(contrib_sum['total'] or 0)

            # 出勤率：基于任务参与情况（已完成 + 进行中）/ 总任务
            engaged_tasks = Task.objects.filter(
                id__in=total_task_ids,
                status__in=[Task.Status.DONE, Task.Status.DOING, Task.Status.PENDING_REVIEW],
            ).count()
            if total_tasks > 0:
                attendance_rate = round(engaged_tasks / total_tasks * 100, 2)
            else:
                attendance_rate = 0.0

            result.append({
                'user_id': user.id,
                'user_name': user.name,
                'email': user.email,
                'global_role': user.global_role,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'task_completion_rate': task_completion_rate,
                'project_participation_count': project_count,
                'contribution_score': contribution_score,
                'attendance_rate': attendance_rate,
            })

        return success_response(result, message='成员统计查询成功')
