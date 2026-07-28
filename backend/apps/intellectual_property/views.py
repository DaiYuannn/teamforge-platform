"""
知识产权管理视图
- IPApplicationViewSet: 申请档案 CRUD + 状态流转 + 归档 + 贡献同步 + 待办
- IPContributorViewSet: 责任分工管理
- IPReturnRecordViewSet: 退回记录管理 + 完成修改
- IPMaterialVersionViewSet: 材料版本管理
- IPObjectionViewSet: 异议管理 + 异议处理
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsTeacherOrAdmin
from .models import (
    IntellectualPropertyApplication,
    IPApplicationCandidate,
    IPApplicationContributor,
    IPReturnRecord,
    IPMaterialVersion,
    IPObjection,
)
from .serializers import (
    IPApplicationListSerializer,
    IPApplicationDetailSerializer,
    IPApplicationCreateSerializer,
    IPApplicationUpdateSerializer,
    IPApplicationCandidateSerializer,
    IPApplicationContributorSerializer,
    IPReturnRecordSerializer,
    IPReturnRecordCreateSerializer,
    IPReturnResolveSerializer,
    IPMaterialVersionSerializer,
    IPMaterialVersionCreateSerializer,
    IPObjectionSerializer,
    IPObjectionCreateSerializer,
    IPObjectionReviewSerializer,
)
from .permissions import (
    IsIPProjectMember,
    IsProjectLeaderOrTeacherOrAdminForIP,
    IsMainWriterOrExecutor,
    IsReturnModifier,
    _can_access_application,
    _is_application_leader_or_privileged,
    accessible_ip_applications,
)
from .services import ip_service


class IPApplicationViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    知识产权申请管理 ViewSet
    - list: 所有认证用户可查看（公开字段）
    - retrieve: 所有认证用户可查看（项目成员看完整字段，非成员看公开字段）
    - create: 项目负责人/老师/管理员
    - update/partial_update: 项目负责人/老师/管理员 或 主导撰写人/申请执行人
    - destroy: 老师/管理员
    - transition: POST 状态流转
    - archive: POST 成果归档
    - sync_contribution: POST 同步贡献
    - my_todo: GET 待我处理
    """
    queryset = IntellectualPropertyApplication.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': IPApplicationListSerializer,
        'retrieve': IPApplicationDetailSerializer,
        'create': IPApplicationCreateSerializer,
        'update': IPApplicationUpdateSerializer,
        'partial_update': IPApplicationUpdateSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdminForIP],
        'update': [IsMainWriterOrExecutor],
        'partial_update': [IsMainWriterOrExecutor],
        'destroy': [IsTeacherOrAdmin],
        'transition': [IsAuthenticated],
        'archive': [IsAuthenticated],
        'sync_contribution': [IsAuthenticated],
        'my_todo': [IsAuthenticated],
        'candidates': [IsAuthenticated],
    }

    filterset_fields = ['ip_type', 'status', 'related_project', 'main_writer', 'applicant_executor']
    search_fields = ['title', 'application_code', 'intro']
    ordering_fields = ['created_at', 'updated_at', 'submit_date', 'accepted_date']

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('related_project', 'related_project__leader')
            .prefetch_related(
                'project_links__project',
                'candidates__user',
            )
            .filter(pk__in=accessible_ip_applications(self.request.user))
        )

    def get_serializer_class(self):
        """
        retrieve 时根据项目成员身份返回不同序列化器
        - 项目成员/老师/管理员：返回 DetailSerializer（完整字段）
        - 非项目成员：返回 ListSerializer（公开字段）
        """
        if getattr(self, 'action', None) == 'retrieve':
            if getattr(self, 'swagger_fake_view', False):
                return IPApplicationDetailSerializer
            instance = self.get_object()
            if not _can_access_application(self.request.user, instance):
                return IPApplicationListSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        """创建知识产权申请"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        return success_response(
            IPApplicationDetailSerializer(application).data,
            message='知识产权申请创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新知识产权申请"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        return success_response(
            IPApplicationDetailSerializer(application).data,
            message='知识产权申请更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除知识产权申请"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='知识产权申请删除成功')

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        """
        状态流转
        POST /api/v1/intellectual-property/applications/{id}/transition/
        body: {"target_status": "writing"}
        """
        application = self.get_object()
        target_status = request.data.get('target_status')
        if not target_status:
            return error_response(message='请提供 target_status 参数')

        # 权限随当前审批阶段收紧，避免业务角色越过后续审核节点。
        user = request.user
        is_privileged = user.global_role in ['sys_admin', 'teacher']
        is_project_leader = _is_application_leader_or_privileged(
            user, application
        )
        institutional_targets = (
            IntellectualPropertyApplication.Status.ACCEPTED,
            IntellectualPropertyApplication.Status.RETURNED,
            IntellectualPropertyApplication.Status.AUTHORIZED,
            IntellectualPropertyApplication.Status.ARCHIVED,
        )
        if target_status in institutional_targets:
            can_transition = is_privileged
        elif application.status == IntellectualPropertyApplication.Status.LEADER_REVIEW:
            can_transition = (
                is_privileged
                or is_project_leader
                or application.project_reviewer_id == user.id
            )
        elif application.status == IntellectualPropertyApplication.Status.TEACHER_CONFIRM:
            can_transition = (
                is_privileged or application.teacher_confirmer_id == user.id
            )
        elif application.status in (
            IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
            IntellectualPropertyApplication.Status.ACCEPTED,
            IntellectualPropertyApplication.Status.AUTHORIZED,
        ):
            can_transition = is_privileged
        else:
            can_transition = (
                is_privileged
                or is_project_leader
                or application.main_writer_id == user.id
                or application.applicant_executor_id == user.id
            )
        if not can_transition:
            return error_response(
                message='无权进行状态流转操作', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        status_note = str(
            request.data.get('status_note', request.data.get('note', '')) or ''
        ).strip()
        reason_required_statuses = {
            IntellectualPropertyApplication.Status.PAUSED,
            IntellectualPropertyApplication.Status.TERMINATED,
            IntellectualPropertyApplication.Status.DEFERRED,
        }
        if target_status in reason_required_statuses and not status_note:
            return error_response(message='暂停、终止或延期时必须填写状态说明')

        success, result = ip_service.transition_status(
            application=application,
            target_status=target_status,
            user=user,
            status_note=status_note,
        )

        if not success:
            return error_response(message=result)

        return success_response(
            IPApplicationDetailSerializer(result).data,
            message='状态流转成功',
        )

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        成果归档
        POST /api/v1/intellectual-property/applications/{id}/archive/
        """
        application = self.get_object()
        # 权限校验：老师/管理员
        if request.user.global_role not in ['sys_admin', 'teacher']:
            return error_response(
                message='仅老师/管理员可执行归档操作', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        success, result = ip_service.archive_application(
            application=application,
            user=request.user,
        )

        if not success:
            return error_response(message=result)

        return success_response(
            IPApplicationDetailSerializer(result).data,
            message='成果归档成功',
        )

    @action(detail=True, methods=['post'])
    def sync_contribution(self, request, pk=None):
        """
        同步贡献记录
        POST /api/v1/intellectual-property/applications/{id}/sync_contribution/
        """
        application = self.get_object()
        # 权限校验：项目负责人/老师/管理员
        user = request.user
        can_sync = (
            user.global_role in ['sys_admin', 'teacher'] or
            _is_application_leader_or_privileged(user, application)
        )
        if not can_sync:
            return error_response(
                message='无权同步贡献记录', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        success, result = ip_service.sync_contribution(
            application=application,
            user=user,
        )

        if not success:
            return error_response(message=result)

        return success_response(
            {'synced_count': result},
            message=f'成功同步{result}条贡献记录',
        )

    @action(detail=False, methods=['get'])
    def my_todo(self, request):
        """
        待我处理的知识产权申请
        GET /api/v1/intellectual-property/applications/my_todo/
        根据当前用户在申请中的角色及申请状态，返回需要处理的申请列表
        """
        user = request.user
        # 构建查询条件：当前用户需处理的申请
        queryset = self.filter_queryset(self.get_queryset()).filter(
            # 主导撰写人 - 材料撰写中
            Q(main_writer=user, status='writing') |
            # 项目负责人审核 - 审核中
            Q(project_reviewer=user, status='leader_review') |
            Q(related_project__leader=user, status='leader_review') |
            # 老师确认 - 确认中
            Q(teacher_confirmer=user, status='teacher_confirm') |
            # 申请执行人 - 退回修改中
            Q(applicant_executor=user, status__in=['returned', 'modifying']) |
            # 主导撰写人 - 退回修改中
            Q(main_writer=user, status__in=['returned', 'modifying'])
        )

        # 系统管理员/老师可见所有待处理（科研处审核中）
        if user.global_role in ['sys_admin', 'teacher']:
            queryset = self.filter_queryset(self.get_queryset()).filter(
                Q(main_writer=user, status='writing') |
                Q(project_reviewer=user, status='leader_review') |
                Q(related_project__leader=user, status='leader_review') |
                Q(status='teacher_confirm') |
                Q(applicant_executor=user, status__in=['returned', 'modifying']) |
                Q(main_writer=user, status__in=['returned', 'modifying']) |
                Q(status='research_office_review')
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = IPApplicationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = IPApplicationListSerializer(queryset, many=True)
        return success_response(serializer.data)

    @action(detail=True, methods=['get', 'post', 'patch', 'delete'])
    def candidates(self, request, pk=None):
        """维护拟申报及正式提交名单，不返回身份证等敏感明文。"""
        application = self.get_object()
        if request.method == 'GET':
            records = application.candidates.select_related(
                'user', 'checked_by',
            ).all()
            return success_response(
                IPApplicationCandidateSerializer(
                    records,
                    many=True,
                    context={'request': request},
                ).data
            )

        if not _is_application_leader_or_privileged(request.user, application):
            return error_response(
                message='仅项目负责人或指定老师可维护拟申报名单',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == 'POST':
            data = request.data.copy()
            data['application'] = application.id
            serializer = IPApplicationCandidateSerializer(
                data=data,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            candidate = serializer.save()
            return success_response(
                IPApplicationCandidateSerializer(
                    candidate,
                    context={'request': request},
                ).data,
                message='拟申报成员已添加',
                http_status=status.HTTP_201_CREATED,
            )

        candidate_id = request.data.get('candidate_id') or request.query_params.get(
            'candidate_id'
        )
        candidate = application.candidates.filter(pk=candidate_id).first()
        if candidate is None:
            return error_response(
                message='拟申报名单记录不存在',
                code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        if request.method == 'PATCH':
            data = request.data.copy()
            data.pop('candidate_id', None)
            serializer = IPApplicationCandidateSerializer(
                candidate,
                data=data,
                partial=True,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            candidate = serializer.save()
            if 'identity_check_status' in serializer.validated_data:
                candidate.checked_by = request.user
                candidate.checked_at = timezone.now()
                candidate.save(update_fields=['checked_by', 'checked_at', 'updated_at'])
            return success_response(
                IPApplicationCandidateSerializer(
                    candidate,
                    context={'request': request},
                ).data,
                message='拟申报名单已更新',
            )

        candidate.delete()
        return success_response(message='拟申报成员已移除')


class IPContributorViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    责任分工管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create: 项目负责人/老师/管理员
    - update: 项目负责人/老师/管理员
    - destroy: 项目负责人/老师/管理员
    """
    queryset = IPApplicationContributor.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': IPApplicationContributorSerializer,
        'retrieve': IPApplicationContributorSerializer,
        'create': IPApplicationContributorSerializer,
        'update': IPApplicationContributorSerializer,
        'partial_update': IPApplicationContributorSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdminForIP],
        'update': [IsProjectLeaderOrTeacherOrAdminForIP],
        'partial_update': [IsProjectLeaderOrTeacherOrAdminForIP],
        'destroy': [IsProjectLeaderOrTeacherOrAdminForIP],
        'confirm': [IsAuthenticated],
    }

    filterset_fields = ['application', 'user', 'role', 'is_confirmed']
    search_fields = ['application__title', 'user__name', 'contribution_description']
    ordering_fields = ['created_at', 'confirmed_at']

    def get_queryset(self):
        return super().get_queryset().select_related(
            'application__related_project', 'user', 'confirmed_by'
        ).filter(
            application__in=accessible_ip_applications(self.request.user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        """创建责任分工记录"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contributor = serializer.save()
        return success_response(
            IPApplicationContributorSerializer(contributor).data,
            message='责任分工记录创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新责任分工记录"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        contributor = serializer.save()
        return success_response(
            IPApplicationContributorSerializer(contributor).data,
            message='责任分工记录更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除责任分工记录"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='责任分工记录删除成功')

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """由贡献本人确认责任分工；重复调用保持幂等。"""
        contributor = self.get_object()
        if contributor.user_id != request.user.id:
            return error_response(
                message='仅贡献本人可确认责任分工', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if not contributor.is_confirmed:
            contributor.is_confirmed = True
            contributor.confirmed_by = request.user
            contributor.confirmed_at = timezone.now()
            contributor.save(update_fields=[
                'is_confirmed', 'confirmed_by', 'confirmed_at'
            ])

        return success_response(
            IPApplicationContributorSerializer(contributor).data,
            message='责任分工确认成功',
        )


class IPReturnRecordViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    退回记录管理 ViewSet
    - list/retrieve: 所有认证用户可查看（项目成员可见完整字段）
    - create: 申请执行人/项目负责人/老师/管理员
    - resolve: POST 完成退回修改
    """
    queryset = IPReturnRecord.objects.all().order_by('-return_time')

    serializer_classes_by_action = {
        'list': IPReturnRecordSerializer,
        'retrieve': IPReturnRecordSerializer,
        'create': IPReturnRecordCreateSerializer,
        'update': IPReturnRecordSerializer,
        'partial_update': IPReturnRecordSerializer,
        'resolve': IPReturnResolveSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'update': [IsProjectLeaderOrTeacherOrAdminForIP],
        'partial_update': [IsProjectLeaderOrTeacherOrAdminForIP],
        'destroy': [IsProjectLeaderOrTeacherOrAdminForIP],
        'resolve': [IsReturnModifier],
    }

    filterset_fields = ['application', 'return_source', 'responsibility_type',
                        'result', 'responsible_user']
    search_fields = ['application__title', 'return_reason', 'modify_description']
    ordering_fields = ['return_time', 'created_at', 'modify_deadline']

    def get_queryset(self):
        return super().get_queryset().select_related(
            'application__related_project', 'responsible_user', 'assigned_by',
            'actual_modifier', 'proof_file',
        ).filter(
            application__in=accessible_ip_applications(self.request.user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        """创建退回记录"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.validated_data.get('application')

        # 权限校验：申请执行人/项目负责人/老师/管理员可创建退回记录
        user = request.user
        can_create = (
            user.global_role in ['sys_admin', 'teacher'] or
            (application and application.applicant_executor_id == user.id) or
            (application and application.related_project and
             application.related_project.leader_id == user.id)
        )
        if not can_create:
            return error_response(
                message='无权创建退回记录', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        # 通过服务层创建退回记录（包含状态更新和日志记录）
        success, result = ip_service.create_return_record(
            application=application,
            data=serializer.validated_data,
            user=user,
        )

        if not success:
            return error_response(message=result)

        return success_response(
            IPReturnRecordSerializer(result).data,
            message='退回记录创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        完成退回修改
        POST /api/v1/intellectual-property/returns/{id}/resolve/
        body: {"modify_description": "修改说明", "result": "modified"}
        """
        return_record = self.get_object()
        self.check_object_permissions(request, return_record)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success, result_obj = ip_service.resolve_return_record(
            return_record=return_record,
            data=serializer.validated_data,
            user=request.user,
        )

        if not success:
            return error_response(message=result_obj)

        return success_response(
            IPReturnRecordSerializer(result_obj).data,
            message='退回修改已完成',
        )


class IPMaterialVersionViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    材料版本管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create: 项目成员（认证用户）
    - update/partial_update: 上传人/老师/管理员
    - destroy: 老师/管理员
    """
    queryset = IPMaterialVersion.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': IPMaterialVersionSerializer,
        'retrieve': IPMaterialVersionSerializer,
        'create': IPMaterialVersionCreateSerializer,
        'update': IPMaterialVersionSerializer,
        'partial_update': IPMaterialVersionSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsIPProjectMember],
        'update': [IsMainWriterOrExecutor],
        'partial_update': [IsMainWriterOrExecutor],
        'destroy': [IsTeacherOrAdmin],
    }

    filterset_fields = ['application', 'material_type', 'uploaded_by', 'is_final']
    search_fields = ['application__title', 'change_note']
    ordering_fields = ['created_at', 'version']

    def get_queryset(self):
        return super().get_queryset().select_related(
            'application__related_project', 'file_asset', 'uploaded_by',
            'related_return_record',
        ).filter(
            application__in=accessible_ip_applications(self.request.user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        """创建材料版本"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 自动设置上传人
        material = serializer.save(uploaded_by=request.user)
        return success_response(
            IPMaterialVersionSerializer(material).data,
            message='材料版本创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新材料版本"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        material = serializer.save()
        return success_response(
            IPMaterialVersionSerializer(material).data,
            message='材料版本更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除材料版本"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='材料版本删除成功')


class IPObjectionViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    异议管理 ViewSet
    - list/retrieve: 所有认证用户可查看（项目成员可见）
    - create: 项目成员（认证用户）
    - review: PATCH 处理异议（项目负责人初审/老师最终确认）
    - destroy: 老师/管理员
    """
    queryset = IPObjection.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': IPObjectionSerializer,
        'retrieve': IPObjectionSerializer,
        'create': IPObjectionCreateSerializer,
        'update': IPObjectionSerializer,
        'partial_update': IPObjectionSerializer,
        'review': IPObjectionReviewSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsIPProjectMember],
        'update': [IsProjectLeaderOrTeacherOrAdminForIP],
        'partial_update': [IsProjectLeaderOrTeacherOrAdminForIP],
        'destroy': [IsTeacherOrAdmin],
        'review': [IsAuthenticated],
    }

    filterset_fields = ['application', 'objection_type', 'status', 'objector']
    search_fields = ['application__title', 'content', 'final_result']
    ordering_fields = ['created_at', 'updated_at']

    def get_queryset(self):
        return super().get_queryset().select_related(
            'application__related_project', 'objector', 'proof_file',
            'leader_reviewer', 'teacher_confirmer',
        ).filter(
            application__in=accessible_ip_applications(self.request.user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        """创建异议"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objection = serializer.save()
        return success_response(
            IPObjectionSerializer(objection).data,
            message='异议创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['patch'])
    def review(self, request, pk=None):
        """
        处理异议
        PATCH /api/v1/intellectual-property/objections/{id}/review/
        body: {
            "action": "leader_review",  # 或 "teacher_confirm"
            "leader_opinion": "负责人意见",
            "teacher_opinion": "老师意见",
            "final_result": "最终结果",
            "final_status": "resolved"  # teacher_confirm 时必填: resolved/rejected
        }
        """
        objection = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        action_type = validated_data.get('action')
        user = request.user

        # 负责人初审
        if action_type == 'leader_review':
            # 权限校验：项目负责人/老师/管理员
            can_review = (
                user.global_role in ['sys_admin', 'teacher'] or
                (objection.application.related_project and
                 objection.application.related_project.leader_id == user.id)
            )
            if not can_review:
                return error_response(
                    message='无权进行负责人初审', code=1003,
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            # 校验当前状态必须为待处理
            if objection.status != IPObjection.ObjectionStatus.PENDING:
                return error_response(message='该异议已初审，无法重复初审')

            objection.leader_opinion = validated_data.get('leader_opinion', '')
            objection.leader_reviewer = user
            objection.leader_reviewed_at = timezone.now()
            objection.status = IPObjection.ObjectionStatus.LEADER_REVIEWED
            objection.save()

        # 老师最终确认
        elif action_type == 'teacher_confirm':
            # 权限校验：老师/管理员
            if user.global_role not in ['sys_admin', 'teacher']:
                return error_response(
                    message='仅老师/管理员可进行最终确认', code=1003,
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            # 校验当前状态必须为负责人已初审
            if objection.status != IPObjection.ObjectionStatus.LEADER_REVIEWED:
                return error_response(message='该异议需先经负责人初审')

            final_status = validated_data.get('final_status')
            objection.teacher_opinion = validated_data.get('teacher_opinion', '')
            objection.teacher_confirmer = user
            objection.teacher_confirmed_at = timezone.now()
            objection.final_result = validated_data.get('final_result', '')
            # 根据最终状态设置异议状态
            if final_status == 'resolved':
                objection.status = IPObjection.ObjectionStatus.RESOLVED
            else:
                objection.status = IPObjection.ObjectionStatus.REJECTED
            objection.save()

        # 写操作日志
        from .services import log_operation
        log_operation(
            user=user,
            action=f'异议处理-{action_type}',
            obj=objection,
            detail=f'异议#{objection.id}，状态: {objection.get_status_display()}',
        )

        return success_response(
            IPObjectionSerializer(objection).data,
            message='异议处理成功',
        )
