"""
RBAC 权限基类模块
基于角色的访问控制，所有权限必须真实校验
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


PERMISSION_PREFIX_BY_PATH = {
    'projects': 'project',
    'tasks': 'task',
    'finance': 'finance',
    'exports': 'report',
    'reports': 'report',
    'members': 'member',
    'users': 'member',
}


def permission_code_for_request(request, view=None, action=None):
    """Map a business API path to the permission codes exposed by the role UI."""
    parts = [part for part in request.path.split('/') if part]
    try:
        api_index = parts.index('v1')
        resource = parts[api_index + 1]
    except (ValueError, IndexError):
        resource = parts[0] if parts else ''
    prefix = PERMISSION_PREFIX_BY_PATH.get(resource)
    if action is None:
        action = 'create' if getattr(view, 'action', '') == 'create' else 'manage'
    return f'{prefix}.{action}' if prefix else ''


def _project_id_from(value):
    if value is None:
        return None
    project = value if hasattr(value, 'leader_id') else getattr(value, 'project', None)
    if project is not None:
        return getattr(project, 'pk', None)
    return getattr(value, 'project_id', None)


def request_project_id(request):
    """Resolve the target project without trusting it as an authorization result."""
    data = getattr(request, 'data', None)
    if hasattr(data, 'get'):
        value = data.get('project') or data.get('project_id')
        if value not in (None, ''):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def user_has_custom_permission(user, code, *, project_id=None, allow_project_scoped=False):
    """Return whether an active assignment grants ``code`` globally or in a project."""
    if not code or not user or not getattr(user, 'is_authenticated', False):
        return False
    try:
        normalized_project_id = int(project_id) if project_id is not None else None
    except (TypeError, ValueError):
        normalized_project_id = None
    assignments = user.role_assignments.select_related('role').only(
        'project_id', 'role__permissions',
    )
    for assignment in assignments:
        if code not in (assignment.role.permissions or []):
            continue
        if assignment.project_id is None:
            return True
        if normalized_project_id is not None and assignment.project_id == normalized_project_id:
            return True
        if normalized_project_id is None and allow_project_scoped:
            return True
    return False


class RolePermission(BasePermission):
    """
    RBAC 权限基类
    子类需设置 required_roles 属性来限定允许访问的角色
    """

    # 允许访问的角色列表，子类覆盖
    required_roles = []

    def has_permission(self, request, view):
        # 未登录直接拒绝
        if not request.user or not request.user.is_authenticated:
            return False

        # 如果未设置 required_roles，则只需认证即可
        if not self.required_roles:
            return True

        # 检查用户全局角色是否在允许列表中
        return request.user.global_role in self.required_roles

    def has_object_permission(self, request, view, obj):
        # 默认调用 has_permission
        return self.has_permission(request, view)


class IsSysAdmin(RolePermission):
    """系统管理员权限"""
    required_roles = ['sys_admin']


class IsSysAdminOrReadOnly(BasePermission):
    """系统管理员可写，其他认证用户只读"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.global_role == 'sys_admin'

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsTeacher(RolePermission):
    """老师权限"""
    required_roles = ['teacher']


class IsTeacherOrAdmin(RolePermission):
    """老师或管理员权限"""
    required_roles = ['teacher', 'sys_admin']

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        code = permission_code_for_request(request, view)
        return user_has_custom_permission(
            request.user,
            code,
            project_id=request_project_id(request),
            allow_project_scoped=request_project_id(request) is None,
        )

    def has_object_permission(self, request, view, obj):
        if request.user.global_role in self.required_roles:
            return True
        return user_has_custom_permission(
            request.user,
            permission_code_for_request(request, view),
            project_id=_project_id_from(obj),
        )


class IsTeacherOrAdminOrReadOnly(BasePermission):
    """老师/管理员可维护，其他已认证内部用户只读。"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.global_role in ['teacher', 'sys_admin']

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsInternalTeamMember(BasePermission):
    """当前在队/暂离的内部成员；明确排除外部协作者与已离队账号。"""

    allowed_membership_statuses = {'active', 'on_leave'}

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'is_active', False)
            and getattr(user, 'membership_status', 'active')
            in self.allowed_membership_statuses
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsSensitiveApprover(RolePermission):
    """敏感资料审批人权限"""
    required_roles = ['sens_approver', 'sys_admin']


class IsProjectLeaderOrTeacherOrAdmin(BasePermission):
    """
    项目负责人 / 老师 / 管理员权限
    对象级权限：检查当前用户是否为该项目的负责人，或全局角色为老师/管理员
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # list / retrieve 等安全方法对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        if request.user.global_role in ['teacher', 'sys_admin']:
            return True
        code = permission_code_for_request(request, view)
        project_id = request_project_id(request)
        if user_has_custom_permission(
            request.user,
            code,
            project_id=project_id,
            allow_project_scoped=project_id is None,
        ):
            return True
        # 创建时尚无对象可供 DRF 校验，直接核对请求中的所属项目。
        if getattr(view, 'action', None) == 'create':
            project_id = request.data.get('project')
            if not project_id:
                return False
            from apps.projects.models import Project
            return Project.objects.filter(pk=project_id, leader=request.user).exists()
        # 更新、删除和自定义详情动作继续交由对象级权限判断。
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 读取对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        # 系统管理员可以操作任何项目
        if request.user.global_role == 'sys_admin':
            return True
        # 老师可以操作任何项目
        if request.user.global_role == 'teacher':
            return True
        if user_has_custom_permission(
            request.user,
            permission_code_for_request(request, view),
            project_id=_project_id_from(obj),
        ):
            return True
        # 项目负责人不能借更新操作把对象转移到自己不负责的项目。
        requested_project_id = request.data.get('project') if hasattr(request.data, 'get') else None
        if requested_project_id:
            from apps.projects.models import Project
            if not Project.objects.filter(pk=requested_project_id, leader=request.user).exists():
                return False
        # 项目负责人可以操作自己的项目
        if hasattr(obj, 'leader'):
            return obj.leader_id == request.user.id
        # 如果是项目成员对象，检查其关联项目
        if hasattr(obj, 'project') and hasattr(obj.project, 'leader'):
            return obj.project.leader_id == request.user.id
        return False


class IsOwnerOrAdmin(BasePermission):
    """数据拥有者或管理员权限"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 管理员可访问
        if request.user.global_role == 'sys_admin':
            return True
        # 数据拥有者可访问
        if hasattr(obj, 'user'):
            return obj.user_id == request.user.id
        if hasattr(obj, 'creator'):
            return obj.creator_id == request.user.id
        if hasattr(obj, 'uploader'):
            return obj.uploader_id == request.user.id
        return False


class IsProjectMember(BasePermission):
    """项目成员权限（用于文件等资源访问）"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 管理员可访问
        if request.user.global_role == 'sys_admin':
            return True
        # 老师可访问
        if request.user.global_role == 'teacher':
            return True
        # 获取关联的项目
        project = getattr(obj, 'project', None)
        if project is None:
            return False
        # 项目负责人
        if project.leader_id == request.user.id:
            return True
        # 项目成员
        from apps.projects.models import ProjectMember
        return ProjectMember.objects.filter(
            project=project, user=request.user, status=ProjectMember.Status.ACTIVE
        ).exists()
