"""
敏感资料视图
- SensitiveDataViewSet: 敏感资料 CRUD + 我的资料 + 查看明文（需有效审批）
- SensitiveAccessRequestViewSet: 访问申请 CRUD + 审批/驳回 + 我的申请 + 待审批 + 限时查看明文
关键：敏感资料明文绝不裸露，必须审批后限时查看，每次查看必须写 OperationLog
"""
from django.http import Http404
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.storage import protected_media_response
from apps.files.audit import record_download_audit
from .models import (
    SensitiveAccessRequest,
    SensitiveData,
    SensitiveDataGrant,
    SensitiveGrantAccessLog,
)
from .serializers import (
    SensitiveDataSerializer,
    SensitiveDataCreateSerializer,
    SensitiveAccessRequestSerializer,
    SensitiveAccessRequestCreateSerializer,
    SensitiveAccessRequestReviewSerializer,
    SensitiveDataGrantSerializer,
    SensitiveGrantAccessLogSerializer,
)
from .permissions import (
    IsSensitiveDataOwner,
    IsSensitiveApproverOrAdmin,
    IsSensitiveDataCreator,
    HasValidAccessApproval,
    IsInternalSensitiveMember,
    can_review_sensitive_request,
    can_manage_sensitive_grants,
    scope_sensitive_data_queryset,
    sensitive_review_team_ids,
)
from .services import SensitiveDataService


# ============ 敏感资料 ============

class SensitiveDataViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    敏感数据管理 ViewSet
    - list: 管理员/敏感审批人查看所有，普通成员查看自己的
    - create: 管理员/敏感审批人/老师创建（加密存储）
    - retrieve: 拥有者/管理员/审批人查看（脱敏）
    - my_data: GET 我的敏感资料（脱敏）
    - view: POST 查看明文（需有效审批，写日志，限时）
    """
    queryset = SensitiveData.objects.all().order_by('-created_at')
    # 默认序列化器（兜底）
    serializer_class = SensitiveDataSerializer

    serializer_classes_by_action = {
        'list': SensitiveDataSerializer,
        'retrieve': SensitiveDataSerializer,
        'create': SensitiveDataCreateSerializer,
        'my_data': SensitiveDataSerializer,
        'view': SensitiveDataSerializer,
    }

    permission_classes_by_action = {
        'list': [IsInternalSensitiveMember],
        'retrieve': [IsSensitiveDataOwner],
        'create': [IsSensitiveDataCreator],
        'update': [IsSensitiveDataCreator],
        'partial_update': [IsSensitiveDataCreator],
        'destroy': [IsSensitiveDataCreator],
        'my_data': [IsInternalSensitiveMember],
        'view': [HasValidAccessApproval],
        'grants': [IsInternalSensitiveMember],
        'revoke_grant': [IsInternalSensitiveMember],
        'grant_candidates': [IsInternalSensitiveMember],
        'grant_access_logs': [IsInternalSensitiveMember],
        'download_by_grant': [IsInternalSensitiveMember],
    }

    def get_queryset(self):
        """管理员/敏感审批人可查看所有，普通成员仅查看自己上传的"""
        queryset = super().get_queryset().select_related(
            'uploader', 'subject_user', 'team', 'project', 'file_attachment',
        )
        return scope_sensitive_data_queryset(queryset, self.request.user)

    def create(self, request, *args, **kwargs):
        """创建敏感资料（加密存储）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sensitive = serializer.save()

        # 写操作日志
        from apps.audit.models import OperationLog
        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.CREATE,
            module='sensitive',
            object_type='SensitiveData',
            object_id=str(sensitive.id),
            description=f'创建敏感资料: {sensitive.title}',
        )

        return success_response(
            SensitiveDataSerializer(sensitive, context={'request': request}).data,
            message='敏感资料创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def my_data(self, request):
        """
        我的敏感资料（脱敏）
        GET /api/v1/sensitive/data/my_data/
        """
        queryset = SensitiveData.objects.filter(
            Q(uploader=request.user) | Q(subject_user=request.user)
        ).select_related(
            'uploader', 'subject_user', 'team', 'project', 'file_attachment',
        ).distinct().order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        """
        查看明文（需有效审批，写日志，限时）
        POST /api/v1/sensitive/data/{id}/view/
        body: {"request_id": 1}
        """
        sensitive = self.get_object()
        grant_id = request.data.get('grant_id')
        request_id = request.data.get('request_id')
        if grant_id:
            success, result = SensitiveDataService.view_sensitive_data_by_grant(
                sensitive_data=sensitive,
                viewer=request.user,
                grant_id=grant_id,
                request=request,
            )
            if not success:
                return error_response(
                    message=result,
                    code=1003,
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            return success_response(
                {
                    'plaintext': result['plaintext'],
                    'grant_id': result['grant'].id,
                    'purpose': result['grant'].purpose,
                    'expires_at': result['grant'].expires_at,
                },
                message='已依据单份授权查看，请严格按授权用途使用',
            )
        if not request_id:
            return error_response(message='请提供 request_id 或 grant_id')

        success, result = SensitiveDataService.view_sensitive_data(
            request_id=request_id,
            viewer=request.user,
            request=request,
            expected_sensitive_data_id=sensitive.id,
        )
        if not success:
            return error_response(message=result, code=1003, http_status=status.HTTP_403_FORBIDDEN)

        return success_response(
            {'plaintext': result['plaintext']},
            message='查看成功，请注意明文保密',
        )

    @action(detail=True, methods=['get', 'post'])
    @transaction.atomic
    def grants(self, request, pk=None):
        """List or upsert purpose-bound grants for one sensitive record."""
        sensitive = self.get_object()
        can_manage = can_manage_sensitive_grants(request.user, sensitive)
        if request.method == 'GET':
            grants = SensitiveDataGrant.objects.filter(sensitive_data=sensitive)
            if not can_manage:
                grants = grants.filter(granted_to=request.user)
            grants = grants.select_related(
                'sensitive_data', 'granted_to', 'granted_by', 'revoked_by',
            ).order_by('-created_at')
            return success_response(SensitiveDataGrantSerializer(grants, many=True).data)
        if not can_manage:
            return error_response(
                message='只有资料本人、团队负责人或全局老师可以授权该资料',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SensitiveDataGrantSerializer(
            data=request.data,
            context={'request': request, 'sensitive_data': sensitive},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        grant, _ = SensitiveDataGrant.objects.update_or_create(
            sensitive_data=sensitive,
            granted_to=data['granted_to'],
            defaults={
                'can_view': data.get('can_view', True),
                'can_download': data.get('can_download', False),
                'purpose': data['purpose'],
                'expires_at': data['expires_at'],
                'granted_by': request.user,
                'revoked_at': None,
                'revoked_by': None,
            },
        )
        from apps.audit.models import OperationLog

        OperationLog.objects.create(
            operator=request.user,
            operation_type=OperationLog.OperationType.OTHER,
            module='sensitive',
            object_type='SensitiveDataGrant',
            object_id=str(grant.id),
            description=(
                f'授权 {grant.granted_to.name} 使用敏感资料 {sensitive.title}；'
                f'用途：{grant.purpose}；截止：{grant.expires_at.isoformat()}'
            ),
        )
        return success_response(
            SensitiveDataGrantSerializer(grant).data,
            message='单份资料授权已保存',
            http_status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['post'],
        url_path=r'grants/(?P<grant_id>[^/.]+)/revoke',
    )
    @transaction.atomic
    def revoke_grant(self, request, pk=None, grant_id=None):
        sensitive = self.get_object()
        if not can_manage_sensitive_grants(request.user, sensitive):
            return error_response(
                message='无权撤销该资料授权',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        grant = SensitiveDataGrant.objects.select_for_update().filter(
            pk=grant_id,
            sensitive_data=sensitive,
        ).first()
        if grant is None:
            return error_response(message='授权记录不存在', http_status=status.HTTP_404_NOT_FOUND)
        grant.revoked_at = timezone.now()
        grant.revoked_by = request.user
        grant.save(update_fields=['revoked_at', 'revoked_by', 'updated_at'])
        return success_response(SensitiveDataGrantSerializer(grant).data, message='授权已撤销')

    @action(detail=True, methods=['get'], url_path='grant-candidates')
    def grant_candidates(self, request, pk=None):
        sensitive = self.get_object()
        if not can_manage_sensitive_grants(request.user, sensitive):
            return error_response(
                message='无权选择该资料的被授权人',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        from apps.common.team_models import TeamMember
        from apps.users.models import User
        from apps.competitions.member_search import member_matches_search

        if sensitive.team_id:
            user_ids = TeamMember.objects.filter(
                team_id=sensitive.team_id,
                status=TeamMember.Status.ACTIVE,
            ).values_list('user_id', flat=True)
            users = User.objects.filter(pk__in=user_ids)
        else:
            users = User.objects.filter(membership_status__in=['active', 'on_leave'])
        users = users.filter(is_active=True).exclude(pk=request.user.id).order_by('name', 'id')
        query = request.query_params.get('search', '')
        candidates = []
        for user in users[:500]:
            if not member_matches_search(
                query=query,
                name=user.name,
                values=[user.name, user.username, user.email, user.phone, user.school, user.major],
            ):
                continue
            candidates.append({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'school': user.school,
                'major': user.major,
            })
            if len(candidates) >= 200:
                break
        return success_response(candidates)

    @action(detail=True, methods=['get'], url_path='grant-access-logs')
    def grant_access_logs(self, request, pk=None):
        sensitive = self.get_object()
        if not can_manage_sensitive_grants(request.user, sensitive):
            return error_response(
                message='无权查看该资料的授权审计',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        logs = SensitiveGrantAccessLog.objects.filter(
            sensitive_data=sensitive,
        ).select_related('grant', 'accessor').order_by('-accessed_at')[:200]
        return success_response(SensitiveGrantAccessLogSerializer(logs, many=True).data)

    @action(detail=True, methods=['get'], url_path='download-by-grant')
    def download_by_grant(self, request, pk=None):
        sensitive = SensitiveData.objects.select_related('file_attachment').filter(pk=pk).first()
        if sensitive is None:
            raise Http404('敏感资料不存在')
        success, message, grant = SensitiveDataService.resolve_direct_grant(
            sensitive_data=sensitive,
            viewer=request.user,
            grant_id=request.query_params.get('grant_id'),
            require_download=True,
        )
        if not success:
            SensitiveDataService.record_direct_grant_access(
                grant=grant,
                viewer=request.user,
                action=SensitiveGrantAccessLog.Action.DOWNLOAD,
                request=request,
                is_success=False,
                detail=message,
            )
            return error_response(message=message, code=1003, http_status=status.HTTP_403_FORBIDDEN)
        attachment = sensitive.file_attachment
        if not attachment or not attachment.file:
            SensitiveDataService.record_direct_grant_access(
                grant=grant,
                viewer=request.user,
                action=SensitiveGrantAccessLog.Action.DOWNLOAD,
                request=request,
                is_success=False,
                detail='敏感资料附件不存在',
            )
            raise Http404('敏感资料附件不存在')
        try:
            response = protected_media_response(
                attachment.file.name,
                as_attachment=True,
                download_name=attachment.name,
            )
        except Http404:
            SensitiveDataService.record_direct_grant_access(
                grant=grant,
                viewer=request.user,
                action=SensitiveGrantAccessLog.Action.DOWNLOAD,
                request=request,
                is_success=False,
                detail='敏感资料附件不存在',
            )
            raise
        SensitiveDataService.record_direct_grant_access(
            grant=grant,
            viewer=request.user,
            action=SensitiveGrantAccessLog.Action.DOWNLOAD,
            request=request,
        )
        record_download_audit(
            request,
            module='sensitive',
            object_type='SensitiveDataGrant',
            object_id=grant.id,
            channel='sensitive_direct_grant',
        )
        return response


# ============ 访问申请 ============


class SensitiveAccessRequestViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    敏感数据访问申请管理 ViewSet
    - list: 申请人查看自己的申请，审批人查看待审批的
    - create: 任何登录成员可创建申请
    - approve: POST 审批通过（敏感资料审批人/管理员）
    - reject: POST 驳回
    - my_requests: GET 我的申请
    - pending_approve: GET 待我审批
    - view_data: POST 限时查看敏感资料明文（检查权限，写日志）
    """
    queryset = SensitiveAccessRequest.objects.all().order_by('-created_at')
    # 默认序列化器（兜底）
    serializer_class = SensitiveAccessRequestSerializer

    serializer_classes_by_action = {
        'list': SensitiveAccessRequestSerializer,
        'retrieve': SensitiveAccessRequestSerializer,
        'create': SensitiveAccessRequestCreateSerializer,
        'approve': SensitiveAccessRequestReviewSerializer,
        'reject': SensitiveAccessRequestReviewSerializer,
        'my_requests': SensitiveAccessRequestSerializer,
        'pending_approve': SensitiveAccessRequestSerializer,
        'view_data': SensitiveAccessRequestSerializer,
    }

    permission_classes_by_action = {
        'list': [IsInternalSensitiveMember],
        'retrieve': [IsInternalSensitiveMember],
        'create': [IsInternalSensitiveMember],
        'approve': [IsSensitiveApproverOrAdmin],
        'reject': [IsSensitiveApproverOrAdmin],
        'my_requests': [IsInternalSensitiveMember],
        'pending_approve': [IsSensitiveApproverOrAdmin],
        'view_data': [HasValidAccessApproval],
        'download_attachment': [IsInternalSensitiveMember],
    }
    # 申请内容提交后不可通过通用 CRUD 改写，审批只能走 approve/reject。
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """申请人查看自己的申请，审批人查看待审批的"""
        queryset = super().get_queryset().select_related(
            'sensitive_data', 'sensitive_data__file_attachment',
            'sensitive_data__team', 'sensitive_data__subject_user',
            'applicant', 'approver', 'project',
        )
        user = self.request.user
        params = self.request.query_params
        review_team_ids = sensitive_review_team_ids(user)
        review_filter = Q(sensitive_data__team_id__in=review_team_ids)
        if (
            user.global_role == 'sens_approver'
            and user.membership_status in {'active', 'on_leave'}
        ):
            review_filter |= Q(sensitive_data__team__isnull=True)
        queryset = queryset.filter(Q(applicant=user) | review_filter)
        stat = params.get('status')
        if stat:
            queryset = queryset.filter(status=stat)
        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        """创建访问申请"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_request = serializer.save()
        return success_response(
            SensitiveAccessRequestSerializer(access_request).data,
            message='访问申请提交成功，等待审批',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        审批通过（设置过期时间，默认1小时）
        POST /api/v1/sensitive/requests/{id}/approve/
        body: {"approval_opinion": "同意", "expire_hours": 1}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        if validated_data.get('action') != 'approve':
            return error_response(message='该接口仅支持审批通过操作')

        access_request = SensitiveAccessRequest.objects.select_related(
            'sensitive_data', 'sensitive_data__team',
        ).filter(pk=pk).first()
        if access_request is None or not can_review_sensitive_request(request.user, access_request):
            return error_response(
                message='无权处理其他团队的敏感资料申请',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        success, result = SensitiveDataService.approve_request(
            request_id=pk,
            approver=request.user,
            expire_hours=validated_data.get('expire_hours', 1),
            approval_opinion=validated_data.get('approval_opinion', ''),
        )
        if not success:
            return error_response(message=result)

        return success_response(
            SensitiveAccessRequestSerializer(result).data,
            message='审批通过',
        )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        驳回申请
        POST /api/v1/sensitive/requests/{id}/reject/
        body: {"approval_opinion": "理由"}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        if validated_data.get('action') != 'reject':
            return error_response(message='该接口仅支持驳回操作')

        access_request = SensitiveAccessRequest.objects.select_related(
            'sensitive_data', 'sensitive_data__team',
        ).filter(pk=pk).first()
        if access_request is None or not can_review_sensitive_request(request.user, access_request):
            return error_response(
                message='无权处理其他团队的敏感资料申请',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        success, result = SensitiveDataService.reject_request(
            request_id=pk,
            approver=request.user,
            approval_opinion=validated_data.get('approval_opinion', ''),
        )
        if not success:
            return error_response(message=result)

        return success_response(
            SensitiveAccessRequestSerializer(result).data,
            message='已驳回',
        )

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """
        我的申请
        GET /api/v1/sensitive/requests/my_requests/
        支持标准分页参数：page、page_size
        """
        queryset = self.get_queryset().filter(applicant=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SensitiveAccessRequestSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SensitiveAccessRequestSerializer(queryset, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending_approve(self, request):
        """
        待我审批（全体审批角色共享队列，排除本人提交的申请）
        GET /api/v1/sensitive/requests/pending_approve/
        支持标准分页参数：page、page_size
        """
        team_filter = Q(
            sensitive_data__team_id__in=sensitive_review_team_ids(request.user)
        )
        if (
            request.user.global_role == 'sens_approver'
            and request.user.membership_status in {'active', 'on_leave'}
        ):
            team_filter |= Q(sensitive_data__team__isnull=True)
        queryset = self.get_queryset().filter(
            team_filter,
            status=SensitiveAccessRequest.Status.PENDING,
        ).exclude(
            applicant=request.user,
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SensitiveAccessRequestSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SensitiveAccessRequestSerializer(queryset, many=True)
        return success_response(serializer.data)

    @action(detail=True, methods=['post'])
    def view_data(self, request, pk=None):
        """
        限时查看敏感资料明文（检查权限，写日志）
        POST /api/v1/sensitive/requests/{id}/view_data/
        - 检查申请已通过且未过期
        - 解密返回明文
        - 写 OperationLog
        """
        success, result = SensitiveDataService.view_sensitive_data(
            request_id=pk, viewer=request.user, request=request,
        )
        if not success:
            return error_response(message=result, code=1003, http_status=status.HTTP_403_FORBIDDEN)

        return success_response(
            {
                'plaintext': result['plaintext'],
                'sensitive_data_id': result['sensitive_data'].id,
                'sensitive_data_title': result['sensitive_data'].title,
                'access_expires_at': result['request'].access_expires_at,
            },
            message='查看成功，请在有效期内使用并注意明文保密',
        )

    @action(
        detail=True,
        methods=['get'],
        url_path='download-attachment',
    )
    def download_attachment(self, request, pk=None):
        """
        仅允许申请人本人依据“已批准、允许下载、未过期”的申请下载附件。
        审批角色下载自己的资料时同样必须提交申请并获得他人审批。
        """
        access_request = self.get_object()
        sensitive = access_request.sensitive_data

        def denied(message, http_status=status.HTTP_403_FORBIDDEN):
            record_download_audit(
                request,
                module='sensitive',
                object_type='SensitiveAccessRequest',
                object_id=access_request.id,
                channel='sensitive_request',
                is_success=False,
                response_status=http_status,
            )
            return error_response(
                message=message,
                code=1003,
                http_status=http_status,
            )

        if access_request.applicant_id != request.user.id:
            return denied('仅申请人本人可下载敏感资料附件')
        if access_request.status != SensitiveAccessRequest.Status.APPROVED:
            return denied('申请未通过审批，无法下载附件')
        if not access_request.is_download:
            return denied('该申请未获下载权限')
        if (
            not access_request.access_expires_at
            or timezone.now() >= access_request.access_expires_at
        ):
            if access_request.status == SensitiveAccessRequest.Status.APPROVED:
                access_request.status = SensitiveAccessRequest.Status.EXPIRED
                access_request.save(update_fields=['status'])
            return denied('下载权限已过期，请重新申请')

        attachment = sensitive.file_attachment
        if not attachment or not attachment.file:
            return denied(
                '敏感资料附件不存在',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        try:
            response = protected_media_response(
                attachment.file.name,
                as_attachment=True,
                download_name=attachment.name,
            )
        except Http404:
            return denied(
                '敏感资料附件不存在',
                http_status=status.HTTP_404_NOT_FOUND,
            )

        record_download_audit(
            request,
            module='sensitive',
            object_type='SensitiveAccessRequest',
            object_id=access_request.id,
            channel='sensitive_request',
        )
        return response
