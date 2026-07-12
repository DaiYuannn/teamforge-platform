"""
多团队支持序列化器与视图
- TeamViewSet: 团队 CRUD + 成员管理
- TeamMemberViewSet: 团队成员 CRUD
"""
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from .team_models import Team, TeamMember


# ============ 序列化器 ============

class TeamMemberSerializer(serializers.ModelSerializer):
    """团队成员序列化器"""
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    user_email = serializers.CharField(source='user.email', read_only=True, default='')
    team_name = serializers.CharField(source='team.name', read_only=True, default='')

    class Meta:
        model = TeamMember
        fields = ('id', 'team', 'team_name', 'user', 'user_name', 'user_email', 'role', 'joined_at')
        read_only_fields = ('id', 'joined_at')


class TeamSerializer(serializers.ModelSerializer):
    """团队序列化器"""
    owner_name = serializers.CharField(source='owner.name', read_only=True, default='')
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ('id', 'name', 'description', 'owner', 'owner_name', 'member_count', 'created_at')
        read_only_fields = ('id', 'owner', 'created_at')

    def get_member_count(self, obj):
        return obj.teammember_set.count()


class TeamCreateSerializer(serializers.ModelSerializer):
    """团队创建序列化器"""

    class Meta:
        model = Team
        fields = ('id', 'name', 'description')
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
        return success_response(
            TeamSerializer(team).data,
            message='团队创建成功',
            http_status=status.HTTP_201_CREATED,
        )

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
            return success_response(TeamMemberSerializer(members, many=True).data)

        # 添加成员
        user_id = request.data.get('user')
        role = request.data.get('role', 'member')
        if not user_id:
            return error_response(message='请提供 user（成员用户ID）', code=2401)
        member, created = TeamMember.objects.get_or_create(
            team=team, user_id=user_id,
            defaults={'role': role},
        )
        if not created:
            return error_response(message='该用户已是团队成员', code=2402)
        return success_response(
            TeamMemberSerializer(member).data,
            message='成员添加成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'], url_path='members/(?P<member_id>[0-9]+)')
    def remove_member(self, request, pk=None, member_id=None):
        """
        移除成员
        DELETE /api/v1/teams/{id}/members/{member_id}/
        """
        team = self.get_object()
        deleted, _ = TeamMember.objects.filter(team=team, id=member_id).delete()
        if not deleted:
            return error_response(message='成员不存在', code=2403, http_status=status.HTTP_404_NOT_FOUND)
        return success_response(message='成员已移除')


class TeamMemberViewSet(ModelViewSet):
    """团队成员 CRUD（独立路由）"""
    queryset = TeamMember.objects.all().order_by('-joined_at')
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['team', 'user', 'role']
