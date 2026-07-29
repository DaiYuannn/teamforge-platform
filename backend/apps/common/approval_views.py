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
from django.utils import timezone

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from common.permissions import IsTeacherOrAdminOrReadOnly
from .approval_models import ApprovalFlow, ApprovalRequest
from .approval_services import (
    approval_reviewer_details,
    approval_reviewer_spec_for_step,
    approval_step,
    apply_business_decision,
    cancel_business_request,
    is_authorized_reviewer,
    prepare_business_request,
    validate_business_metadata,
)


def _append_review(metadata, review):
    """Append one server-authored audit entry to otherwise user metadata."""
    normalized = dict(metadata or {})
    reviews = normalized.get('reviews')
    if not isinstance(reviews, list):
        reviews = []
    reviews.append(review)
    normalized['reviews'] = reviews
    return normalized


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

    def validate_steps(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Approval steps must be a list')
        if not value:
            raise serializers.ValidationError(
                'A new approval flow requires at least one assigned step'
            )
        normalized = []
        for index, raw_step in enumerate(value):
            if not isinstance(raw_step, dict):
                raise serializers.ValidationError(
                    f'Approval step {index + 1} must be an object'
                )
            step = dict(raw_step)
            name = str(step.get('name', '')).strip()
            if not name:
                raise serializers.ValidationError(
                    f'Approval step {index + 1} requires a name'
                )
            step['name'] = name
            reviewer_ids, reviewer_roles = approval_reviewer_spec_for_step(step)
            if not reviewer_ids and not reviewer_roles:
                # Preserve the historical API shape while making the new flow
                # assignment explicit. It no longer falls back to every teacher.
                step['reviewer_role'] = 'sys_admin'
            if 'reviewer_ids' in step:
                if not isinstance(step['reviewer_ids'], list):
                    raise serializers.ValidationError(
                        f'Approval step {index + 1} reviewer_ids must be a list'
                    )
                try:
                    step['reviewer_ids'] = sorted({
                        int(user_id) for user_id in step['reviewer_ids']
                    })
                except (TypeError, ValueError) as exc:
                    raise serializers.ValidationError(
                        f'Approval step {index + 1} has invalid reviewer_ids'
                    ) from exc
            if 'reviewer_roles' in step:
                if not isinstance(step['reviewer_roles'], list):
                    raise serializers.ValidationError(
                        f'Approval step {index + 1} reviewer_roles must be a list'
                    )
                step['reviewer_roles'] = sorted({
                    str(role).strip()
                    for role in step['reviewer_roles']
                    if str(role).strip()
                })
            normalized.append(step)
        return normalized


class ApprovalRequestSerializer(serializers.ModelSerializer):
    """审批申请序列化器"""
    applicant_name = serializers.CharField(source='applicant.name', read_only=True, default='')
    flow_name = serializers.CharField(source='flow.name', read_only=True, default='')
    flow_type = serializers.CharField(source='flow.flow_type', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_step_name = serializers.SerializerMethodField()
    reviewer_ids = serializers.SerializerMethodField()
    reviewer_roles = serializers.SerializerMethodField()
    reviewer_names = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    review_history = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = (
            'id', 'applicant', 'applicant_name', 'flow', 'flow_name', 'flow_type',
            'status', 'status_display', 'title', 'content',
            'current_step', 'current_step_name', 'reviewer_ids',
            'reviewer_roles', 'reviewer_names', 'can_review', 'review_history',
            'metadata', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'applicant', 'status', 'current_step', 'created_at', 'updated_at')

    def get_current_step_name(self, obj):
        step = approval_step(obj)
        if step:
            return str(step.get('name') or f'第 {obj.current_step + 1} 级审批')
        return '流程已结束' if obj.status != ApprovalRequest.Status.PENDING else '历史兼容审批'

    @staticmethod
    def _reviewer_details(obj):
        cache_name = '_serialized_approval_reviewer_details'
        details = getattr(obj, cache_name, None)
        if details is None:
            details = approval_reviewer_details(obj)
            setattr(obj, cache_name, details)
        return details

    def get_reviewer_ids(self, obj):
        return self._reviewer_details(obj)['reviewer_ids']

    def get_reviewer_roles(self, obj):
        return self._reviewer_details(obj)['reviewer_roles']

    def get_reviewer_names(self, obj):
        return self._reviewer_details(obj)['reviewer_names']

    def get_can_review(self, obj):
        request = self.context.get('request')
        return bool(request and is_authorized_reviewer(request.user, obj))

    def get_review_history(self, obj):
        from apps.users.models import User

        reviews = [
            dict(review)
            for review in (obj.metadata or {}).get('reviews', [])
            if isinstance(review, dict)
        ]
        reviewer_ids = {
            review.get('by')
            for review in reviews
            if review.get('by')
        }
        names = dict(
            User.objects.filter(id__in=reviewer_ids).values_list('id', 'name')
        )
        for review in reviews:
            review.setdefault('by_name', names.get(review.get('by'), ''))
        return reviews


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
            flow=attrs['flow'],
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
            ApprovalRequestSerializer(req, context={'request': request}).data,
            message='审批申请已提交',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def approve(self, request, pk=None):
        """审批通过"""
        visible_request = self.get_object()
        req = ApprovalRequest.objects.select_for_update().select_related(
            'applicant',
            'flow',
        ).get(pk=visible_request.pk)
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可操作', code=2501)
        if not is_authorized_reviewer(request.user, req):
            return error_response(
                message='当前审批节点未授权该用户审批',
                code=2502,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        steps = req.flow.steps or []
        reviewed_step = req.current_step
        reviewed_step_name = str(
            approval_step(req).get('name')
            or f'第 {reviewed_step + 1} 级审批'
        )
        opinion = serializer.validated_data.get('opinion', '')
        # 推进步骤，若已是最后一步则通过
        if req.current_step + 1 >= len(steps):
            req.status = ApprovalRequest.Status.APPROVED
            apply_business_decision(
                req,
                approved=True,
                actor=request.user,
                opinion=opinion,
            )
        else:
            req.current_step = req.current_step + 1
        meta = _append_review(req.metadata, {
            'action': 'approve',
            'opinion': opinion,
            'by': request.user.id,
            'by_name': request.user.name,
            'step': reviewed_step,
            'step_name': reviewed_step_name,
            'at': timezone.now().isoformat(),
        })
        req.metadata = meta
        req.save(update_fields=['status', 'current_step', 'metadata', 'updated_at'])
        return success_response(
            ApprovalRequestSerializer(req, context={'request': request}).data,
            message='审批通过',
        )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reject(self, request, pk=None):
        """驳回"""
        visible_request = self.get_object()
        req = ApprovalRequest.objects.select_for_update().select_related(
            'applicant',
            'flow',
        ).get(pk=visible_request.pk)
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可操作', code=2501)
        if not is_authorized_reviewer(request.user, req):
            return error_response(
                message='当前审批节点未授权该用户审批',
                code=2502,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reviewed_step = req.current_step
        reviewed_step_name = str(
            approval_step(req).get('name')
            or f'第 {reviewed_step + 1} 级审批'
        )
        opinion = serializer.validated_data.get('opinion', '')
        req.status = ApprovalRequest.Status.REJECTED
        apply_business_decision(
            req,
            approved=False,
            actor=request.user,
            opinion=opinion,
        )
        meta = _append_review(req.metadata, {
            'action': 'reject',
            'opinion': opinion,
            'by': request.user.id,
            'by_name': request.user.name,
            'step': reviewed_step,
            'step_name': reviewed_step_name,
            'at': timezone.now().isoformat(),
        })
        req.metadata = meta
        req.save(update_fields=['status', 'metadata', 'updated_at'])
        return success_response(
            ApprovalRequestSerializer(req, context={'request': request}).data,
            message='已驳回',
        )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        """取消申请"""
        visible_request = self.get_object()
        req = ApprovalRequest.objects.select_for_update().select_related(
            'applicant',
            'flow',
        ).get(pk=visible_request.pk)
        if req.applicant_id != request.user.id:
            return error_response(message='仅申请人可取消', code=2502,
                                  http_status=status.HTTP_403_FORBIDDEN)
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可取消', code=2503)
        req.status = ApprovalRequest.Status.CANCELLED
        cancel_business_request(req)
        meta = _append_review(req.metadata, {
            'action': 'cancel',
            'opinion': '',
            'by': request.user.id,
            'by_name': request.user.name,
            'step': req.current_step,
            'step_name': str(
                approval_step(req).get('name')
                or f'第 {req.current_step + 1} 级审批'
            ),
            'at': timezone.now().isoformat(),
        })
        req.metadata = meta
        req.save(update_fields=['status', 'metadata', 'updated_at'])
        return success_response(
            ApprovalRequestSerializer(req, context={'request': request}).data,
            message='已取消',
        )

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """我的申请"""
        qs = self.get_queryset().filter(applicant=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ApprovalRequestSerializer(
                page,
                many=True,
                context={'request': request},
            )
            return self.get_paginated_response(serializer.data)
        return success_response(
            ApprovalRequestSerializer(
                qs,
                many=True,
                context={'request': request},
            ).data
        )

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
        """Compatibility wrapper retained for callers of the old helper."""
        return is_authorized_reviewer(user, req)
