"""
成员技能视图
- MemberSkillViewSet: 成员技能 CRUD
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsTeacherOrAdmin
from .skill_models import MemberSkill
from .skill_serializers import MemberSkillSerializer


class MemberSkillViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    成员技能管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 老师或管理员
    """
    queryset = MemberSkill.objects.all().order_by('-level', '-created_at')

    serializer_classes_by_action = {
        'list': MemberSkillSerializer,
        'retrieve': MemberSkillSerializer,
        'create': MemberSkillSerializer,
        'update': MemberSkillSerializer,
        'partial_update': MemberSkillSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsTeacherOrAdmin],
        'update': [IsTeacherOrAdmin],
        'partial_update': [IsTeacherOrAdmin],
        'destroy': [IsTeacherOrAdmin],
    }

    filterset_fields = ['user', 'name', 'certified']
    search_fields = ['name', 'user__name']
    ordering_fields = ['level', 'created_at']

    def create(self, request, *args, **kwargs):
        """创建技能"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill = serializer.save()
        return success_response(
            MemberSkillSerializer(skill).data,
            message='技能创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新技能"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        skill = serializer.save()
        return success_response(MemberSkillSerializer(skill).data, message='技能更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除技能"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='技能删除成功')
