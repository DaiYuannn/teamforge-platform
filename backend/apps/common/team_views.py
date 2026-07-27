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
from django.utils import timezone

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from .team_models import Team, TeamMember, TeamMembershipEvent


def _is_team_manager(team, user):
    return (
        user.global_role == 'sys_admin'
        or team.owner_id == user.id
        or TeamMember.objects.filter(
            team=team,
            user=user,
            role__in=[TeamMember.Role.OWNER, TeamMember.Role.ADMIN],
            status=TeamMember.Status.ACTIVE,
        ).exists()
    )


# ============ 序列化器 ============

class TeamMemberSerializer(serializers.ModelSerializer):
    """团队成员序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    user_email = serializers.CharField(source='user.email', read_only=True, default='')
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    handover_to_name = serializers.CharField(source='handover_to.user.name', read_only=True, default='')

    class Meta:
        model = TeamMember
        fields = (
            'id', 'team', 'team_name', 'user', 'user_name', 'user_email',
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
    member_count = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = (
            'id', 'name', 'code', 'description', 'logo', 'contact_email',
            'join_message', 'is_active', 'owner', 'owner_name', 'member_count',
            'current_user_role', 'can_manage', 'created_at',
        )
        read_only_fields = ('id', 'owner', 'created_at')

    def get_member_count(self, obj) -> int:
        return obj.teammember_set.filter(status=TeamMember.Status.ACTIVE).count()

    def get_current_user_role(self, obj) -> str:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ''
        membership = TeamMember.objects.filter(team=obj, user=request.user).first()
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
            'join_message', 'is_active',
        )
        read_only_fields = ('id',)


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
        user = self.request.user
        # 当前用户拥有或加入的团队
        owned = self.queryset.filter(owner=user)
        joined = Team.objects.filter(members=user)
        return (owned | joined).distinct()

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
            members = team.teammember_set.all().order_by('-joined_at')
            status_value = request.query_params.get('status')
            if status_value:
                members = members.filter(status=status_value)
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
        member, created = TeamMember.objects.get_or_create(
            team=team, user_id=user_id,
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
        ).order_by('name')
        search = request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
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
            old_owner.role = TeamMember.Role.ADMIN
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
    queryset = TeamMember.objects.all().order_by('-joined_at')
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['team', 'user', 'role']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        user = self.request.user
        if user.global_role == 'sys_admin':
            return self.queryset
        return self.queryset.filter(team__members=user).distinct()

    def create(self, request, *args, **kwargs):
        team = Team.objects.filter(pk=request.data.get('team')).first()
        if team is None or not _is_team_manager(team, request.user):
            return error_response(
                message='无权管理该团队',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
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
