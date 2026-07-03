"""
任务业务逻辑服务
"""
from django.db import transaction
from django.utils import timezone

from .models import Task, TaskLog
from common.response import error_response


class TaskService:
    """任务业务服务"""

    @staticmethod
    @transaction.atomic
    def change_status(task, to_status, operator, delay_reason=''):
        """
        修改任务状态
        :param task: 任务实例
        :param to_status: 目标状态
        :param operator: 操作人
        :param delay_reason: 延期原因（转逾期时填写）
        :return: (success, task_or_message)
        """
        from_status = task.status

        # 状态相同无需变更
        if to_status == from_status:
            return False, '目标状态与当前状态相同'

        # 更新任务状态
        task.status = to_status

        # 如果变为已完成，记录完成时间
        if to_status == Task.Status.DONE:
            task.completed_at = timezone.now()

        # 如果变为已逾期，记录延期原因
        if to_status == Task.Status.OVERDUE and delay_reason:
            task.delay_reason = delay_reason

        task.save()

        # 记录状态变更日志
        TaskLog.objects.create(
            task=task,
            from_status=from_status,
            to_status=to_status,
            operator=operator,
        )

        return True, task

    @staticmethod
    def check_overdue_tasks():
        """
        批量检查逾期任务
        将已过截止时间且未完成的任务标记为已逾期
        :return: 标记的逾期任务数量
        """
        now = timezone.now()
        # 查找已过截止时间且状态为待办/进行中/待审核/需要帮助的任务
        overdue_tasks = Task.objects.filter(
            deadline__lt=now,
            status__in=[
                Task.Status.TODO,
                Task.Status.DOING,
                Task.Status.PENDING_REVIEW,
                Task.Status.NEED_HELP,
            ],
        )
        count = 0
        for task in overdue_tasks:
            TaskService.change_status(
                task=task,
                to_status=Task.Status.OVERDUE,
                operator=None,
            )
            task.overdue_reminded = True
            task.save()
            count += 1
        return count


# 全局服务实例
task_service = TaskService()
