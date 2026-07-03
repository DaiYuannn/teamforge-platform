"""
项目业务逻辑服务
"""
from django.db import transaction
from django.utils import timezone

from .models import Project, ProjectStageLog, ProjectMember
from common.response import error_response, success_response


class ProjectService:
    """项目业务服务"""

    @staticmethod
    @transaction.atomic
    def advance_stage(project, to_stage, operator, note=''):
        """
        推进项目阶段
        :param project: 项目实例
        :param to_stage: 目标阶段
        :param operator: 操作人
        :param note: 备注
        :return: (success: bool, data_or_message)
        """
        from_stage = project.current_stage

        # 校验阶段不能回退（除非是暂停/终止）
        if to_stage < from_stage and to_stage not in (Project.Stage.PAUSED, Project.Stage.TERMINATED):
            return False, '项目阶段不能回退'

        # 如果目标阶段和当前阶段相同
        if to_stage == from_stage:
            return False, '目标阶段与当前阶段相同'

        # 更新项目阶段
        project.current_stage = to_stage

        # 如果推进到终止或已结项，更新实际结束日期
        if to_stage in (Project.Stage.TERMINATED, Project.Stage.CLOSED, Project.Stage.AWARDED):
            if not project.actual_end_date:
                project.actual_end_date = timezone.now().date()
            project.status = Project.Status.CLOSED if to_stage == Project.Stage.CLOSED else project.status

        # 如果推进到暂停
        if to_stage == Project.Stage.PAUSED:
            project.status = Project.Status.PAUSED

        # 如果从暂停恢复
        if from_stage == Project.Stage.PAUSED and to_stage != Project.Stage.PAUSED:
            project.status = Project.Status.ACTIVE

        project.save()

        # 记录阶段日志
        ProjectStageLog.objects.create(
            project=project,
            from_stage=from_stage,
            to_stage=to_stage,
            operator=operator,
            note=note,
        )

        return True, project

    @staticmethod
    @transaction.atomic
    def leader_update(project, operator, note=''):
        """
        项目负责人打卡更新
        更新 last_leader_update 时间戳
        :param project: 项目实例
        :param operator: 操作人（需为项目负责人）
        :param note: 更新备注
        :return: project
        """
        # 校验操作人是否为项目负责人
        if project.leader_id != operator.id and operator.global_role not in ['sys_admin', 'teacher']:
            return False, '只有项目负责人可以打卡更新'

        project.last_leader_update = timezone.now()
        project.save()
        return True, project

    @staticmethod
    @transaction.atomic
    def add_member(project, user, role_in_project='participant'):
        """
        添加项目成员
        :param project: 项目实例
        :param user: 用户实例
        :param role_in_project: 项目角色
        :return: (success, member_or_message)
        """
        # 检查是否已存在
        if ProjectMember.objects.filter(project=project, user=user).exists():
            return False, '该用户已是项目成员'

        member = ProjectMember.objects.create(
            project=project,
            user=user,
            role_in_project=role_in_project,
        )
        return True, member

    @staticmethod
    @transaction.atomic
    def remove_member(project, user):
        """
        移除项目成员
        :param project: 项目实例
        :param user: 用户实例
        :return: (success, message)
        """
        # 项目负责人不能被移除
        if project.leader_id == user.id:
            return False, '不能移除项目负责人'

        deleted, _ = ProjectMember.objects.filter(project=project, user=user).delete()
        if deleted == 0:
            return False, '该用户不是项目成员'
        return True, '成员已移除'


# 全局服务实例
project_service = ProjectService()
