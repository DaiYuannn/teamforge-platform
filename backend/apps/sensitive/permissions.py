"""
敏感资料模块权限
- IsInternalSensitiveMember: 内部成员可查看团队脱敏目录
- IsSensitiveDataOwner: 安全读取开放脱敏元数据，写操作仍校验所有者/角色
- IsSensitiveApproverOrAdmin: 审批权限
- HasValidAccessApproval: 有有效审批才能查看明文
所有权限必须后端真实校验
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.db.models import Q
from django.utils import timezone


GLOBAL_SENSITIVE_MANAGER_ROLES = {'sys_admin', 'teacher'}


def _active_team_ids(user):
    from apps.common.team_models import TeamMember

    if not user or not user.is_authenticated:
        return set()
    return set(
        TeamMember.objects.filter(
            user=user,
            status=TeamMember.Status.ACTIVE,
        ).values_list('team_id', flat=True)
    )


def sensitive_review_team_ids(user):
    """返回用户被明确允许处理敏感申请的团队范围。"""
    from apps.common.team_models import Team, TeamMember

    if (
        not user
        or not user.is_authenticated
        or not user.is_active
        or getattr(user, 'membership_status', '') not in {'active', 'on_leave'}
    ):
        return set()
    if user.global_role in GLOBAL_SENSITIVE_MANAGER_ROLES:
        return set(Team.objects.values_list('id', flat=True))
    team_ids = set(
        Team.objects.filter(owner=user).values_list('id', flat=True)
    )
    team_ids.update(
        TeamMember.objects.filter(
            user=user,
            role__in=[TeamMember.Role.OWNER, TeamMember.Role.CO_LEAD],
            status=TeamMember.Status.ACTIVE,
        ).values_list('team_id', flat=True)
    )
    # sens_approver 是“明确审批人”，但仍必须是目标团队的活动成员，
    # 不再拥有跨全部团队的共享队列。
    if user.global_role == 'sens_approver':
        team_ids.update(_active_team_ids(user))
    return team_ids


def can_review_sensitive_data(user, sensitive_data):
    if (
        user
        and user.is_authenticated
        and user.is_active
        and user.global_role in GLOBAL_SENSITIVE_MANAGER_ROLES
    ):
        return True
    if not sensitive_data.team_id:
        # 历史资料在完成团队归属补录前，仅保留给明确的敏感审批人。
        return bool(
            is_internal_sensitive_member(user)
            and user.global_role == 'sens_approver'
        )
    return bool(
        sensitive_data.team_id in sensitive_review_team_ids(user)
    )


def can_review_sensitive_request(user, access_request):
    return can_review_sensitive_data(user, access_request.sensitive_data)


def user_can_view_sensitive_metadata(user, sensitive_data):
    if not is_internal_sensitive_member(user):
        return False
    if sensitive_data.uploader_id == user.id or sensitive_data.subject_user_id == user.id:
        return True
    if can_use_sensitive_grant(user, sensitive_data):
        return True
    if not sensitive_data.team_id:
        return False
    if sensitive_data.data_type == 'id_card':
        return can_review_sensitive_data(user, sensitive_data)
    return sensitive_data.team_id in _active_team_ids(user)


def scope_sensitive_data_queryset(queryset, user):
    """团队资料仅在本队可见；身份证目录进一步收窄到本人和审批角色。"""
    if not is_internal_sensitive_member(user):
        return queryset.none()
    active_team_ids = _active_team_ids(user)
    review_team_ids = sensitive_review_team_ids(user)
    visibility = (
        Q(uploader=user)
        | Q(subject_user=user)
        | Q(team_id__in=active_team_ids) & ~Q(data_type='id_card')
        | Q(team_id__in=review_team_ids, data_type='id_card')
        | (
            Q(
                direct_grants__granted_to=user,
                direct_grants__revoked_at__isnull=True,
                direct_grants__expires_at__gt=timezone.now(),
            )
            & (
                Q(direct_grants__can_view=True)
                | Q(direct_grants__can_download=True)
            )
        )
    )
    if user.global_role in GLOBAL_SENSITIVE_MANAGER_ROLES:
        return queryset.distinct()
    if user.global_role == 'sens_approver':
        visibility |= Q(team__isnull=True)
    return queryset.filter(visibility).distinct()


def get_active_sensitive_grant(user, sensitive_data, *, require_download=None):
    """Return the active grant for this exact record and user, if any."""
    if not is_internal_sensitive_member(user):
        return None
    from .models import SensitiveDataGrant

    queryset = SensitiveDataGrant.objects.filter(
        sensitive_data=sensitive_data,
        granted_to=user,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    )
    if require_download is True:
        queryset = queryset.filter(can_download=True)
    elif require_download is False:
        queryset = queryset.filter(can_view=True)
    else:
        queryset = queryset.filter(Q(can_view=True) | Q(can_download=True))
    return queryset.select_related('sensitive_data', 'granted_to', 'granted_by').first()


def can_use_sensitive_grant(user, sensitive_data, *, require_download=None):
    return get_active_sensitive_grant(
        user,
        sensitive_data,
        require_download=require_download,
    ) is not None


def can_manage_sensitive_grants(user, sensitive_data):
    """Team reviewers and the data subject may delegate one exact record."""
    if not is_internal_sensitive_member(user):
        return False
    return bool(
        sensitive_data.subject_user_id == user.id
        or can_review_sensitive_data(user, sensitive_data)
    )


def is_internal_sensitive_member(user):
    """离队成员和外部协作者不能浏览团队敏感资料目录。"""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    return getattr(user, 'membership_status', 'active') in ['active', 'on_leave']


class IsInternalSensitiveMember(BasePermission):
    """团队内部成员可访问脱敏目录并提交自己的访问申请。"""

    def has_permission(self, request, view):
        return is_internal_sensitive_member(getattr(request, 'user', None))


class IsSensitiveDataOwner(BasePermission):
    """
    敏感资料拥有者权限
    - 普通内部成员可查看所有条目的脱敏元数据
    - 非安全方法仍只允许拥有者或审批角色
    - 管理员/敏感审批人可查看所有
    """

    def has_permission(self, request, view):
        return is_internal_sensitive_member(getattr(request, 'user', None))

    def has_object_permission(self, request, view, obj):
        if (
            not request.user
            or not request.user.is_authenticated
            or not request.user.is_active
        ):
            return False
        if request.method in SAFE_METHODS:
            return user_can_view_sensitive_metadata(request.user, obj)
        # 数据拥有者（上传人）可访问
        if getattr(obj, 'uploader_id', None) == request.user.id:
            return True
        return can_review_sensitive_data(request.user, obj)


class IsSensitiveApproverOrAdmin(BasePermission):
    """
    敏感资料审批人/管理员权限
    用于审批操作（approve/reject）
    """

    def has_permission(self, request, view):
        if not is_internal_sensitive_member(getattr(request, 'user', None)):
            return False
        return bool(
            request.user.global_role == 'sens_approver'
            or sensitive_review_team_ids(request.user)
        )

    def has_object_permission(self, request, view, obj):
        if not is_internal_sensitive_member(getattr(request, 'user', None)):
            return False
        return can_review_sensitive_request(request.user, obj)


class IsSensitiveDataCreator(BasePermission):
    """
    敏感资料创建权限
    - 活动内部成员可提交本团队资料；序列化器继续校验团队和资料所属人
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.is_active:
            return False
        return is_internal_sensitive_member(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return user_can_view_sensitive_metadata(request.user, obj)
        return (
            obj.uploader_id == request.user.id
            or can_review_sensitive_data(request.user, obj)
        )


class HasValidAccessApproval(BasePermission):
    """
    有效审批权限
    - 查看明文时校验：申请人本人 + 状态为已通过 + 未过期
    - 实际的申请ID校验在视图中完成，此处仅做基础认证
    """

    def has_permission(self, request, view):
        return is_internal_sensitive_member(getattr(request, 'user', None))
