"""
项目风险视图
- ProjectRiskViewSet: 风险 CRUD + 解决
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from common.project_access import scope_project_queryset, user_can_access_project
from .risk_models import ProjectRisk
from .risk_serializers import ProjectRiskSerializer


class ProjectRiskViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    项目风险管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 项目负责人/老师/管理员
    - resolve: 关闭风险
    """
    queryset = ProjectRisk.objects.all().order_by('-level', '-identified_at')

    serializer_classes_by_action = {
        'list': ProjectRiskSerializer,
        'retrieve': ProjectRiskSerializer,
        'create': ProjectRiskSerializer,
        'update': ProjectRiskSerializer,
        'partial_update': ProjectRiskSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
        'resolve': [IsProjectLeaderOrTeacherOrAdmin],
    }

    filterset_fields = ['project', 'level', 'status', 'identified_by']
    search_fields = ['title', 'description', 'project__name']
    ordering_fields = ['level', 'status', 'identified_at']

    def get_queryset(self):
        return scope_project_queryset(
            super().get_queryset(),
            self.request.user,
            project_lookup='project',
        )

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        write = request.method not in ('GET', 'HEAD', 'OPTIONS')
        if not user_can_access_project(request.user, obj.project, write=write):
            self.permission_denied(request, message='无权访问该项目风险')

    def create(self, request, *args, **kwargs):
        """创建风险，自动设置识别人为当前用户"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        risk = serializer.save(identified_by=request.user)
        return success_response(
            ProjectRiskSerializer(risk).data,
            message='风险创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新风险"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        risk = serializer.save()
        return success_response(ProjectRiskSerializer(risk).data, message='风险更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除风险"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='风险已删除')

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        关闭风险
        POST /api/v1/projects/risks/{id}/resolve/
        """
        risk = self.get_object()
        self.check_object_permissions(request, risk)
        if risk.status == ProjectRisk.Status.CLOSED:
            return error_response(message='该风险已关闭')
        risk.resolve()
        return success_response(ProjectRiskSerializer(risk).data, message='风险已关闭')
