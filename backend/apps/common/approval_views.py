"""
审批流程序列化器与视图
- ApprovalFlowViewSet: 审批流程 CRUD
- ApprovalRequestViewSet: 审批申请 CRUD + approve/reject/cancel
"""
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django.db.models import Q
from django.db import transaction

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from common.permissions import IsTeacherOrAdminOrReadOnly
from .approval_models import ApprovalFlow, ApprovalRequest
from .approval_services import (
    apply_business_decision,
    cancel_business_request,
    prepare_business_request,
    validate_business_metadata,
)


# ============ 序列化器 ============

class ApprovalFlowSerializer(serializers.ModelSerializer):
    """审批流程序列化器"""

    class Meta:
        model = ApprovalFlow
        fields = ('id', 'name', 'flow_type', 'steps', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_flow_type(self, value):
        if not value.strip():
            raise serializers.ValidationError('Approval flow type is required')
        return value


class ApprovalRequestSerializer(serializers.ModelSerializer):
    """审批申请序列化器"""
    applicant_name = serializers.CharField(source='applicant.name', read_only=True, default='')
    flow_name = serializers.CharField(source='flow.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = (
            'id', 'applicant', 'applicant_name', 'flow', 'flow_name',
            'status', 'status_display', 'title', 'content',
            'current_step', 'metadata', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'applicant', 'status', 'current_step', 'created_at', 'updated_at')


class ApprovalRequestCreateSerializer(serializers.ModelSerializer):
    """审批申请创建序列化器"""

    class Meta:
        model = ApprovalRequest
        fields = ('id', 'flow', 'title', 'content', 'metadata')
        read_only_fields = ('id',)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs['metadata'] = validate_business_metadata(
            attrs['flow'].flow_type,
            attrs.get('metadata', {}),
            self.context['request'].user,
        )
        return attrs


class ApprovalReviewSerializer(serializers.Serializer):
    """审批/驳回请求序列化器"""
    opinion = serializers.CharField(required=False, default='')
    next_step = serializers.IntegerField(required=False)


# ============ ViewSet ============

class ApprovalFlowViewSet(ModelViewSet):
    """审批流程管理 ViewSet"""
    queryset = ApprovalFlow.objects.all().order_by('-created_at')
    serializer_class = ApprovalFlowSerializer
    permission_classes = [IsTeacherOrAdminOrReadOnly]
    filterset_fields = ['flow_type', 'is_active']
    search_fields = ['name', 'flow_type']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.global_role in ('teacher', 'sys_admin'):
            return queryset
        return queryset.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        flow = serializer.save()
        return success_response(
            ApprovalFlowSerializer(flow).data,
            message='审批流程创建成功',
            http_status=status.HTTP_201_CREATED,
        )


class ApprovalRequestViewSet(MultiSerializerMixin, ModelViewSet):
    """
    审批申请管理 ViewSet
    - list: 当前用户查看自己的申请
    - create: 创建申请（applicant 自动设为当前用户）
    - approve: POST 审批通过
    - reject: POST 驳回
    - cancel: POST 取消
    - my_requests: GET 我的申请
    """
    queryset = ApprovalRequest.objects.all().order_by('-created_at')
    serializer_class = ApprovalRequestSerializer
    serializer_classes_by_action = {
        'list': ApprovalRequestSerializer,
        'retrieve': ApprovalRequestSerializer,
        'create': ApprovalRequestCreateSerializer,
        'approve': ApprovalReviewSerializer,
        'reject': ApprovalReviewSerializer,
    }
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'flow']
    ordering_fields = ['created_at', 'updated_at']

    def get_queryset(self):
        # 管理角色可查看全部；其他成员可看自己的申请和当前轮到自己审批的申请。
        user = self.request.user
        qs = super().get_queryset().select_related('applicant', 'flow')
        if user.global_role in ('sys_admin', 'teacher'):
            return qs
        reviewable_ids = [
            req.id
            for req in qs.filter(status=ApprovalRequest.Status.PENDING)
            if self._is_authorized_reviewer(user, req)
        ]
        return qs.filter(Q(applicant=user) | Q(id__in=reviewable_ids))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data['flow'].is_active:
            return error_response(
                message='审批流程已停用',
                code=2504,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            req = serializer.save(applicant=request.user, status=ApprovalRequest.Status.PENDING)
            prepare_business_request(req)
        return success_response(
            ApprovalRequestSerializer(req).data,
            message='审批申请已提交',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def approve(self, request, pk=None):
        """审批通过"""
        req = self.get_object()
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可操作', code=2501)
        if not self._is_authorized_reviewer(request.user, req):
            return error_response(
                message='当前审批节点未授权该用户审批',
                code=2502,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        steps = req.flow.steps or []
        # 推进步骤，若已是最后一步则通过
        if req.current_step + 1 >= len(steps):
            req.status = ApprovalRequest.Status.APPROVED
            apply_business_decision(
                req,
                approved=True,
                actor=request.user,
                opinion=serializer.validated_data.get('opinion', ''),
            )
        else:
            req.current_step = req.current_step + 1
        meta = dict(req.metadata or {})
        meta.setdefault('reviews', []).append({
            'action': 'approve',
            'opinion': serializer.validated_data.get('opinion', ''),
            'by': request.user.id,
        })
        req.metadata = meta
        req.save(update_fields=['status', 'current_step', 'metadata', 'updated_at'])
        return success_response(ApprovalRequestSerializer(req).data, message='审批通过')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reject(self, request, pk=None):
        """驳回"""
        req = self.get_object()
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可操作', code=2501)
        if not self._is_authorized_reviewer(request.user, req):
            return error_response(
                message='当前审批节点未授权该用户审批',
                code=2502,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req.status = ApprovalRequest.Status.REJECTED
        apply_business_decision(
            req,
            approved=False,
            actor=request.user,
            opinion=serializer.validated_data.get('opinion', ''),
        )
        meta = dict(req.metadata or {})
        meta.setdefault('reviews', []).append({
            'action': 'reject',
            'opinion': serializer.validated_data.get('opinion', ''),
            'by': request.user.id,
        })
        req.metadata = meta
        req.save(update_fields=['status', 'metadata', 'updated_at'])
        return success_response(ApprovalRequestSerializer(req).data, message='已驳回')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        """取消申请"""
        req = self.get_object()
        if req.applicant_id != request.user.id:
            return error_response(message='仅申请人可取消', code=2502,
                                  http_status=status.HTTP_403_FORBIDDEN)
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可取消', code=2503)
        req.status = ApprovalRequest.Status.CANCELLED
        cancel_business_request(req)
        req.save(update_fields=['status', 'metadata', 'updated_at'])
        return success_response(ApprovalRequestSerializer(req).data, message='已取消')

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """我的申请"""
        qs = self.get_queryset().filter(applicant=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ApprovalRequestSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return success_response(ApprovalRequestSerializer(qs, many=True).data)

    @staticmethod
    def _as_set(value):
        if value in (None, ''):
            return set()
        if isinstance(value, (list, tuple, set)):
            values = value
        else:
            values = [value]
        return {str(item) for item in values if item not in (None, '')}

    @classmethod
    def _is_authorized_reviewer(cls, user, req):
        """Match the current flow step by explicit reviewer IDs or roles."""
        if (
            not user
            or not user.is_authenticated
            or req.applicant_id == user.id
            or req.status != ApprovalRequest.Status.PENDING
        ):
            return False

        steps = req.flow.steps or []
        step = (
            steps[req.current_step]
            if 0 <= req.current_step < len(steps)
            and isinstance(steps[req.current_step], dict)
            else {}
        )

        reviewer_ids = set()
        reviewer_roles = set()
        for key in (
            'reviewer_id', 'reviewer_ids', 'approver_id', 'approver_ids',
            'user_id', 'user_ids',
        ):
            reviewer_ids.update(cls._as_set(step.get(key)))
        for key in (
            'reviewer_role', 'reviewer_roles', 'approver_role',
            'approver_roles', 'required_role', 'required_roles',
            'role', 'roles',
        ):
            reviewer_roles.update(cls._as_set(step.get(key)))

        reviewer = step.get('reviewer')
        if isinstance(reviewer, dict):
            reviewer_ids.update(cls._as_set(reviewer.get('id')))
            reviewer_roles.update(cls._as_set(reviewer.get('role')))
        elif reviewer not in (None, ''):
            reviewer_ids.update(cls._as_set(reviewer))

        if reviewer_ids or reviewer_roles:
            return (
                str(user.id) in reviewer_ids
                or str(user.global_role) in reviewer_roles
            )

        # Legacy flows only carried a display name for each step.
        return user.global_role in ('teacher', 'sys_admin')
