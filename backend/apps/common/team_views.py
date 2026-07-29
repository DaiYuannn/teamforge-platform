"""
多团队支持序列化器与视图
- TeamViewSet: 团队 CRUD + 成员管理
- TeamMemberViewSet: 团队成员 CRUD
"""
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from common.project_access import active_user_root_team_ids
from .team_models import Team, TeamMember, TeamMembershipEvent


TEAM_MEMBER_ROLE_PRIORITY = (
    TeamMember.Role.TEACHER,
    TeamMember.Role.OWNER,
    TeamMember.Role.CO_LEAD,
    TeamMember.Role.ADMIN,
    TeamMember.Role.ADVISOR,
    TeamMember.Role.MEMBER,
    TeamMember.Role.EXTERNAL,
)


def _filter_and_order_team_members(queryset, query_params):
    """Apply one member-list contract to nested and standalone endpoints."""
    role_value = (
        query_params.get('role')
        or query_params.get('team_role')
        or ''
    ).strip()
    school_value = (query_params.get('school') or '').strip()
    team_status_value = (
        query_params.get('status')
        or query_params.get('team_status')
        or ''
    ).strip()
    membership_status_value = (
        query_params.get('membership_status')
        or ''
    ).strip()

    if role_value:
        queryset = queryset.filter(role=role_value)
    if school_value:
        queryset = queryset.filter(user__school__icontains=school_value)
    if team_status_value:
        queryset = queryset.filter(status=team_status_value)
    if membership_status_value:
        queryset = queryset.filter(
            user__membership_status=membership_status_value
        )

    role_order = Case(
        *[
            When(role=role, then=Value(priority))
            for priority, role in enumerate(TEAM_MEMBER_ROLE_PRIORITY)
        ],
        default=Value(len(TEAM_MEMBER_ROLE_PRIORITY)),
        output_field=IntegerField(),
    )
    return (
        queryset
        .select_related('team', 'user', 'handover_to__user')
        .annotate(_role_priority=role_order)
        .order_by('_role_priority', 'user__name', 'joined_at', 'id')
    )


def _visible_teams_for(user):
    """仅让仍在队/暂离的内部成员看到自己的组织及相邻两级上下文。"""
    if (
        not user
        or not user.is_authenticated
        or not user.is_active
        or getattr(user, 'membership_status', '') not in {'active', 'on_leave'}
    ):
        return Team.objects.none()
    if user.global_role == 'sys_admin':
        return Team.objects.all()

    visible_statuses = [TeamMember.Status.ACTIVE, TeamMember.Status.ON_LEAVE]
    return Team.objects.filter(
        Q(owner=user)
        | Q(
            teammember__user=user,
            teammember__status__in=visible_statuses,
        )
        | Q(parent__owner=user)
        | Q(
            parent__teammember__user=user,
            parent__teammember__role__in=[
                TeamMember.Role.OWNER,
                TeamMember.Role.CO_LEAD,
                TeamMember.Role.ADMIN,
                TeamMember.Role.TEACHER,
            ],
            parent__teammember__status=TeamMember.Status.ACTIVE,
        )
        | Q(child_teams__owner=user)
        | Q(
            child_teams__teammember__user=user,
            child_teams__teammember__status__in=visible_statuses,
        )
    ).distinct()


def _is_team_manager(team, user):
    manages_team = (
        user.global_role == 'sys_admin'
        or team.owner_id == user.id
        or TeamMember.objects.filter(
            team=team,
            user=user,
            role__in=[
                TeamMember.Role.OWNER,
                TeamMember.Role.CO_LEAD,
                TeamMember.Role.ADMIN,
            ],
            status=TeamMember.Status.ACTIVE,
        ).exists()
    )
    if manages_team or not team.parent_id:
        return manages_team
    return (
        team.parent.owner_id == user.id
        or TeamMember.objects.filter(
            team=team.parent,
            user=user,
            role__in=[
                TeamMember.Role.OWNER,
                TeamMember.Role.CO_LEAD,
                TeamMember.Role.ADMIN,
            ],
            status=TeamMember.Status.ACTIVE,
        ).exists()
    )


def _can_assign_team_leadership(team, user):
    """共同负责人属于提权操作，只允许主负责人或上级总团队负责人授予。"""
    if user.global_role == 'sys_admin' or team.owner_id == user.id:
        return True
    parent = getattr(team, 'parent', None)
    if not parent:
        return False
    if parent.owner_id == user.id:
        return True
    return TeamMember.objects.filter(
        team=parent,
        user=user,
        role__in=[TeamMember.Role.OWNER, TeamMember.Role.CO_LEAD],
        status=TeamMember.Status.ACTIVE,
    ).exists()


def _user_can_join_team_organization(team, user, role, actor):
    """限制普通成员只能加入同一根团队，保留单根部署的待分组成员兼容。"""
    if actor.global_role == 'sys_admin':
        return bool(user and user.is_active)
    if not user or not user.is_active:
        return False
    membership_status = getattr(user, 'membership_status', '')
    if membership_status == 'external':
        return role == TeamMember.Role.EXTERNAL
    if membership_status not in {'active', 'on_leave'}:
        return False

    target_root_id = team.parent_id or team.id
    user_root_ids = active_user_root_team_ids(user)
    if target_root_id in user_root_ids:
        return True
    if user_root_ids:
        return False

    # 升级后的单根团队部署中，尚未分组的旧用户仍可由负责人首次加入。
    active_root_ids = list(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)[:2]
    )
    return len(active_root_ids) == 1 and active_root_ids[0] == target_root_id


# ============ 序列化器 ============

class TeamMemberSerializer(serializers.ModelSerializer):
    """团队成员序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    user_email = serializers.CharField(source='user.email', read_only=True, default='')
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    user_school = serializers.CharField(source='user.school', read_only=True, default='')
    user_grade = serializers.CharField(source='user.grade', read_only=True, default='')
    user_major = serializers.CharField(source='user.major', read_only=True, default='')
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    handover_to_name = serializers.CharField(source='handover_to.user.name', read_only=True, default='')

    class Meta:
        model = TeamMember
        fields = (
            'id', 'team', 'team_name', 'user', 'user_name', 'user_email',
            'user_avatar', 'user_school', 'user_grade', 'user_major',
            'role', 'role_display', 'status', 'status_display', 'joined_at',
            'left_at', 'exit_reason', 'handover_to', 'handover_to_name',
            'handover_notes',
        )
        read_only_fields = ('id', 'joined_at')


class TeamMembershipEventSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.name', read_only=True, default='')
    member_name = serializers.CharField(source='membership.user.name', read_only=True, default='')
    handover_to_name = serializers.CharField(source='handover_to.user.name', read_only=True, default='')

    class Meta:
        model = TeamMembershipEvent
        fields = (
            'id', 'membership', 'member_name', 'event_type', 'from_role', 'to_role',
            'from_status', 'to_status', 'reason', 'handover_to',
            'handover_to_name', 'handover_notes', 'operator', 'operator_name',
            'created_at',
        )
        read_only_fields = fields


class TeamSerializer(serializers.ModelSerializer):
    """团队序列化器"""
    owner_name = serializers.CharField(source='owner.name', read_only=True, default='')
    parent_name = serializers.CharField(source='parent.name', read_only=True, default='')
    team_type_display = serializers.CharField(source='get_team_type_display', read_only=True)
    member_count = serializers.SerializerMethodField()
    child_count = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = (
            'id', 'name', 'code', 'description', 'logo', 'contact_email',
            'join_message', 'is_active', 'owner', 'owner_name', 'member_count',
            'parent', 'parent_name', 'team_type', 'team_type_display', 'child_count',
            'current_user_role', 'can_manage', 'created_at',
        )
        read_only_fields = ('id', 'owner', 'created_at')

    def get_member_count(self, obj) -> int:
        return obj.teammember_set.filter(status=TeamMember.Status.ACTIVE).count()

    def get_child_count(self, obj) -> int:
        return obj.child_teams.filter(is_active=True).count()

    def get_current_user_role(self, obj) -> str:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ''
        membership = TeamMember.objects.filter(
            team=obj,
            user=request.user,
            status__in=[TeamMember.Status.ACTIVE, TeamMember.Status.ON_LEAVE],
        ).first()
        return membership.role if membership else ''

    def get_can_manage(self, obj) -> bool:
        request = self.context.get('request')
        return bool(
            request and request.user.is_authenticated
            and _is_team_manager(obj, request.user)
        )


class TeamCreateSerializer(serializers.ModelSerializer):
    """团队创建序列化器"""

    class Meta:
        model = Team
        fields = (
            'id', 'name', 'code', 'description', 'logo', 'contact_email',
            'join_message', 'is_active', 'parent', 'team_type',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        request = self.context.get('request')
        instance = self.instance
        parent = attrs.get('parent', getattr(instance, 'parent', None))
        if (
            instance
            and 'parent' in attrs
            and instance.parent_id != getattr(parent, 'pk', None)
            and request
            and instance.parent
            and not _is_team_manager(instance.parent, request.user)
        ):
            raise serializers.ValidationError({
                'parent': '调整或解除小团队归属需经原总团队负责人操作'
            })
        if parent:
            if instance and parent.pk == instance.pk:
                raise serializers.ValidationError({'parent': '团队不能将自己设为上级团队'})
            if instance and instance.child_teams.exists():
                raise serializers.ValidationError({
                    'parent': '已有下级团队的总团队不能再改为其他团队的下级'
                })
            if parent.parent_id:
                raise serializers.ValidationError({'parent': '团队组织最多支持“总团队—小团队”两级'})
            if request and not _is_team_manager(parent, request.user):
                raise serializers.ValidationError({'parent': '只有总团队负责人可以创建或调整其小团队'})
            attrs['team_type'] = Team.TeamType.SQUAD
        else:
            attrs['team_type'] = Team.TeamType.ORGANIZATION
        return attrs


# ============ ViewSet ============

class TeamViewSet(MultiSerializerMixin, ModelViewSet):
    """
    团队管理 ViewSet
    - list: 当前用户可查看自己拥有或加入的团队
    - create: 创建团队（owner 自动设为当前用户，并自动加入为 owner）
    - members: GET/POST 管理团队成员
    """
    queryset = Team.objects.all().order_by('-created_at')
    serializer_class = TeamSerializer
    serializer_classes_by_action = {
        'list': TeamSerializer,
        'retrieve': TeamSerializer,
        'create': TeamCreateSerializer,
        'update': TeamCreateSerializer,
        'partial_update': TeamCreateSerializer,
    }
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        # 当前用户可见自己有效加入的团队，并补充相邻的两级组织上下文。
        return _visible_teams_for(
            self.request.user,
        ).select_related('owner', 'parent').order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = serializer.save(owner=request.user)
        # 创建人自动加入为 owner
        TeamMember.objects.create(team=team, user=request.user, role='owner')
        owner_membership = TeamMember.objects.get(team=team, user=request.user)
        TeamMembershipEvent.objects.create(
            membership=owner_membership,
            event_type='joined',
            to_role=owner_membership.role,
            to_status=owner_membership.status,
            operator=request.user,
        )
        return success_response(
            TeamSerializer(team, context={'request': request}).data,
            message='团队创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        team = self.get_object()
        if not _is_team_manager(team, request.user):
            return error_response(
                message='只有团队负责人或管理员可以修改团队资料',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        team = self.get_object()
        if request.user.global_role != 'sys_admin' and team.owner_id != request.user.id:
            return error_response(
                message='只有团队负责人可以删除团队',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        """
        团队成员管理
        GET  /api/v1/teams/{id}/members/    列出成员
        POST /api/v1/teams/{id}/members/    添加成员 body: {"user": 1, "role": "member"}
        """
        team = self.get_object()
        if request.method == 'GET':
            members = _filter_and_order_team_members(
                team.teammember_set.all(),
                request.query_params,
            )
            return success_response(TeamMemberSerializer(members, many=True).data)

        # 添加成员
        if not _is_team_manager(team, request.user):
            return error_response(
                message='只有团队负责人或管理员可以添加成员',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        user_id = request.data.get('user')
        role = request.data.get('role', 'member')
        if not user_id:
            return error_response(message='请提供 user（成员用户ID）', code=2401)
        if role not in TeamMember.Role.values:
            return error_response(message='团队角色不合法', code=2404)
        if role == TeamMember.Role.OWNER:
            return error_response(
                message='主负责人只能通过负责人转让设置',
                code=2405,
            )
        if (
            role == TeamMember.Role.CO_LEAD
            and not _can_assign_team_leadership(team, request.user)
        ):
            return error_response(
                message='只有主负责人或上级总团队负责人可以设置共同负责人',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        from apps.users.models import User

        target_user = User.objects.filter(pk=user_id).first()
        if target_user is None:
            return error_response(message='成员用户不存在', code=2403)
        if not _user_can_join_team_organization(
            team,
            target_user,
            role,
            request.user,
        ):
            return error_response(
                message='只能添加同一总团队的成员；外部协作者需使用外部协作者角色',
                code=2409,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        member, created = TeamMember.objects.get_or_create(
            team=team, user=target_user,
            defaults={'role': role},
        )
        if not created:
            if member.status != TeamMember.Status.EXITED:
                return error_response(message='该用户已是团队成员', code=2402)
            old_status = member.status
            member.status = TeamMember.Status.ACTIVE
            member.role = role
            member.left_at = None
            member.exit_reason = ''
            member.handover_to = None
            member.handover_notes = ''
            member.save()
            TeamMembershipEvent.objects.create(
                membership=member,
                event_type='reactivated',
                from_status=old_status,
                to_status=member.status,
                to_role=member.role,
                operator=request.user,
            )
        else:
            TeamMembershipEvent.objects.create(
                membership=member,
                event_type='joined',
                to_role=member.role,
                to_status=member.status,
                operator=request.user,
            )
        return success_response(
            TeamMemberSerializer(member).data,
            message='成员添加成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='members/(?P<member_id>[0-9]+)/transition')
    @transaction.atomic
    def transition_member(self, request, pk=None, member_id=None):
        team = self.get_object()
        if not _is_team_manager(team, request.user):
            return error_response(
                message='只有团队负责人或管理员可以变更成员',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        member = TeamMember.objects.filter(team=team, pk=member_id).first()
        if member is None:
            return error_response(message='成员不存在', code=2403, http_status=status.HTTP_404_NOT_FOUND)
        role_value = request.data.get('role', member.role)
        status_value = request.data.get('status', member.status)
        if role_value not in TeamMember.Role.values or status_value not in TeamMember.Status.values:
            return error_response(message='角色或成员状态不合法', code=2404)
        if member.role == TeamMember.Role.OWNER and status_value == TeamMember.Status.EXITED:
            return error_response(message='团队负责人不能直接退出，请先转让团队负责人', code=2405)
        if member.role == TeamMember.Role.OWNER and role_value != TeamMember.Role.OWNER:
            return error_response(message='主负责人角色只能通过负责人转让进行变更', code=2405)
        if member.role != TeamMember.Role.OWNER and role_value == TeamMember.Role.OWNER:
            return error_response(message='主负责人只能通过负责人转让设置', code=2405)
        if (
            TeamMember.Role.CO_LEAD in {member.role, role_value}
            and member.role != role_value
            and not _can_assign_team_leadership(team, request.user)
        ):
            return error_response(
                message='只有主负责人或上级总团队负责人可以授予或撤销共同负责人',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        handover = None
        if request.data.get('handover_to'):
            handover = TeamMember.objects.filter(
                team=team,
                pk=request.data['handover_to'],
                status=TeamMember.Status.ACTIVE,
            ).exclude(pk=member.pk).first()
            if handover is None:
                return error_response(message='交接人必须是同团队的活动成员', code=2406)
        old_role, old_status = member.role, member.status
        member.role = role_value
        member.status = status_value
        member.exit_reason = request.data.get('reason', '')
        member.handover_to = handover
        member.handover_notes = request.data.get('handover_notes', '')
        member.left_at = timezone.now() if status_value == TeamMember.Status.EXITED else None
        member.save()
        TeamMembershipEvent.objects.create(
            membership=member,
            event_type=(
                'exited' if status_value == TeamMember.Status.EXITED
                else 'role_changed' if old_role != role_value
                else 'status_changed'
            ),
            from_role=old_role,
            to_role=role_value,
            from_status=old_status,
            to_status=status_value,
            reason=member.exit_reason,
            handover_to=handover,
            handover_notes=member.handover_notes,
            operator=request.user,
        )
        return success_response(TeamMemberSerializer(member).data, message='团队成员已更新')

    @action(detail=True, methods=['get'], url_path='membership-history')
    def membership_history(self, request, pk=None):
        team = self.get_object()
        events = TeamMembershipEvent.objects.filter(
            membership__team=team
        ).select_related('membership__user', 'operator', 'handover_to__user')
        return success_response(TeamMembershipEventSerializer(events, many=True).data)

    @action(detail=True, methods=['get'])
    def candidates(self, request, pk=None):
        """团队管理员选择新增成员或交接人时使用的最小化成员目录。"""
        team = self.get_object()
        if not _is_team_manager(team, request.user):
            return error_response(
                message='只有团队负责人或管理员可以查看候选成员',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        from apps.users.models import User

        users = User.objects.exclude(
            membership_status=User.MembershipStatus.EXITED
        ).filter(is_active=True)
        if request.user.global_role != 'sys_admin':
            root_id = team.parent_id or team.id
            visible_statuses = [
                TeamMember.Status.ACTIVE,
                TeamMember.Status.ON_LEAVE,
            ]
            same_root_user_ids = TeamMember.objects.filter(
                Q(team_id=root_id) | Q(team__parent_id=root_id),
                status__in=visible_statuses,
            ).values_list('user_id', flat=True)
            same_root_owner_ids = Team.objects.filter(
                Q(id=root_id) | Q(parent_id=root_id),
            ).values_list('owner_id', flat=True)
            active_root_ids = list(
                Team.objects.filter(
                    parent__isnull=True,
                    is_active=True,
                ).values_list('id', flat=True)[:2]
            )
            allowed_ids = set(same_root_user_ids) | set(same_root_owner_ids)
            if len(active_root_ids) == 1 and active_root_ids[0] == root_id:
                assigned_user_ids = set(
                    TeamMember.objects.filter(
                        status__in=visible_statuses,
                    ).values_list('user_id', flat=True)
                )
                owned_user_ids = set(
                    Team.objects.values_list('owner_id', flat=True)
                )
                unassigned_ids = set(
                    users.exclude(
                        id__in=assigned_user_ids | owned_user_ids
                    ).values_list('id', flat=True)
                )
                allowed_ids.update(unassigned_ids)
            users = users.filter(id__in=allowed_ids)
        users = users.order_by('name')
        search = request.query_params.get('search', '').strip()
        if search:
            users = users.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search)
            )
        return success_response([
            {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'membership_status': user.membership_status,
            }
            for user in users[:200]
        ])

    @action(detail=True, methods=['post'], url_path='transfer-owner')
    @transaction.atomic
    def transfer_owner(self, request, pk=None):
        team = self.get_object()
        if request.user.global_role != 'sys_admin' and team.owner_id != request.user.id:
            return error_response(
                message='只有当前团队负责人可以转让负责人',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        target = TeamMember.objects.filter(
            team=team,
            pk=request.data.get('member_id'),
            status=TeamMember.Status.ACTIVE,
        ).select_related('user').first()
        if target is None:
            return error_response(message='接任成员不存在或不在队', code=2406)
        old_owner = TeamMember.objects.filter(
            team=team, user=team.owner
        ).first()
        if old_owner and old_owner.pk == target.pk:
            return error_response(message='该成员已经是团队负责人', code=2408)
        if old_owner:
            previous_role = old_owner.role
            old_owner.role = TeamMember.Role.CO_LEAD
            old_owner.save(update_fields=['role'])
            TeamMembershipEvent.objects.create(
                membership=old_owner,
                event_type='role_changed',
                from_role=previous_role,
                to_role=old_owner.role,
                from_status=old_owner.status,
                to_status=old_owner.status,
                reason=request.data.get('reason', '团队负责人转让'),
                operator=request.user,
            )
        previous_role = target.role
        target.role = TeamMember.Role.OWNER
        target.save(update_fields=['role'])
        team.owner = target.user
        team.save(update_fields=['owner'])
        TeamMembershipEvent.objects.create(
            membership=target,
            event_type='role_changed',
            from_role=previous_role,
            to_role=target.role,
            from_status=target.status,
            to_status=target.status,
            reason=request.data.get('reason', '团队负责人转让'),
            operator=request.user,
        )
        return success_response(
            TeamSerializer(team, context={'request': request}).data,
            message='团队负责人已转让',
        )

    @action(detail=True, methods=['delete'], url_path='members/(?P<member_id>[0-9]+)')
    @transaction.atomic
    def remove_member(self, request, pk=None, member_id=None):
        """
        移除成员
        DELETE /api/v1/teams/{id}/members/{member_id}/
        """
        team = self.get_object()
        if not _is_team_manager(team, request.user):
            return error_response(
                message='只有团队负责人或管理员可以移除成员',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        member = TeamMember.objects.filter(team=team, id=member_id).first()
        if not member:
            return error_response(message='成员不存在', code=2403, http_status=status.HTTP_404_NOT_FOUND)
        if member.role == TeamMember.Role.OWNER:
            return error_response(message='不能移除团队负责人', code=2405)
        old_status = member.status
        member.status = TeamMember.Status.EXITED
        member.left_at = timezone.now()
        member.exit_reason = request.data.get('reason', '团队管理员执行离队')
        member.save()
        TeamMembershipEvent.objects.create(
            membership=member,
            event_type='exited',
            from_role=member.role,
            to_role=member.role,
            from_status=old_status,
            to_status=member.status,
            reason=member.exit_reason,
            operator=request.user,
        )
        return success_response(message='成员已离队，历史记录已保留')


class TeamMemberViewSet(ModelViewSet):
    """团队成员 CRUD（独立路由）"""
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]
    # role/status 统一由 _filter_and_order_team_members 处理，确保该入口与
    # /teams/{id}/members/ 对合法及非法参数保持一致。
    filterset_fields = ['team', 'user']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        user = self.request.user
        queryset = self.queryset
        if user.global_role != 'sys_admin':
            queryset = queryset.filter(
                team__in=_visible_teams_for(user),
            ).distinct()
        return _filter_and_order_team_members(
            queryset,
            self.request.query_params,
        )

    def create(self, request, *args, **kwargs):
        team = Team.objects.filter(pk=request.data.get('team')).first()
        if team is None or not _is_team_manager(team, request.user):
            return error_response(
                message='无权管理该团队',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if request.data.get('role') == TeamMember.Role.OWNER:
            return error_response(
                message='主负责人只能通过负责人转让设置',
                code=2405,
            )
        if (
            request.data.get('role') == TeamMember.Role.CO_LEAD
            and not _can_assign_team_leadership(team, request.user)
        ):
            return error_response(
                message='只有主负责人或上级总团队负责人可以设置共同负责人',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        from apps.users.models import User

        role = request.data.get('role', TeamMember.Role.MEMBER)
        target_user = User.objects.filter(pk=request.data.get('user')).first()
        if target_user is None:
            return error_response(message='成员用户不存在', code=2403)
        if not _user_can_join_team_organization(
            team,
            target_user,
            role,
            request.user,
        ):
            return error_response(
                message='只能添加同一总团队的成员；外部协作者需使用外部协作者角色',
                code=2409,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        member = self.get_object()
        if not _is_team_manager(member.team, request.user):
            return error_response(
                message='无权管理该团队',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return error_response(message='请使用团队成员状态变更接口，以保留完整历史', code=2407)

    def destroy(self, request, *args, **kwargs):
        return error_response(message='请使用团队成员离队接口，以保留完整历史', code=2407)
