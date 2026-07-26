"""
项目业务逻辑服务
"""
from django.db import transaction
from django.utils import timezone

from .models import Project, ProjectStageLog, ProjectMember, ProjectMembershipEvent
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
    def add_member(project, user, role_in_project='participant', operator=None):
        """
        添加项目成员
        :param project: 项目实例
        :param user: 用户实例
        :param role_in_project: 项目角色
        :return: (success, member_or_message)
        """
        # 检查是否已存在
        existing = ProjectMember.objects.filter(project=project, user=user).first()
        if existing:
            if existing.status == ProjectMember.Status.EXITED:
                old_status = existing.status
                existing.status = ProjectMember.Status.ACTIVE
                existing.role_in_project = role_in_project
                existing.exited_at = None
                existing.exit_reason = ''
                existing.handover_to = None
                existing.handover_notes = ''
                existing.save()
                ProjectMembershipEvent.objects.create(
                    membership=existing,
                    event_type=ProjectMembershipEvent.EventType.REACTIVATED,
                    from_status=old_status,
                    to_status=existing.status,
                    to_role=role_in_project,
                    operator=operator,
                )
                return True, existing
            return False, '该用户已是项目成员'

        member = ProjectMember.objects.create(
            project=project,
            user=user,
            role_in_project=role_in_project,
        )
        ProjectMembershipEvent.objects.create(
            membership=member,
            event_type=ProjectMembershipEvent.EventType.JOINED,
            to_role=role_in_project,
            to_status=member.status,
            operator=operator,
        )
        return True, member

    @staticmethod
    @transaction.atomic
    def remove_member(project, user, operator=None, reason='', handover_to=None, handover_notes=''):
        """
        移除项目成员
        :param project: 项目实例
        :param user: 用户实例
        :return: (success, message)
        """
        # 项目负责人不能被移除
        if project.leader_id == user.id:
            return False, '不能移除项目负责人'

        member = ProjectMember.objects.filter(project=project, user=user).first()
        if not member:
            return False, '该用户不是项目成员'
        if member.status == ProjectMember.Status.EXITED:
            return False, '该成员已经退出项目'
        if handover_to and handover_to.project_id != project.id:
            return False, '交接人必须属于同一项目'

        old_status = member.status
        member.status = ProjectMember.Status.EXITED
        member.exited_at = timezone.now()
        member.exit_reason = reason
        member.handover_to = handover_to
        member.handover_notes = handover_notes
        member.save()
        ProjectMembershipEvent.objects.create(
            membership=member,
            event_type=ProjectMembershipEvent.EventType.EXITED,
            from_role=member.role_in_project,
            to_role=member.role_in_project,
            from_status=old_status,
            to_status=member.status,
            reason=reason,
            handover_to=handover_to,
            handover_notes=handover_notes,
            operator=operator,
        )
        return True, '成员已退出项目，历史记录已保留'

    @staticmethod
    @transaction.atomic
    def update_member(member, operator=None, role_in_project=None, status=None,
                      reason='', handover_to=None, handover_notes=''):
        old_role = member.role_in_project
        old_status = member.status
        if role_in_project:
            member.role_in_project = role_in_project
        if status:
            member.status = status
            if status == ProjectMember.Status.EXITED:
                member.exited_at = timezone.now()
            elif status == ProjectMember.Status.ACTIVE:
                member.exited_at = None
                member.exit_reason = ''
        if reason:
            member.exit_reason = reason
        if handover_to is not None:
            member.handover_to = handover_to
        if handover_notes:
            member.handover_notes = handover_notes
        member.save()

        event_type = (
            ProjectMembershipEvent.EventType.ROLE_CHANGED
            if old_role != member.role_in_project and old_status == member.status
            else ProjectMembershipEvent.EventType.STATUS_CHANGED
        )
        if member.status == ProjectMember.Status.EXITED:
            event_type = ProjectMembershipEvent.EventType.EXITED
        elif old_status == ProjectMember.Status.EXITED and member.status == ProjectMember.Status.ACTIVE:
            event_type = ProjectMembershipEvent.EventType.REACTIVATED
        ProjectMembershipEvent.objects.create(
            membership=member,
            event_type=event_type,
            from_role=old_role,
            to_role=member.role_in_project,
            from_status=old_status,
            to_status=member.status,
            reason=reason,
            handover_to=handover_to,
            handover_notes=handover_notes,
            operator=operator,
        )
        return True, member


# 全局服务实例
project_service = ProjectService()
