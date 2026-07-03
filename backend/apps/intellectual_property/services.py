"""
知识产权管理业务逻辑服务
包含：状态流转、退回记录创建/完成、贡献同步、成果归档、操作日志记录
"""
from django.db import transaction
from django.utils import timezone

from .models import (
    IntellectualPropertyApplication,
    IPApplicationContributor,
    IPReturnRecord,
    IPMaterialVersion,
    IPObjection,
)
from apps.audit.models import OperationLog
from apps.contributions.models import Contribution


# ============ 状态流转合法路径定义 ============
VALID_TRANSITIONS = {
    'draft': ['writing', 'paused', 'terminated'],
    'writing': ['leader_review', 'paused', 'terminated'],
    'leader_review': ['teacher_confirm', 'writing', 'paused'],
    'teacher_confirm': ['research_office_review', 'leader_review', 'paused'],
    'research_office_review': ['accepted', 'returned', 'paused'],
    'returned': ['modifying', 'paused', 'terminated'],
    'modifying': ['resubmitted', 'paused', 'terminated'],
    'resubmitted': ['research_office_review', 'accepted', 'returned', 'paused'],
    'accepted': ['authorized', 'paused'],
    'authorized': ['archived'],
    'archived': [],
    'paused': ['draft', 'writing', 'leader_review', 'teacher_confirm',
               'research_office_review', 'modifying'],
    'terminated': [],
    'deferred': ['draft'],
}

# 贡献角色到贡献类型的映射
ROLE_TO_CONTRIBUTION_TYPE = {
    IPApplicationContributor.ContributorRole.MAIN_WRITER: Contribution.ContributionType.IP_WRITING,
    IPApplicationContributor.ContributorRole.CO_WRITER: Contribution.ContributionType.IP_WRITING,
    IPApplicationContributor.ContributorRole.CODE_PROVIDER: Contribution.ContributionType.IP_WRITING,
    IPApplicationContributor.ContributorRole.DOCUMENT_WRITER: Contribution.ContributionType.IP_WRITING,
    IPApplicationContributor.ContributorRole.DRAWING_PROVIDER: Contribution.ContributionType.IP_WRITING,
    IPApplicationContributor.ContributorRole.TESTER: Contribution.ContributionType.IP_WRITING,
    IPApplicationContributor.ContributorRole.EXECUTOR: Contribution.ContributionType.IP_EXECUTION,
    IPApplicationContributor.ContributorRole.MATERIAL_MANAGER: Contribution.ContributionType.IP_MATERIAL,
    IPApplicationContributor.ContributorRole.REVIEWER: Contribution.ContributionType.IP_WRITING,
}


def log_operation(user, action, obj, detail=''):
    """
    写入操作日志辅助方法
    :param user: 操作人
    :param action: 操作动作描述
    :param obj: 操作对象
    :param detail: 操作详情
    """
    object_type = obj.__class__.__name__ if obj else ''
    object_id = str(obj.id) if obj and hasattr(obj, 'id') else ''
    OperationLog.objects.create(
        operator=user,
        operation_type=OperationLog.OperationType.OTHER,
        module='intellectual_property',
        object_type=object_type,
        object_id=object_id,
        description=f'{action}: {detail}',
    )


class IPService:
    """知识产权业务服务"""

    @staticmethod
    @transaction.atomic
    def transition_status(application, target_status, user):
        """
        状态流转（校验合法转换路径）
        :param application: 知识产权申请实例
        :param target_status: 目标状态
        :param user: 操作人
        :return: (success: bool, data_or_message)
        """
        current_status = application.status

        # 目标状态与当前状态相同
        if target_status == current_status:
            return False, '目标状态与当前状态相同'

        # 校验目标状态值有效性
        valid_status_values = [choice[0] for choice in IntellectualPropertyApplication.Status.choices]
        if target_status not in valid_status_values:
            return False, f'无效的状态值: {target_status}'

        # 校验状态转换路径合法性
        allowed_targets = VALID_TRANSITIONS.get(current_status, [])
        if target_status not in allowed_targets:
            current_display = application.get_status_display()
            return False, f'不允许从"{current_display}"转换到目标状态'

        from_status = application.status
        # 更新申请状态
        application.status = target_status

        # 根据目标状态更新相关日期字段
        now_date = timezone.now().date()
        if target_status == IntellectualPropertyApplication.Status.ACCEPTED:
            application.accepted_date = now_date
        elif target_status == IntellectualPropertyApplication.Status.AUTHORIZED:
            application.authorized_date = now_date
        elif target_status in (
            IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
            IntellectualPropertyApplication.Status.LEADER_REVIEW,
        ):
            # 提交审核视为提交日期
            if not application.submit_date:
                application.submit_date = now_date

        application.save()

        # 写操作日志
        log_operation(
            user=user,
            action='状态流转',
            obj=application,
            detail=f'{application.title}: {from_status} -> {target_status}',
        )

        return True, application

    @staticmethod
    @transaction.atomic
    def create_return_record(application, data, user):
        """
        创建退回记录
        - 创建 IPReturnRecord
        - 增加 application.return_count
        - 更新申请状态为 returned（科研处退回）
        - 写 OperationLog
        :param application: 知识产权申请实例
        :param data: 退回记录数据（return_time, return_source, return_reason,
                      responsibility_type, responsible_user, modify_deadline, proof_file）
        :param user: 操作人（指派人）
        :return: (success: bool, data_or_message)
        """
        # 创建退回记录
        return_record = IPReturnRecord.objects.create(
            application=application,
            return_time=data.get('return_time', timezone.now()),
            return_source=data.get('return_source', IPReturnRecord.ReturnSource.RESEARCH_OFFICE),
            return_reason=data.get('return_reason', ''),
            responsibility_type=data.get(
                'responsibility_type', IPReturnRecord.ResponsibilityType.OTHER
            ),
            responsible_user=data.get('responsible_user'),
            assigned_by=user,
            modify_deadline=data.get('modify_deadline'),
            proof_file=data.get('proof_file'),
        )

        # 增加退回次数
        application.return_count = (application.return_count or 0) + 1
        # 更新申请状态为退回修改
        application.status = IntellectualPropertyApplication.Status.RETURNED
        application.save()

        # 写操作日志
        log_operation(
            user=user,
            action='创建退回记录',
            obj=application,
            detail=f'{application.title} 第{application.return_count}次退回，'
                   f'责任类型: {return_record.get_responsibility_type_display()}',
        )

        return True, return_record

    @staticmethod
    @transaction.atomic
    def resolve_return_record(return_record, data, user):
        """
        完成退回修改
        - 更新退回记录的修改说明、实际修改人、处理结果
        - 更新申请状态为 resubmitted（已重新提交）
        - 写 OperationLog
        :param return_record: 退回记录实例
        :param data: 修改数据（modify_description, result）
        :param user: 操作人（实际修改人）
        :return: (success: bool, data_or_message)
        """
        application = return_record.application

        # 更新退回记录
        return_record.modify_description = data.get('modify_description', '')
        return_record.actual_modifier = user
        return_record.result = data.get('result', IPReturnRecord.ReturnResult.MODIFIED)
        return_record.save()

        # 更新申请状态为已重新提交
        old_status = application.status
        application.status = IntellectualPropertyApplication.Status.RESUBMITTED
        application.save()

        # 写操作日志
        log_operation(
            user=user,
            action='完成退回修改',
            obj=application,
            detail=f'{application.title} 退回记录#{return_record.id}已修改完成，'
                   f'申请状态: {old_status} -> resubmitted',
        )

        # 为实际修改人记录退回修改贡献
        Contribution.objects.create(
            user=user,
            project=application.related_project,
            contribution_type=Contribution.ContributionType.IP_RETURN_FIX,
            description=f'知识产权申请"{application.title}"退回修改完成',
            related_object_id=application.id,
        )

        return True, return_record

    @staticmethod
    @transaction.atomic
    def sync_contribution(application, user):
        """
        同步贡献记录到 Contribution 表
        - 根据申请的责任分工记录，为每个成员创建对应的贡献记录
        - 写 OperationLog
        :param application: 知识产权申请实例
        :param user: 操作人
        :return: (success: bool, data_or_message) data 为创建的贡献记录数量
        """
        contributors = application.contributors.all()
        if not contributors.exists():
            return False, '该申请暂无责任分工记录，无法同步贡献'

        created_count = 0
        for contributor in contributors:
            contribution_type = ROLE_TO_CONTRIBUTION_TYPE.get(
                contributor.role, Contribution.ContributionType.OTHER
            )
            # 避免重复创建：同一申请同一用户同一贡献类型只创建一次
            _, created = Contribution.objects.get_or_create(
                user=contributor.user,
                project=application.related_project,
                contribution_type=contribution_type,
                related_object_id=application.id,
                defaults={
                    'description': f'知识产权申请"{application.title}" - '
                                   f'{contributor.get_role_display()}',
                },
            )
            if created:
                created_count += 1

        # 写操作日志
        log_operation(
            user=user,
            action='同步贡献记录',
            obj=application,
            detail=f'{application.title} 同步{created_count}条贡献记录',
        )

        return True, created_count

    @staticmethod
    @transaction.atomic
    def archive_application(application, user):
        """
        成果归档
        - 更新申请状态为 archived
        - 将所有材料标记为非最终版（保留当前最终版）
        - 写 OperationLog
        :param application: 知识产权申请实例
        :param user: 操作人
        :return: (success: bool, data_or_message)
        """
        # 校验当前状态必须为已授权/已登记
        if application.status != IntellectualPropertyApplication.Status.AUTHORIZED:
            return False, '仅"已授权/已登记"状态的申请可以归档'

        old_status = application.status
        application.status = IntellectualPropertyApplication.Status.ARCHIVED
        application.save()

        # 为创建人记录归档贡献
        if application.related_project:
            Contribution.objects.create(
                user=user,
                project=application.related_project,
                contribution_type=Contribution.ContributionType.IP_ARCHIVE,
                description=f'知识产权申请"{application.title}"成果归档',
                related_object_id=application.id,
            )

        # 写操作日志
        log_operation(
            user=user,
            action='成果归档',
            obj=application,
            detail=f'{application.title} 归档完成，状态: {old_status} -> archived',
        )

        return True, application


# 全局服务实例
ip_service = IPService()
