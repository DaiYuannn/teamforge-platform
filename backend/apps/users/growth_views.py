"""
成员成长记录视图
- MemberGrowthViewSet: 成员成长记录 CRUD
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsTeacherOrAdmin
from .growth_models import MemberGrowth
from .growth_serializers import MemberGrowthSerializer


class MemberGrowthViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    成员成长记录管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 老师或管理员
    """
    queryset = MemberGrowth.objects.all().order_by('-period')

    serializer_classes_by_action = {
        'list': MemberGrowthSerializer,
        'retrieve': MemberGrowthSerializer,
        'create': MemberGrowthSerializer,
        'update': MemberGrowthSerializer,
        'partial_update': MemberGrowthSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsTeacherOrAdmin],
        'update': [IsTeacherOrAdmin],
        'partial_update': [IsTeacherOrAdmin],
        'destroy': [IsTeacherOrAdmin],
    }

    filterset_fields = ['user', 'period']
    search_fields = ['user__name', 'notes']
    ordering_fields = ['period', 'contribution_score', 'task_count']

    def create(self, request, *args, **kwargs):
        """创建成长记录"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        growth = serializer.save()
        return success_response(
            MemberGrowthSerializer(growth).data,
            message='成长记录创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新成长记录"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        growth = serializer.save()
        return success_response(MemberGrowthSerializer(growth).data, message='成长记录更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除成长记录"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='成长记录删除成功')
