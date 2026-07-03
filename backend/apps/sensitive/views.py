"""
敏感资料视图
- SensitiveDataViewSet: 敏感资料 CRUD + 我的资料 + 查看明文（需有效审批）
- SensitiveAccessRequestViewSet: 访问申请 CRUD + 审批/驳回 + 我的申请 + 待审批 + 限时查看明文
关键：敏感资料明文绝不裸露，必须审批后限时查看，每次查看必须写 OperationLog
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from .models import SensitiveData, SensitiveAccessRequest
from .serializers import (
    SensitiveDataSerializer,
    SensitiveDataCreateSerializer,
    SensitiveAccessRequestSerializer,
    SensitiveAccessRequestCreateSerializer,
    SensitiveAccessRequestReviewSerializer,
)
from .permissions import (
    IsSensitiveDataOwner,
    IsSensitiveApproverOrAdmin,
    IsSensitiveDataCreator,
    HasValidAccessApproval,
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
        'list': [IsAuthenticated],
        'retrieve': [IsSensitiveDataOwner],
        'create': [IsSensitiveDataCreator],
        'update': [IsSensitiveDataCreator],
        'partial_update': [IsSensitiveDataCreator],
        'destroy': [IsSensitiveDataCreator],
        'my_data': [IsAuthenticated],
        'view': [HasValidAccessApproval],
    }

    def get_queryset(self):
        """管理员/敏感审批人可查看所有，普通成员仅查看自己上传的"""
        queryset = super().get_queryset().select_related('uploader', 'project')
        user = self.request.user
        if user.global_role in ['sys_admin', 'sens_approver', 'teacher']:
            return queryset
        # view 动作需要访问所有敏感资料（通过 request_id 校验权限）
        if self.action == 'view':
            return queryset
        # 普通成员仅查看自己上传的
        return queryset.filter(uploader=user)

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
            SensitiveDataSerializer(sensitive).data,
            message='敏感资料创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def my_data(self, request):
        """
        我的敏感资料（脱敏）
        GET /api/v1/sensitive/data/my_data/
        """
        queryset = SensitiveData.objects.filter(uploader=request.user).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SensitiveDataSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SensitiveDataSerializer(queryset, many=True)
        return success_response(serializer.data)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        """
        查看明文（需有效审批，写日志，限时）
        POST /api/v1/sensitive/data/{id}/view/
        body: {"request_id": 1}
        """
        sensitive = self.get_object()
        request_id = request.data.get('request_id')
        if not request_id:
            return error_response(message='请提供 request_id（访问申请ID）')

        success, result = SensitiveDataService.view_sensitive_data(
            request_id=request_id, viewer=request.user, request=request,
        )
        if not success:
            return error_response(message=result, code=1003, http_status=status.HTTP_403_FORBIDDEN)

        # 校验申请对应的敏感资料与当前资源一致
        if result['sensitive_data'].id != sensitive.id:
            return error_response(
                message='访问申请与敏感资料不匹配', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        return success_response(
            {'plaintext': result['plaintext']},
            message='查看成功，请注意明文保密',
        )


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
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'approve': [IsSensitiveApproverOrAdmin],
        'reject': [IsSensitiveApproverOrAdmin],
        'my_requests': [IsAuthenticated],
        'pending_approve': [IsSensitiveApproverOrAdmin],
        'view_data': [HasValidAccessApproval],
    }

    def get_queryset(self):
        """申请人查看自己的申请，审批人查看待审批的"""
        queryset = super().get_queryset().select_related(
            'sensitive_data', 'applicant', 'approver', 'project',
        )
        user = self.request.user
        params = self.request.query_params
        # 审批人/管理员/老师可查看所有，并支持按 status 筛选
        if user.global_role in ['sens_approver', 'sys_admin', 'teacher']:
            stat = params.get('status')
            if stat:
                queryset = queryset.filter(status=stat)
            return queryset
        # 普通成员仅查看自己的申请
        return queryset.filter(applicant=user)

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
        待我审批
        GET /api/v1/sensitive/requests/pending_approve/
        """
        queryset = self.get_queryset().filter(
            status=SensitiveAccessRequest.Status.PENDING
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
