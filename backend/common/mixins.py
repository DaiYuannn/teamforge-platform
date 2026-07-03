"""
视图 Mixin 集合
提供常用的可复用混入行为
"""
from rest_framework.permissions import IsAuthenticated, AllowAny


class IsAuthenticatedOrCreateMixin:
    """
    认证或创建 Mixin
    - 创建操作（POST）允许任何用户访问（如注册）
    - 其他操作需要认证
    """
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]


class MultiPermissionMixin:
    """
    多权限 Mixin
    子类通过 permission_classes_by_action 字典为不同 action 配置不同权限
    示例:
        permission_classes_by_action = {
            'list': [IsAuthenticated],
            'create': [IsTeacherOrAdmin],
            'update': [IsTeacherOrAdmin],
            'destroy': [IsSysAdmin],
        }
    """
    permission_classes_by_action = {}

    def get_permissions(self):
        # 优先使用 action 级别配置
        if self.action in self.permission_classes_by_action:
            return [perm() for perm in self.permission_classes_by_action[self.action]]
        # 回退到类级别配置
        return super().get_permissions()


class MultiSerializerMixin:
    """
    多序列化器 Mixin
    子类通过 serializer_classes_by_action 字典为不同 action 配置不同序列化器
    示例:
        serializer_classes_by_action = {
            'list': ProjectListSerializer,
            'create': ProjectCreateSerializer,
            'retrieve': ProjectSerializer,
        }
    """
    serializer_classes_by_action = {}

    def get_serializer_class(self):
        # 优先使用 action 级别配置
        if self.action in self.serializer_classes_by_action:
            return self.serializer_classes_by_action[self.action]
        # 回退到类级别配置
        return super().get_serializer_class()
