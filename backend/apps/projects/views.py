"""
项目视图
- ProjectViewSet: 项目 CRUD + 阶段推进 + 负责人打卡 + 成员管理
- ProjectMemberViewSet: 项目成员管理
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsInternalTeamMember
from common.project_access import is_external_collaborator, scope_project_queryset
from .models import Project, ProjectMember, ProjectMembershipEvent, ProjectStageLog
from .serializers import (
    ProjectSerializer, ProjectListSerializer, ProjectCreateSerializer,
    ProjectMemberSerializer, ProjectMembershipEventSerializer, ProjectStageLogSerializer,
)
from .permissions import IsProjectLeaderOrTeacherOrAdmin, IsProjectLeader
from .services import project_service
from apps.users.models import User


class ProjectViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    项目管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 老师/管理员/项目负责人
    - stage: POST 推进阶段（项目负责人/老师/管理员）
    - leader_update: POST 负责人打卡更新
    - members: GET/POST 项目成员管理
    """
    queryset = Project.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': ProjectListSerializer,
        'retrieve': ProjectSerializer,
        'create': ProjectCreateSerializer,
        'update': ProjectSerializer,
        'partial_update': ProjectSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
        'stage': [IsProjectLeader],
        'leader_update': [IsProjectLeader],
        'members': [IsAuthenticated],
        'membership_history': [IsInternalTeamMember],
        'stage_logs': [IsAuthenticated],
    }

    filterset_fields = ['status', 'priority', 'current_stage', 'leader']
    search_fields = ['name', 'code', 'intro']
    ordering_fields = [
        'created_at', 'updated_at', 'name', 'status', 'priority',
        'start_date', 'planned_end_date', 'archived_at',
    ]

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related('leader')
            .annotate(
                active_member_count=Count(
                    'members',
                    filter=Q(members__status=ProjectMember.Status.ACTIVE),
                    distinct=True,
                ),
                task_count=Count('tasks', distinct=True),
                competition_count=Count('competitions', distinct=True),
            )
        )
        user = self.request.user
        if getattr(user, 'membership_status', '') == User.MembershipStatus.EXTERNAL:
            queryset = queryset.filter(
                members__user=user,
                members__status=ProjectMember.Status.ACTIVE,
            )
        else:
            queryset = queryset.prefetch_related('budgets')
        if self.request.query_params.get('scope') == 'mine':
            queryset = queryset.filter(
                Q(leader=user)
                | Q(
                    members__user=user,
                    members__status=ProjectMember.Status.ACTIVE,
                )
            )
        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        """创建项目"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        return success_response(
            ProjectSerializer(project).data,
            message='项目创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新项目"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # 权限校验
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        return success_response(ProjectSerializer(project).data, message='项目更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除项目（软删除，移入回收站）"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        self.perform_destroy(instance)
        return success_response(message='项目已移入回收站')

    def perform_destroy(self, instance):
        """软删除而非物理删除，可通过回收站恢复"""
        instance.soft_delete(getattr(self.request, 'user', None))

    @action(detail=True, methods=['post'])
    def stage(self, request, pk=None):
        """
        推进项目阶段
        POST /api/v1/projects/{id}/stage/
        body: {"to_stage": 3, "note": "进入材料准备阶段"}
        """
        project = self.get_object()
        self.check_object_permissions(request, project)

        to_stage = request.data.get('to_stage')
        note = request.data.get('note', '')

        if to_stage is None:
            return error_response(message='请指定目标阶段 to_stage')

        try:
            to_stage = int(to_stage)
        except (ValueError, TypeError):
            return error_response(message='to_stage 必须是整数')

        success, result = project_service.advance_stage(
            project=project,
            to_stage=to_stage,
            operator=request.user,
            note=note,
        )

        if not success:
            return error_response(message=result)

        return success_response(
            ProjectSerializer(result).data,
            message='阶段推进成功',
        )

    @action(detail=True, methods=['post'])
    def leader_update(self, request, pk=None):
        """
        项目负责人打卡更新
        POST /api/v1/projects/{id}/leader_update/
        body: {"note": "本周完成了xxx"}
        """
        project = self.get_object()
        self.check_object_permissions(request, project)

        note = request.data.get('note', '')

        success, result = project_service.leader_update(
            project=project,
            operator=request.user,
            note=note,
        )

        if not success:
            return error_response(message=result)

        return success_response(
            ProjectSerializer(result).data,
            message='打卡更新成功',
        )

    @action(detail=True, methods=['get', 'post', 'patch', 'delete'])
    def members(self, request, pk=None):
        """
        项目成员管理
        GET /api/v1/projects/{id}/members/ - 获取成员列表
        POST /api/v1/projects/{id}/members/ - 添加成员 {"user_id": 1, "role_in_project": "core"}
        DELETE /api/v1/projects/{id}/members/?user_id=1 - 移除成员
        """
        project = self.get_object()

        if request.method == 'GET':
            members = project.members.select_related('user', 'handover_to__user').all()
            if is_external_collaborator(request.user):
                members = members.filter(status=ProjectMember.Status.ACTIVE)
            member_status = request.query_params.get('status')
            if member_status:
                members = members.filter(status=member_status)
            serializer = ProjectMemberSerializer(
                members,
                many=True,
                context={'request': request},
            )
            return success_response(serializer.data)

        elif request.method == 'POST':
            # 仅项目负责人/老师/管理员可添加成员
            if not (project.leader_id == request.user.id or
                    request.user.global_role in ['sys_admin', 'teacher']):
                return error_response(message='权限不足', code=1003,
                                      http_status=status.HTTP_403_FORBIDDEN)

            user_id = request.data.get('user_id')
            role_in_project = request.data.get('role_in_project', 'participant')

            if not user_id:
                return error_response(message='请提供 user_id')

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return error_response(message='用户不存在', code=1004)

            if role_in_project not in ProjectMember.RoleInProject.values:
                return error_response(message='项目角色不合法', code=1001)

            success, result = project_service.add_member(
                project, user, role_in_project, operator=request.user
            )
            if not success:
                return error_response(message=result)

            return success_response(
                ProjectMemberSerializer(
                    result,
                    context={'request': request},
                ).data,
                message='成员添加成功',
                http_status=status.HTTP_201_CREATED,
            )

        elif request.method == 'PATCH':
            if not (project.leader_id == request.user.id or
                    request.user.global_role in ['sys_admin', 'teacher']):
                return error_response(message='权限不足', code=1003,
                                      http_status=status.HTTP_403_FORBIDDEN)
            member_id = request.data.get('member_id')
            user_id = request.data.get('user_id')
            member = project.members.filter(
                id=member_id
            ).first() if member_id else project.members.filter(user_id=user_id).first()
            if member is None:
                return error_response(message='项目成员不存在', code=1004)
            role_value = request.data.get('role_in_project')
            status_value = request.data.get('status')
            if role_value and role_value not in ProjectMember.RoleInProject.values:
                return error_response(message='项目角色不合法', code=1001)
            if status_value and status_value not in ProjectMember.Status.values:
                return error_response(message='成员状态不合法', code=1001)
            handover = None
            if request.data.get('handover_to'):
                handover = project.members.filter(
                    pk=request.data.get('handover_to'),
                    status=ProjectMember.Status.ACTIVE,
                ).first()
                if handover is None:
                    return error_response(message='交接人必须是同项目的活动成员', code=1001)
            if member.user_id == project.leader_id and status_value == ProjectMember.Status.EXITED:
                if not handover:
                    return error_response(message='项目负责人退出前必须指定交接成员', code=1001)
                project.leader = handover.user
                project.save(update_fields=['leader', 'updated_at'])
                handover.role_in_project = ProjectMember.RoleInProject.LEADER
                handover.save(update_fields=['role_in_project'])
            success, result = project_service.update_member(
                member,
                operator=request.user,
                role_in_project=role_value,
                status=status_value,
                reason=request.data.get('reason', ''),
                handover_to=handover,
                handover_notes=request.data.get('handover_notes', ''),
            )
            return success_response(
                ProjectMemberSerializer(
                    result,
                    context={'request': request},
                ).data,
                message='项目成员已更新',
            )

        elif request.method == 'DELETE':
            # 仅项目负责人/老师/管理员可移除成员
            if not (project.leader_id == request.user.id or
                    request.user.global_role in ['sys_admin', 'teacher']):
                return error_response(message='权限不足', code=1003,
                                      http_status=status.HTTP_403_FORBIDDEN)

            user_id = request.query_params.get('user_id')
            if not user_id:
                return error_response(message='请提供 user_id 参数')

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return error_response(message='用户不存在', code=1004)

            handover = None
            handover_id = request.data.get('handover_to') or request.query_params.get('handover_to')
            if handover_id:
                handover = project.members.filter(
                    pk=handover_id,
                    status=ProjectMember.Status.ACTIVE,
                ).first()
            success, message = project_service.remove_member(
                project,
                user,
                operator=request.user,
                reason=request.data.get('reason', '') or request.query_params.get('reason', ''),
                handover_to=handover,
                handover_notes=(
                    request.data.get('handover_notes', '')
                    or request.query_params.get('handover_notes', '')
                ),
            )
            if not success:
                return error_response(message=message)

            return success_response(message=message)

    @action(detail=True, methods=['get'], url_path='membership-history')
    def membership_history(self, request, pk=None):
        project = self.get_object()
        events = ProjectMembershipEvent.objects.filter(
            membership__project=project
        ).select_related('membership__user', 'operator', 'handover_to__user')
        user_id = request.query_params.get('user_id')
        if user_id:
            events = events.filter(membership__user_id=user_id)
        return success_response(ProjectMembershipEventSerializer(events, many=True).data)

    @action(detail=True, methods=['get'])
    def stage_logs(self, request, pk=None):
        """
        获取项目阶段变更日志
        GET /api/v1/projects/{id}/stage_logs/
        """
        project = self.get_object()
        logs = project.stage_logs.all()
        serializer = ProjectStageLogSerializer(logs, many=True)
        return success_response(serializer.data)


class ProjectMemberViewSet(ModelViewSet):
    """
    项目成员管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 项目负责人/老师/管理员
    """
    queryset = ProjectMember.objects.all().order_by('-joined_at')
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsProjectLeaderOrTeacherOrAdmin]

    filterset_fields = ['project', 'user', 'role_in_project', 'status']
    search_fields = ['project__name', 'user__name', 'user__email']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('project', 'user')
        queryset = scope_project_queryset(
            queryset,
            self.request.user,
            project_lookup='project',
        )
        if is_external_collaborator(self.request.user):
            queryset = queryset.filter(status=ProjectMember.Status.ACTIVE)
        return queryset

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        handover = serializer.validated_data.get('handover_to')
        success, member = project_service.update_member(
            instance,
            operator=request.user,
            role_in_project=serializer.validated_data.get('role_in_project'),
            status=serializer.validated_data.get('status'),
            reason=serializer.validated_data.get('exit_reason', ''),
            handover_to=handover,
            handover_notes=serializer.validated_data.get('handover_notes', ''),
        )
        return success_response(
            ProjectMemberSerializer(
                member,
                context={'request': request},
            ).data,
            message='项目成员已更新',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        success, message = project_service.remove_member(
            instance.project,
            instance.user,
            operator=request.user,
            reason=request.data.get('reason', ''),
            handover_to=instance.handover_to,
            handover_notes=request.data.get('handover_notes', ''),
        )
        if not success:
            return error_response(message=message)
        return success_response(message=message)
