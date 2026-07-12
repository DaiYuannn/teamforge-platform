"""
项目里程碑视图
- MilestoneViewSet: 里程碑 CRUD + 完成/取消完成
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from .milestone_models import Milestone
from .milestone_serializers import MilestoneSerializer


class MilestoneViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    项目里程碑管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 项目负责人/老师/管理员
    - toggle: 切换完成状态
    """
    queryset = Milestone.objects.all().order_by('sort_order', 'due_date')

    serializer_classes_by_action = {
        'list': MilestoneSerializer,
        'retrieve': MilestoneSerializer,
        'create': MilestoneSerializer,
        'update': MilestoneSerializer,
        'partial_update': MilestoneSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsProjectLeaderOrTeacherOrAdmin],
        'partial_update': [IsProjectLeaderOrTeacherOrAdmin],
        'destroy': [IsProjectLeaderOrTeacherOrAdmin],
        'toggle': [IsAuthenticated],
    }

    filterset_fields = ['project', 'is_completed']
    search_fields = ['title', 'description', 'project__name']
    ordering_fields = ['sort_order', 'due_date', 'created_at']

    def create(self, request, *args, **kwargs):
        """创建里程碑"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        milestone = serializer.save()
        return success_response(
            MilestoneSerializer(milestone).data,
            message='里程碑创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新里程碑"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        milestone = serializer.save()
        return success_response(MilestoneSerializer(milestone).data, message='里程碑更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除里程碑"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='里程碑已删除')

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """
        切换里程碑完成状态
        POST /api/v1/projects/milestones/{id}/toggle/
        """
        milestone = self.get_object()
        if milestone.is_completed:
            milestone.mark_incomplete()
            message = '里程碑已标记为未完成'
        else:
            milestone.mark_completed()
            message = '里程碑已完成'
        return success_response(MilestoneSerializer(milestone).data, message=message)
