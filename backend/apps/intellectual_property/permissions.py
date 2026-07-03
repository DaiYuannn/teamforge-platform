"""
知识产权管理权限
所有权限必须后端真实校验
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


def _get_application(obj):
    """
    从对象中获取关联的知识产权申请
    - 申请对象本身直接返回
    - 关联记录（contributor/return_record/material/objection）通过 application 字段获取
    """
    from .models import IntellectualPropertyApplication
    if isinstance(obj, IntellectualPropertyApplication):
        return obj
    return getattr(obj, 'application', None)


def _is_project_member(user, application):
    """
    判断用户是否为申请关联项目的成员（含项目负责人）
    - 管理员/老师直接通过
    - 无关联项目则返回 False
    """
    if user.global_role in ['sys_admin', 'teacher']:
        return True
    project = getattr(application, 'related_project', None)
    if project is None:
        return False
    # 项目负责人
    if project.leader_id == user.id:
        return True
    # 项目成员
    from apps.projects.models import ProjectMember
    return ProjectMember.objects.filter(project=project, user=user).exists()


class IsIPProjectMember(BasePermission):
    """
    知识产权申请关联项目成员权限
    - 读取：项目成员可见
    - 写操作：项目成员可操作
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 系统管理员/老师可访问所有
        if request.user.global_role in ['sys_admin', 'teacher']:
            return True
        application = _get_application(obj)
        if application is None:
            return False
        return _is_project_member(request.user, application)


class IsProjectLeaderOrTeacherOrAdminForIP(BasePermission):
    """
    项目负责人 / 老师 / 管理员权限（知识产权专用）
    - 读取：所有认证用户
    - 写操作：老师/管理员/申请关联项目的负责人
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 安全方法对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        # 写操作需老师或管理员（对象级权限进一步校验项目负责人）
        return request.user.global_role in ['teacher', 'sys_admin']

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 读取对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        # 系统管理员
        if request.user.global_role == 'sys_admin':
            return True
        # 老师
        if request.user.global_role == 'teacher':
            return True
        # 申请关联项目的负责人
        application = _get_application(obj)
        if application is None:
            return False
        project = getattr(application, 'related_project', None)
        if project is not None and project.leader_id == request.user.id:
            return True
        return False


class IsMainWriterOrExecutor(BasePermission):
    """
    主导撰写人 / 申请执行人权限
    用于申请材料的维护操作
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 系统管理员/老师可操作
        if request.user.global_role in ['sys_admin', 'teacher']:
            return True
        application = _get_application(obj)
        if application is None:
            return False
        # 主导撰写人
        if application.main_writer_id == request.user.id:
            return True
        # 申请执行人
        if application.applicant_executor_id == request.user.id:
            return True
        # 申请关联项目的负责人
        project = getattr(application, 'related_project', None)
        if project is not None and project.leader_id == request.user.id:
            return True
        return False


class IsReturnModifier(BasePermission):
    """
    退回修改责任人权限
    用于完成退回修改操作：退回记录的责任人/实际修改人可完成
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 系统管理员/老师可操作
        if request.user.global_role in ['sys_admin', 'teacher']:
            return True
        # 退回记录对象
        from .models import IPReturnRecord
        if isinstance(obj, IPReturnRecord):
            # 责任人
            if obj.responsible_user_id == request.user.id:
                return True
            # 实际修改人
            if obj.actual_modifier_id == request.user.id:
                return True
            # 申请执行人/主导撰写人
            application = obj.application
            if application.main_writer_id == request.user.id:
                return True
            if application.applicant_executor_id == request.user.id:
                return True
            # 项目负责人
            project = getattr(application, 'related_project', None)
            if project is not None and project.leader_id == request.user.id:
                return True
            return False
        # 其他对象回退到项目成员判断
        application = _get_application(obj)
        if application is None:
            return False
        return _is_project_member(request.user, application)
