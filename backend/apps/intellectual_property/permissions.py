"""
知识产权管理权限
所有权限必须后端真实校验
"""
from django.db.models import Q
from rest_framework.permissions import BasePermission, SAFE_METHODS

from common.project_access import is_exited_member, is_external_collaborator
from common.project_access import project_can_manage


PRIVILEGED_IP_ROLES = ('sys_admin', 'teacher')


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
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return False
    if user.global_role in PRIVILEGED_IP_ROLES:
        return True
    project = getattr(application, 'related_project', None)
    project_ids = set()
    if project is not None:
        project_ids.add(project.id)
    if getattr(application, 'pk', None):
        project_ids.update(
            application.project_links.values_list('project_id', flat=True)
        )
    if not project_ids:
        return False
    from apps.projects.models import ProjectMember
    active_membership = ProjectMember.objects.filter(
        project_id__in=project_ids,
        user=user,
        status=ProjectMember.Status.ACTIVE,
    ).exists()
    if is_external_collaborator(user):
        return active_membership
    # 内部项目负责人或仍在项目中的成员可访问。
    from apps.projects.models import Project
    if any(
        project_can_manage(user, linked_project)
        for linked_project in Project.objects.filter(id__in=project_ids)
    ):
        return True
    return active_membership


def _can_access_application(user, application):
    """Return whether a user may see the application's non-public records."""
    return _is_project_member(user, application)


def accessible_ip_applications(user):
    """Applications whose private related records are visible to ``user``."""
    from .models import IntellectualPropertyApplication

    queryset = IntellectualPropertyApplication.objects.all()
    if (
        not user
        or not user.is_authenticated
        or not getattr(user, 'is_active', False)
        or is_exited_member(user)
    ):
        return queryset.none()
    if user.global_role in PRIVILEGED_IP_ROLES:
        return queryset

    from apps.projects.models import ProjectMember

    if is_external_collaborator(user):
        return queryset.filter(
            Q(
                related_project__members__user=user,
                related_project__members__status=ProjectMember.Status.ACTIVE,
            )
            | Q(
                project_links__project__members__user=user,
                project_links__project__members__status=ProjectMember.Status.ACTIVE,
            )
        ).distinct()

    return queryset.filter(
        Q(related_project__leader=user)
        | Q(
            related_project__members__user=user,
            related_project__members__status=ProjectMember.Status.ACTIVE,
        )
        | Q(project_links__project__leader=user)
        | Q(
            project_links__project__members__user=user,
            project_links__project__members__status=ProjectMember.Status.ACTIVE,
        )
    ).distinct()


def _request_application(request):
    """Resolve an application referenced by a create request."""
    from .models import IntellectualPropertyApplication

    application_id = request.data.get('application')
    if not application_id:
        return None
    try:
        return IntellectualPropertyApplication.objects.select_related(
            'related_project'
        ).get(pk=application_id)
    except (IntellectualPropertyApplication.DoesNotExist, TypeError, ValueError):
        return None


def _request_project(request):
    """Resolve a project referenced by an application create request."""
    from apps.projects.models import Project

    project_id = request.data.get('related_project')
    if not project_id:
        return None
    try:
        return Project.objects.get(pk=project_id)
    except (Project.DoesNotExist, TypeError, ValueError):
        return None


def _is_application_leader_or_privileged(user, application):
    if user.global_role in PRIVILEGED_IP_ROLES:
        return True
    # 写权限只跟随主项目。成果复用项目的负责人可查看关联成果，
    # 但不能据此核验身份、改主申请或推进申请流程。
    primary_project = getattr(application, 'related_project', None)
    if primary_project is not None:
        return project_can_manage(user, primary_project)
    primary_link = application.project_links.select_related('project').filter(
        relation_type='primary',
    ).first()
    return bool(
        primary_link and project_can_manage(user, primary_link.project)
    )


class IsIPProjectMember(BasePermission):
    """
    知识产权申请关联项目成员权限
    - 读取：项目成员可见
    - 写操作：项目成员可操作
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(view, 'action', None) == 'create':
            application = _request_application(request)
            return application is not None and _can_access_application(
                request.user, application
            )
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 系统管理员/老师可访问所有
        if request.user.global_role in PRIVILEGED_IP_ROLES:
            return True
        application = _get_application(obj)
        if application is None:
            return False
        return _can_access_application(request.user, application)


class IsProjectLeaderOrTeacherOrAdminForIP(BasePermission):
    """
    项目负责人 / 老师 / 管理员权限（知识产权专用）
    - 读取：所有认证用户
    - 写操作：老师/管理员/申请关联项目的负责人
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 安全方法的对象范围由各 ViewSet 的 queryset 隔离。
        if request.method in SAFE_METHODS:
            return True
        if request.user.global_role in PRIVILEGED_IP_ROLES:
            return True

        # 创建申请时校验请求中的项目；创建关联记录时校验请求中的申请。
        if getattr(view, 'action', None) == 'create':
            application = _request_application(request)
            if application is not None:
                return _is_application_leader_or_privileged(request.user, application)
            project = _request_project(request)
            return project_can_manage(request.user, project)

        # 非创建写操作继续执行到对象级权限，避免把项目负责人挡在入口处。
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # 读取对所有认证用户开放
        if request.method in SAFE_METHODS:
            return True
        # 系统管理员
        application = _get_application(obj)
        if application is None:
            return False
        return _is_application_leader_or_privileged(request.user, application)


class IsMainWriterOrExecutor(BasePermission):
    """
    主导撰写人 / 申请执行人 / 材料上传人权限
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
        if request.user.global_role in PRIVILEGED_IP_ROLES:
            return True
        from .models import IPMaterialVersion
        if isinstance(obj, IPMaterialVersion) and obj.uploaded_by_id == request.user.id:
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
        if _is_application_leader_or_privileged(request.user, application):
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
        if request.user.global_role in PRIVILEGED_IP_ROLES:
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
        return _can_access_application(request.user, application)
