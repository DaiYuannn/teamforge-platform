"""
任务业务逻辑服务
"""
from django.db import transaction
from django.utils import timezone

from common.project_access import project_can_manage
from .models import Task, TaskLog


class TaskService:
    """任务业务服务"""

    # 管理角色负责调度、暂停、取消与重开；任何角色都不能跳过待审核直接完成。
    MANAGER_TRANSITIONS = {
        Task.Status.TODO: {
            Task.Status.DOING,
            Task.Status.OVERDUE,
            Task.Status.PAUSED,
            Task.Status.CANCELLED,
            Task.Status.NEED_HELP,
        },
        Task.Status.DOING: {
            Task.Status.PENDING_REVIEW,
            Task.Status.OVERDUE,
            Task.Status.PAUSED,
            Task.Status.CANCELLED,
            Task.Status.NEED_HELP,
        },
        Task.Status.PENDING_REVIEW: {
            Task.Status.DONE,
            Task.Status.DOING,
            Task.Status.OVERDUE,
            Task.Status.PAUSED,
            Task.Status.CANCELLED,
        },
        Task.Status.OVERDUE: {
            Task.Status.DOING,
            Task.Status.PENDING_REVIEW,
            Task.Status.PAUSED,
            Task.Status.CANCELLED,
            Task.Status.NEED_HELP,
        },
        Task.Status.PAUSED: {
            Task.Status.TODO,
            Task.Status.DOING,
            Task.Status.OVERDUE,
            Task.Status.CANCELLED,
        },
        Task.Status.CANCELLED: {
            Task.Status.TODO,
        },
        Task.Status.NEED_HELP: {
            Task.Status.DOING,
            Task.Status.PENDING_REVIEW,
            Task.Status.OVERDUE,
            Task.Status.PAUSED,
            Task.Status.CANCELLED,
        },
        Task.Status.DONE: {
            Task.Status.DOING,
        },
    }

    # 执行人和协作者只负责执行、求助和提交审核，不具备审核、暂停或取消权限。
    PARTICIPANT_TRANSITIONS = {
        Task.Status.TODO: {
            Task.Status.DOING,
            Task.Status.NEED_HELP,
        },
        Task.Status.DOING: {
            Task.Status.PENDING_REVIEW,
            Task.Status.NEED_HELP,
        },
        Task.Status.OVERDUE: {
            Task.Status.DOING,
            Task.Status.PENDING_REVIEW,
            Task.Status.NEED_HELP,
        },
        Task.Status.NEED_HELP: {
            Task.Status.DOING,
            Task.Status.PENDING_REVIEW,
        },
    }

    # 审核人只处理待审核节点：确认完成，或退回继续执行。
    REVIEWER_TRANSITIONS = {
        Task.Status.PENDING_REVIEW: {
            Task.Status.DONE,
            Task.Status.DOING,
        },
    }

    @staticmethod
    def is_manager(task, operator):
        """老师、管理员、牵头负责人或共同负责人是任务管理者。"""
        return project_can_manage(operator, task.project)

    @classmethod
    def can_access_status_action(cls, task, operator):
        """判断用户是否参与该任务的状态流转。"""
        if not operator:
            return False
        if cls.is_manager(task, operator):
            return True
        return bool(
            task.assignee_id == operator.id
            or task.reviewer_id == operator.id
            or task.collaborators.filter(id=operator.id).exists()
        )

    @classmethod
    def allowed_transitions(cls, task, operator):
        """按当前任务关系合并操作者可执行的目标状态。"""
        if cls.is_manager(task, operator):
            return cls.MANAGER_TRANSITIONS.get(task.status, set())

        allowed = set()
        if operator and (
            task.assignee_id == operator.id
            or task.collaborators.filter(id=operator.id).exists()
        ):
            allowed.update(cls.PARTICIPANT_TRANSITIONS.get(task.status, set()))
        if operator and task.reviewer_id == operator.id:
            allowed.update(cls.REVIEWER_TRANSITIONS.get(task.status, set()))
        return allowed

    @classmethod
    def validate_transition(cls, task, to_status, operator, delay_reason=''):
        """校验状态机、操作者职责与延期原因。"""
        from_status = task.status
        valid_statuses = {choice[0] for choice in Task.Status.choices}
        if to_status not in valid_statuses:
            return False, '无效的任务状态'
        if to_status == from_status:
            return False, '目标状态与当前状态相同'

        # 定时任务仅可把超期的开放任务标为逾期，不能代替任何人工流程动作。
        if operator is None:
            if (
                to_status == Task.Status.OVERDUE
                and from_status in {
                    Task.Status.TODO,
                    Task.Status.DOING,
                    Task.Status.PENDING_REVIEW,
                    Task.Status.NEED_HELP,
                }
            ):
                if not str(delay_reason or '').strip():
                    return False, '进入已逾期状态必须填写延期原因'
                return True, ''
            return False, '系统任务无权执行此状态流转'

        if not cls.can_access_status_action(task, operator):
            return False, '无权修改此任务状态'

        if (
            to_status == Task.Status.DONE
            and from_status != Task.Status.PENDING_REVIEW
        ):
            return False, '任务必须先提交待审核，不能直接标记为已完成'

        if to_status == Task.Status.OVERDUE and not str(delay_reason or '').strip():
            return False, '进入已逾期状态必须填写延期原因'

        if to_status not in cls.allowed_transitions(task, operator):
            if to_status == Task.Status.DONE:
                return False, '只有审核人、项目负责人、老师或管理员可以确认任务完成'
            return False, '当前角色不能执行此任务状态流转'

        return True, ''

    @classmethod
    @transaction.atomic
    def change_status(
        cls,
        task,
        to_status,
        operator,
        delay_reason='',
        completion_note=None,
    ):
        """
        修改任务状态
        :param task: 任务实例
        :param to_status: 目标状态
        :param operator: 操作人
        :param delay_reason: 延期原因（转逾期时填写）
        :param completion_note: 本次提交/审核关联的完成说明（不传则保留原值）
        :return: (success, task_or_message)
        """
        # 锁定最新记录，防止并发请求同时越过同一个审核节点。
        task = (
            Task.objects.select_for_update()
            .select_related('project')
            .get(pk=task.pk)
        )
        from_status = task.status
        is_valid, message = cls.validate_transition(
            task=task,
            to_status=to_status,
            operator=operator,
            delay_reason=delay_reason,
        )
        if not is_valid:
            return False, message

        task.status = to_status

        if to_status == Task.Status.DONE:
            task.completed_at = timezone.now()
        elif from_status == Task.Status.DONE:
            task.completed_at = None

        if to_status == Task.Status.OVERDUE:
            task.delay_reason = str(delay_reason).strip()
        if completion_note is not None:
            task.completion_note = str(completion_note).strip()

        task.save(update_fields=[
            'status',
            'completed_at',
            'delay_reason',
            'completion_note',
            'updated_at',
        ])

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
            success, _ = TaskService.change_status(
                task=task,
                to_status=Task.Status.OVERDUE,
                operator=None,
                delay_reason='系统自动标记：任务已超过截止时间',
            )
            if success:
                count += 1
        return count


# 全局服务实例
task_service = TaskService()
