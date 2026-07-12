"""
审批流程序列化器与视图
- ApprovalFlowViewSet: 审批流程 CRUD
- ApprovalRequestViewSet: 审批申请 CRUD + approve/reject/cancel
"""
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from .approval_models import ApprovalFlow, ApprovalRequest


# ============ 序列化器 ============

class ApprovalFlowSerializer(serializers.ModelSerializer):
    """审批流程序列化器"""

    class Meta:
        model = ApprovalFlow
        fields = ('id', 'name', 'flow_type', 'steps', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


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


class ApprovalReviewSerializer(serializers.Serializer):
    """审批/驳回请求序列化器"""
    opinion = serializers.CharField(required=False, default='')
    next_step = serializers.IntegerField(required=False)


# ============ ViewSet ============

class ApprovalFlowViewSet(ModelViewSet):
    """审批流程管理 ViewSet"""
    queryset = ApprovalFlow.objects.all().order_by('-created_at')
    serializer_class = ApprovalFlowSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['flow_type', 'is_active']
    search_fields = ['name', 'flow_type']
    ordering_fields = ['created_at', 'name']

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
        # 普通成员仅查看自己的申请；管理员可查看全部
        user = self.request.user
        qs = super().get_queryset().select_related('applicant', 'flow')
        if user.global_role in ('sys_admin', 'teacher'):
            return qs
        return qs.filter(applicant=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = serializer.save(applicant=request.user, status=ApprovalRequest.Status.PENDING)
        return success_response(
            ApprovalRequestSerializer(req).data,
            message='审批申请已提交',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """审批通过"""
        req = self.get_object()
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可操作', code=2501)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        steps = req.flow.steps or []
        # 推进步骤，若已是最后一步则通过
        if req.current_step + 1 >= len(steps):
            req.status = ApprovalRequest.Status.APPROVED
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
    def reject(self, request, pk=None):
        """驳回"""
        req = self.get_object()
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可操作', code=2501)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req.status = ApprovalRequest.Status.REJECTED
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
    def cancel(self, request, pk=None):
        """取消申请"""
        req = self.get_object()
        if req.applicant_id != request.user.id:
            return error_response(message='仅申请人可取消', code=2502,
                                  http_status=status.HTTP_403_FORBIDDEN)
        if req.status != ApprovalRequest.Status.PENDING:
            return error_response(message='仅待审批的申请可取消', code=2503)
        req.status = ApprovalRequest.Status.CANCELLED
        req.save(update_fields=['status', 'updated_at'])
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
