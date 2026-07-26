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
    'draft': ['writing', 'paused', 'terminated', 'deferred'],
    'writing': ['leader_review', 'paused', 'terminated', 'deferred'],
    'leader_review': ['teacher_confirm', 'writing', 'paused', 'deferred'],
    'teacher_confirm': ['research_office_review', 'leader_review', 'paused', 'deferred'],
    'research_office_review': ['accepted', 'paused', 'deferred'],
    'returned': ['modifying', 'paused', 'terminated', 'deferred'],
    'modifying': ['paused', 'terminated', 'deferred'],
    'resubmitted': ['research_office_review', 'accepted', 'paused', 'deferred'],
    'accepted': ['authorized', 'paused'],
    'authorized': [],
    'archived': [],
    'paused': ['draft', 'writing', 'leader_review', 'teacher_confirm',
               'research_office_review', 'modifying', 'deferred'],
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


def _stored_file_exists(file_asset):
    """Return whether a FileAsset points to a readable object in its storage."""
    if not file_asset or not file_asset.file or not file_asset.file.name:
        return False
    try:
        return file_asset.file.storage.exists(file_asset.file.name)
    except (OSError, ValueError):
        return False


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
        application = (
            IntellectualPropertyApplication.objects.select_for_update()
            .get(pk=application.pk)
        )
        current_status = application.status

        # 目标状态与当前状态相同
        if target_status == current_status:
            return False, '目标状态与当前状态相同'

        # 校验目标状态值有效性
        valid_status_values = [choice[0] for choice in IntellectualPropertyApplication.Status.choices]
        if target_status not in valid_status_values:
            return False, f'无效的状态值: {target_status}'

        specialized_targets = {
            IntellectualPropertyApplication.Status.RETURNED:
                '退回状态必须通过“新建退回记录”进入，以保留原因、责任人与修改期限',
            IntellectualPropertyApplication.Status.RESUBMITTED:
                '重新提交必须通过“完成退回修改”进入，以结清退回记录并同步贡献',
            IntellectualPropertyApplication.Status.ARCHIVED:
                '归档状态必须通过“成果归档”操作进入，以同步归档贡献和审计记录',
        }
        if target_status in specialized_targets:
            return False, specialized_targets[target_status]

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

        # 正式授权/登记时自动落贡献；后续手工同步仍保持幂等。
        if target_status == IntellectualPropertyApplication.Status.AUTHORIZED:
            IPService.sync_contribution(application, user)

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
        application = (
            IntellectualPropertyApplication.objects.select_for_update()
            .get(pk=application.pk)
        )
        if application.status not in {
            IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
            IntellectualPropertyApplication.Status.RESUBMITTED,
        }:
            return False, '仅科研处审核中或已重新提交的申请可登记退回'
        if IPReturnRecord.objects.filter(
            application=application,
            result=IPReturnRecord.ReturnResult.PENDING,
        ).exists():
            return False, '该申请已有待处理的退回记录，不能重复登记'

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
        return_record = (
            IPReturnRecord.objects.select_for_update()
            .select_related('application')
            .get(pk=return_record.pk)
        )
        application = (
            IntellectualPropertyApplication.objects.select_for_update()
            .get(pk=return_record.application_id)
        )

        if return_record.result != IPReturnRecord.ReturnResult.PENDING:
            return False, '该退回记录已完成处理，不能重复提交'
        if application.status not in {
            IntellectualPropertyApplication.Status.RETURNED,
            IntellectualPropertyApplication.Status.MODIFYING,
        }:
            return False, '申请仅在退回修改或修改中状态可完成本次退回'

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
            period=timezone.localdate().strftime('%Y-%m'),
        )

        return True, return_record

    @staticmethod
    @transaction.atomic
    def sync_contribution(application, user):
        """
        同步贡献记录到 Contribution 表
        - 根据责任分工记录和申请责任链字段，为每个成员创建对应贡献
        - 同一申请、成员、贡献类型幂等
        - 写 OperationLog
        :param application: 知识产权申请实例
        :param user: 操作人
        :return: (success: bool, data_or_message) data 为创建的贡献记录数量
        """
        assignments = [
            (contributor.user, contributor.role, contributor.get_role_display())
            for contributor in application.contributors.select_related('user').all()
        ]
        direct_assignments = (
            (
                application.main_writer,
                IPApplicationContributor.ContributorRole.MAIN_WRITER,
                '主导撰写人',
            ),
            (
                application.applicant_executor,
                IPApplicationContributor.ContributorRole.EXECUTOR,
                '申请执行人',
            ),
            (
                application.material_manager,
                IPApplicationContributor.ContributorRole.MATERIAL_MANAGER,
                '材料整理人',
            ),
            (
                application.project_reviewer,
                IPApplicationContributor.ContributorRole.REVIEWER,
                '项目负责人审核人',
            ),
        )
        assignments.extend(
            assignment for assignment in direct_assignments if assignment[0] is not None
        )
        if not assignments:
            return False, '该申请暂无责任分工记录，无法同步贡献'

        created_count = 0
        seen = set()
        for contributor_user, contributor_role, role_label in assignments:
            contribution_type = ROLE_TO_CONTRIBUTION_TYPE.get(
                contributor_role, Contribution.ContributionType.OTHER
            )
            assignment_key = (contributor_user.id, contribution_type)
            if assignment_key in seen:
                continue
            seen.add(assignment_key)
            # 避免重复创建：同一申请同一用户同一贡献类型只创建一次
            _, created = Contribution.objects.get_or_create(
                user=contributor_user,
                project=application.related_project,
                contribution_type=contribution_type,
                related_object_id=application.id,
                defaults={
                    'description': f'知识产权申请"{application.title}" - '
                                   f'{role_label}',
                    'content': f'知识产权申请"{application.title}" - {role_label}',
                    'filled_by': user,
                    'period': timezone.localdate().strftime('%Y-%m'),
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
        - 校验已授权/登记状态、最终证书和最终材料
        - 幂等补齐职责贡献
        - 更新申请状态为 archived
        - 写 OperationLog
        :param application: 知识产权申请实例
        :param user: 操作人
        :return: (success: bool, data_or_message)
        """
        application = (
            IntellectualPropertyApplication.objects.select_for_update()
            .get(pk=application.pk)
        )
        # 归档只接收正式授权/登记后的成果，且必须形成可核验的材料闭环。
        if application.status != IntellectualPropertyApplication.Status.AUTHORIZED:
            return False, '仅“已授权/已登记”状态的申请可以归档'

        certificate = application.final_certificate_file
        if certificate is None:
            return False, '归档前请先上传最终授权/登记证书'
        if not _stored_file_exists(certificate):
            return False, '最终证书文件不存在或无法读取，请重新上传后再归档'

        final_materials = list(
            IPMaterialVersion.objects.select_for_update()
            .select_related('file_asset')
            .filter(application=application, is_final=True)
        )
        if not final_materials:
            return False, '归档前请至少将一个成果材料版本标记为最终版'
        if not any(_stored_file_exists(material.file_asset) for material in final_materials):
            return False, '最终材料文件不存在或无法读取，请重新上传后再归档'

        # 兼容历史上直接置为授权状态的数据，归档时再次幂等补齐职责贡献。
        IPService.sync_contribution(application, user)

        old_status = application.status
        application.status = IntellectualPropertyApplication.Status.ARCHIVED
        application.save()

        # 为创建人记录归档贡献
        if application.related_project:
            Contribution.objects.get_or_create(
                user=user,
                project=application.related_project,
                contribution_type=Contribution.ContributionType.IP_ARCHIVE,
                related_object_id=application.id,
                defaults={
                    'description': f'知识产权申请"{application.title}"成果归档',
                    'content': f'知识产权申请"{application.title}"成果归档',
                    'filled_by': user,
                    'period': timezone.localdate().strftime('%Y-%m'),
                },
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
