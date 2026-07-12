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

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from .models import Project, ProjectMember, ProjectStageLog
from .serializers import (
    ProjectSerializer, ProjectListSerializer, ProjectCreateSerializer,
    ProjectMemberSerializer, ProjectStageLogSerializer,
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
        'stage_logs': [IsAuthenticated],
    }

    filterset_fields = ['status', 'priority', 'current_stage', 'leader']
    search_fields = ['name', 'code', 'intro']
    ordering_fields = [
        'created_at', 'updated_at', 'name', 'status', 'priority',
        'start_date', 'planned_end_date', 'archived_at',
    ]

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

    @action(detail=True, methods=['get', 'post', 'delete'])
    def members(self, request, pk=None):
        """
        项目成员管理
        GET /api/v1/projects/{id}/members/ - 获取成员列表
        POST /api/v1/projects/{id}/members/ - 添加成员 {"user_id": 1, "role_in_project": "core"}
        DELETE /api/v1/projects/{id}/members/?user_id=1 - 移除成员
        """
        project = self.get_object()

        if request.method == 'GET':
            members = project.members.all()
            serializer = ProjectMemberSerializer(members, many=True)
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

            success, result = project_service.add_member(project, user, role_in_project)
            if not success:
                return error_response(message=result)

            return success_response(
                ProjectMemberSerializer(result).data,
                message='成员添加成功',
                http_status=status.HTTP_201_CREATED,
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

            success, message = project_service.remove_member(project, user)
            if not success:
                return error_response(message=message)

            return success_response(message=message)

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
    permission_classes = [IsAuthenticated]

    filterset_fields = ['project', 'user', 'role_in_project']
    search_fields = ['project__name', 'user__name', 'user__email']
