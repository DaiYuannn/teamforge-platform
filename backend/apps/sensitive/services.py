"""
敏感资料业务逻辑服务
包含：脱敏显示、加密存储、解密、创建查看申请、审批、限时查看明文（写日志）、过期检查
关键：敏感资料明文绝不裸露，审批通过后限时查看，每次查看必须写 OperationLog
"""
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import SensitiveData, SensitiveAccessRequest
from apps.audit.models import OperationLog


class SensitiveDataService:
    """敏感资料服务"""

    @staticmethod
    def mask_value(data_type, value):
        """
        脱敏显示
        :param data_type: 数据类型
        :param value: 明文值
        :return: 脱敏后的字符串
        """
        if not value:
            return '***'
        value = str(value)

        if data_type == 'id_card':
            # 110***********1234
            if len(value) >= 18:
                return value[:3] + '*' * (len(value) - 7) + value[-4:]
            return value[:1] + '*' * (len(value) - 1) if len(value) > 1 else '***'
        elif data_type == 'phone':
            # 138****5678
            if len(value) >= 11:
                return value[:3] + '****' + value[-4:]
            return value[:2] + '****' if len(value) > 2 else '***'
        elif data_type == 'bank_account':
            # 末四位可见
            if len(value) > 8:
                return '*' * (len(value) - 4) + value[-4:]
            return '****'
        elif data_type == 'address':
            # 只显示前10个字符
            return value[:10] + '***' if len(value) > 10 else '***'
        elif data_type == 'signature':
            return '***签名***'
        return '***'

    @staticmethod
    def encrypt_value(value):
        """加密存储"""
        from common.encryption import get_field_cipher
        cipher = get_field_cipher()
        return cipher.encrypt(value)

    @staticmethod
    def decrypt_value(encrypted_value):
        """解密（仅审批通过后调用）"""
        from common.encryption import get_field_cipher
        cipher = get_field_cipher()
        return cipher.decrypt(encrypted_value)

    @staticmethod
    def create_sensitive_data(data_type, title, plaintext, **kwargs):
        """
        创建敏感资料（加密存储）
        :param data_type: 数据类型
        :param title: 数据标题
        :param plaintext: 明文内容
        :param kwargs: display_name, project, uploader, file_attachment 等
        :return: SensitiveData 实例
        """
        from common.encryption import get_field_cipher
        cipher = get_field_cipher()
        encrypted = cipher.encrypt(plaintext) if plaintext else ''
        sensitive = SensitiveData.objects.create(
            data_type=data_type,
            title=title,
            display_name=kwargs.get('display_name', title),
            encrypted_content=encrypted,
            is_encrypted=bool(plaintext),
            key_version=1,
            file_attachment=kwargs.get('file_attachment'),
            project=kwargs.get('project'),
            uploader=kwargs.get('uploader'),
        )
        return sensitive

    @staticmethod
    @transaction.atomic
    def create_access_request(requester, target, reason, usage_scenario='',
                              project=None, expected_use_time=None,
                              is_download=False, request_note=''):
        """
        创建查看申请
        :param requester: 申请人
        :param target: SensitiveData 实例
        :param reason: 申请理由
        :param usage_scenario: 使用场景
        :param project: 所属项目
        :param expected_use_time: 预计使用时间
        :param is_download: 是否需要下载
        :param request_note: 申请说明
        :return: SensitiveAccessRequest 实例
        """
        request_obj = SensitiveAccessRequest.objects.create(
            sensitive_data=target,
            applicant=requester,
            reason=reason,
            usage_scenario=usage_scenario,
            project=project,
            expected_use_time=expected_use_time,
            is_download=is_download,
            request_note=request_note,
            status=SensitiveAccessRequest.Status.PENDING,
        )

        # 写操作日志
        OperationLog.objects.create(
            operator=requester,
            operation_type=OperationLog.OperationType.OTHER,
            module='sensitive',
            object_type='SensitiveAccessRequest',
            object_id=str(request_obj.id),
            description=f'申请查看敏感资料: {target.title}',
        )
        return request_obj

    @staticmethod
    @transaction.atomic
    def approve_request(request_id, approver, expire_hours=1, approval_opinion=''):
        """
        审批通过，设置过期时间（默认1小时）
        :param request_id: 申请ID
        :param approver: 审批人
        :param expire_hours: 有效期小时数
        :param approval_opinion: 审批意见
        :return: (success, data_or_message)
        """
        try:
            request_obj = SensitiveAccessRequest.objects.get(id=request_id)
        except SensitiveAccessRequest.DoesNotExist:
            return False, '访问申请不存在'

        if request_obj.status != SensitiveAccessRequest.Status.PENDING:
            return False, '该申请已处理，不可重复审批'

        request_obj.status = SensitiveAccessRequest.Status.APPROVED
        request_obj.approver = approver
        request_obj.approval_opinion = approval_opinion
        request_obj.approval_comment = approval_opinion
        request_obj.approved_at = timezone.now()
        request_obj.access_expires_at = timezone.now() + timedelta(hours=expire_hours)
        request_obj.save()

        # 写操作日志
        OperationLog.objects.create(
            operator=approver,
            operation_type=OperationLog.OperationType.APPROVE,
            module='sensitive',
            object_type='SensitiveAccessRequest',
            object_id=str(request_obj.id),
            description=f'审批通过敏感资料查看申请，有效期{expire_hours}小时: '
                        f'{request_obj.sensitive_data.title}',
        )
        return True, request_obj

    @staticmethod
    @transaction.atomic
    def reject_request(request_id, approver, approval_opinion=''):
        """
        驳回申请
        :param request_id: 申请ID
        :param approver: 审批人
        :param approval_opinion: 审批意见
        :return: (success, data_or_message)
        """
        try:
            request_obj = SensitiveAccessRequest.objects.get(id=request_id)
        except SensitiveAccessRequest.DoesNotExist:
            return False, '访问申请不存在'

        if request_obj.status != SensitiveAccessRequest.Status.PENDING:
            return False, '该申请已处理，不可重复审批'

        request_obj.status = SensitiveAccessRequest.Status.REJECTED
        request_obj.approver = approver
        request_obj.approval_opinion = approval_opinion
        request_obj.approval_comment = approval_opinion
        request_obj.approved_at = timezone.now()
        request_obj.save()

        # 写操作日志
        OperationLog.objects.create(
            operator=approver,
            operation_type=OperationLog.OperationType.APPROVE,
            module='sensitive',
            object_type='SensitiveAccessRequest',
            object_id=str(request_obj.id),
            description=f'驳回敏感资料查看申请: {request_obj.sensitive_data.title}',
        )
        return True, request_obj

    @staticmethod
    @transaction.atomic
    def view_sensitive_data(request_id, viewer, request=None):
        """
        查看敏感资料明文（检查权限是否有效，写 OperationLog，限时）
        - 检查 status=approved 且未过期
        - 解密返回明文
        - 写 OperationLog
        - 更新 viewed_at
        :param request_id: 申请ID
        :param viewer: 查看人
        :param request: HTTP 请求对象（用于记录 IP 等）
        :return: (success, data_or_message) data 为 {'plaintext': ..., 'sensitive_data': ...}
        """
        try:
            request_obj = SensitiveAccessRequest.objects.select_related(
                'sensitive_data'
            ).get(id=request_id)
        except SensitiveAccessRequest.DoesNotExist:
            return False, '访问申请不存在'

        # 校验查看人必须是申请人本人
        if request_obj.applicant_id != viewer.id:
            return False, '仅申请人本人可查看敏感资料明文'

        # 检查 status=approved 且未过期
        if request_obj.status != SensitiveAccessRequest.Status.APPROVED:
            return False, '申请未通过审批，无法查看明文'

        now = timezone.now()
        if request_obj.access_expires_at and now > request_obj.access_expires_at:
            # 已过期，自动关闭
            request_obj.status = SensitiveAccessRequest.Status.EXPIRED
            request_obj.save()
            return False, '查看权限已过期，请重新申请'

        # 解密返回明文
        sensitive = request_obj.sensitive_data
        try:
            plaintext = SensitiveDataService.decrypt_value(sensitive.encrypted_content)
        except Exception as e:
            return False, f'解密失败: {e}'

        # 更新首次查看时间
        if not request_obj.viewed_at:
            request_obj.viewed_at = now
            request_obj.save()

        # 写操作日志（每次查看必写）
        OperationLog.objects.create(
            operator=viewer,
            operation_type=OperationLog.OperationType.OTHER,
            module='sensitive',
            object_type='SensitiveData',
            object_id=str(sensitive.id),
            description=f'查看敏感资料明文: {sensitive.title}（申请#{request_obj.id}）',
            request_method=getattr(request, 'method', '') if request else '',
            request_path=getattr(request, 'path', '') if request else '',
            request_ip=_get_client_ip(request) if request else None,
        )

        return True, {
            'plaintext': plaintext,
            'sensitive_data': sensitive,
            'request': request_obj,
        }

    @staticmethod
    def check_expired():
        """
        检查过期申请，自动关闭
        将已通过但超过 access_expires_at 的申请标记为 expired
        :return: 关闭的申请数量
        """
        now = timezone.now()
        expired = SensitiveAccessRequest.objects.filter(
            status=SensitiveAccessRequest.Status.APPROVED,
            access_expires_at__lt=now,
        )
        count = expired.count()
        expired.update(status=SensitiveAccessRequest.Status.EXPIRED)
        return count


def _get_client_ip(request):
    """从请求中获取客户端IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
