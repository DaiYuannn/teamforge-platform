"""
自定义角色序列化器与视图集
- CustomRoleViewSet: 角色 CRUD
- UserRoleAssignmentViewSet: 角色分配 CRUD
"""
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsSysAdminOrReadOnly
from .role_models import CustomRole, UserRoleAssignment


# ============ 序列化器 ============

class CustomRoleSerializer(serializers.ModelSerializer):
    """自定义角色序列化器"""

    class Meta:
        model = CustomRole
        fields = ('id', 'name', 'description', 'permissions', 'is_system', 'created_at')
        read_only_fields = ('id', 'is_system', 'created_at')


class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    """用户角色分配序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    role_name = serializers.CharField(source='role.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    assigned_by_name = serializers.CharField(source='assigned_by.name', read_only=True, default='')

    class Meta:
        model = UserRoleAssignment
        fields = (
            'id', 'user', 'user_name', 'role', 'role_name',
            'project', 'project_name', 'assigned_by', 'assigned_by_name',
            'created_at',
        )
        read_only_fields = ('id', 'created_at', 'assigned_by')
        extra_kwargs = {
            'project': {'required': False, 'allow_null': True},
        }
        # 移除自动生成的 UniqueTogetherValidator，
        # 因为它会导致 project 字段变成必填（即使 model 允许 null）
        # 唯一性检查改为在 validate() 中手动处理
        validators = []

    def validate(self, attrs):
        """手动检查 (user, role, project) 唯一性"""
        user = attrs.get('user')
        role = attrs.get('role')
        project = attrs.get('project')

        # 如果是更新操作，获取当前实例的值作为默认值
        if self.instance:
            user = user or self.instance.user
            role = role or self.instance.role
            project = attrs.get('project', self.instance.project)

        # 检查唯一性
        qs = UserRoleAssignment.objects.filter(user=user, role=role, project=project)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                '该用户已分配此角色' + ('（当前项目）' if project else '（全局）')
            )
        return attrs


# ============ ViewSet ============

class CustomRoleViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    自定义角色管理 ViewSet
    - 任何登录用户可查看
    - 仅系统管理员可创建/更新/删除
    - 系统角色不可删除
    """
    queryset = CustomRole.objects.all().order_by('name')
    serializer_class = CustomRoleSerializer
    serializer_classes_by_action = {
        'list': CustomRoleSerializer,
        'retrieve': CustomRoleSerializer,
        'create': CustomRoleSerializer,
        'update': CustomRoleSerializer,
        'partial_update': CustomRoleSerializer,
    }
    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsSysAdminOrReadOnly],
        'update': [IsSysAdminOrReadOnly],
        'partial_update': [IsSysAdminOrReadOnly],
        'destroy': [IsSysAdminOrReadOnly],
    }
    filterset_fields = ['is_system']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        return success_response(
            CustomRoleSerializer(role).data,
            message='角色创建成功',
            http_status=201,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        return success_response(CustomRoleSerializer(role).data, message='角色更新成功')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return error_response(message='系统角色不可删除', code=2101)
        instance.delete()
        return success_response(message='角色删除成功')


class UserRoleAssignmentViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    用户角色分配 ViewSet
    - 任何登录用户可查看
    - 仅系统管理员可分配/修改/撤销
    """
    queryset = UserRoleAssignment.objects.all().order_by('-created_at')
    serializer_class = UserRoleAssignmentSerializer
    serializer_classes_by_action = {
        'list': UserRoleAssignmentSerializer,
        'retrieve': UserRoleAssignmentSerializer,
        'create': UserRoleAssignmentSerializer,
        'update': UserRoleAssignmentSerializer,
        'partial_update': UserRoleAssignmentSerializer,
    }
    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsSysAdminOrReadOnly],
        'update': [IsSysAdminOrReadOnly],
        'partial_update': [IsSysAdminOrReadOnly],
        'destroy': [IsSysAdminOrReadOnly],
    }
    filterset_fields = ['user', 'role', 'project']
    ordering_fields = ['created_at']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(assigned_by=request.user)
        return success_response(
            UserRoleAssignmentSerializer(assignment).data,
            message='角色分配成功',
            http_status=201,
        )
