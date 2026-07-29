"""
比赛视图
- CompetitionViewSet: 比赛 CRUD + 获奖记录管理
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.db.models import Case, Count, IntegerField, Q, Value, When

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsProjectLeaderOrTeacherOrAdmin
from common.project_access import (
    active_user_root_team_ids,
    project_root_team_ids,
    scope_project_queryset,
)
from apps.common.team_models import Team, TeamMember
from apps.users.models import User
from .member_search import member_matches_search, normalize_search_text
from .models import Competition, CompetitionEvent, CompetitionParticipant
from .permissions import can_manage_competition
from .serializers import (
    CompetitionEventSerializer,
    CompetitionSerializer,
    CompetitionListSerializer,
    CompetitionParticipantSerializer,
)
from .award_models import CompetitionAward
from .award_serializers import CompetitionAwardSerializer, CompetitionAwardCreateSerializer


TEAM_ROLE_PRIORITY = (
    TeamMember.Role.TEACHER,
    TeamMember.Role.OWNER,
    TeamMember.Role.CO_LEAD,
    TeamMember.Role.ADMIN,
    TeamMember.Role.ADVISOR,
    TeamMember.Role.MEMBER,
    TeamMember.Role.EXTERNAL,
)


class CompetitionEventViewSet(ReadOnlyModelViewSet):
    """List shared competition editions visible through their project entries."""

    serializer_class = CompetitionEventSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['edition']
    search_fields = ['name', 'edition', 'organizer']
    ordering_fields = ['edition', 'name', 'created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CompetitionEvent.objects.none()
        visible_entries = scope_project_queryset(
            Competition.objects.all(),
            self.request.user,
            project_lookup='project',
        )
        return (
            CompetitionEvent.objects
            .filter(entries__in=visible_entries)
            .annotate(
                entry_count=Count(
                    'entries',
                    filter=Q(entries__in=visible_entries),
                    distinct=True,
                ),
            )
            .distinct()
            .order_by('-edition', 'name', 'id')
        )


class CompetitionViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    比赛管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 项目负责人/老师/管理员
    """
    queryset = Competition.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': CompetitionListSerializer,
        'retrieve': CompetitionSerializer,
        'create': CompetitionSerializer,
        'update': CompetitionSerializer,
        'partial_update': CompetitionSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsProjectLeaderOrTeacherOrAdmin],
        'update': [IsAuthenticated],
        'partial_update': [IsAuthenticated],
        'destroy': [IsAuthenticated],
        'award_tracking': [IsAuthenticated],
        'participants': [IsAuthenticated],
        'participant_candidates': [IsAuthenticated],
    }

    filterset_fields = [
        'event', 'project', 'level', 'status', 'is_promoted', 'is_awarded',
    ]
    search_fields = ['name', 'organizer', 'project__name']
    ordering_fields = ['created_at', 'register_date', 'defense_date', 'result_date']

    def filter_queryset(self, queryset):
        # Candidate-search parameters belong to the member directory, not to
        # the Competition object resolved by this detail action.
        if self.action == 'participant_candidates':
            return queryset
        return super().filter_queryset(queryset)

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'event', 'project', 'project__leader',
        ).prefetch_related(
            'participants__user',
            'project__members__user',
            'project__teams',
        )
        return scope_project_queryset(
            queryset,
            self.request.user,
            project_lookup='project',
        )

    def create(self, request, *args, **kwargs):
        """创建比赛"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        competition = serializer.save()
        return success_response(
            CompetitionSerializer(
                competition,
                context=self.get_serializer_context(),
            ).data,
            message='比赛创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新比赛"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if not can_manage_competition(request.user, instance):
            return error_response(
                message='仅比赛负责人或项目负责人可修改比赛',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        competition = serializer.save()
        return success_response(
            CompetitionSerializer(
                competition,
                context=self.get_serializer_context(),
            ).data,
            message='比赛更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除比赛"""
        instance = self.get_object()
        if not can_manage_competition(request.user, instance):
            return error_response(
                message='仅比赛负责人或项目负责人可删除比赛',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return success_response(message='比赛删除成功')

    @action(detail=True, methods=['get', 'post', 'patch', 'delete'])
    def participants(self, request, pk=None):
        """维护比赛拟参赛及已确认成员名单。"""
        competition = self.get_object()
        if request.method == 'GET':
            records = competition.participants.select_related('user').all()
            return success_response(
                CompetitionParticipantSerializer(
                    records,
                    many=True,
                    context=self.get_serializer_context(),
                ).data
            )

        if not can_manage_competition(request.user, competition):
            return error_response(
                message='仅比赛负责人或项目负责人可维护参赛名单',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == 'POST':
            data = request.data.copy()
            data['competition'] = competition.id
            serializer = CompetitionParticipantSerializer(
                data=data,
                context=self.get_serializer_context(),
            )
            serializer.is_valid(raise_exception=True)
            participant = serializer.save()
            return success_response(
                CompetitionParticipantSerializer(
                    participant,
                    context=self.get_serializer_context(),
                ).data,
                message='参赛成员已添加',
                http_status=status.HTTP_201_CREATED,
            )

        participant_id = request.data.get('participant_id') or request.query_params.get(
            'participant_id'
        )
        participant = competition.participants.filter(pk=participant_id).first()
        if participant is None:
            return error_response(
                message='参赛成员记录不存在',
                code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        if request.method == 'PATCH':
            data = request.data.copy()
            data.pop('participant_id', None)
            serializer = CompetitionParticipantSerializer(
                participant,
                data=data,
                partial=True,
                context=self.get_serializer_context(),
            )
            serializer.is_valid(raise_exception=True)
            participant = serializer.save()
            return success_response(
                CompetitionParticipantSerializer(
                    participant,
                    context=self.get_serializer_context(),
                ).data,
                message='参赛成员已更新',
            )

        participant.delete()
        return success_response(message='参赛成员已移除')

    @action(detail=True, methods=['get'], url_path='participant-candidates')
    def participant_candidates(self, request, pk=None):
        """Search the target project's root organization without mutating it."""
        competition = self.get_object()
        if not can_manage_competition(request.user, competition):
            return error_response(
                message='仅比赛负责人或项目负责人可搜索参赛候选成员',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        root_ids = project_root_team_ids(competition.project)
        if not root_ids:
            root_ids = active_user_root_team_ids(request.user)
        if not root_ids and request.user.global_role == User.GlobalRole.SYS_ADMIN:
            root_ids = set(
                Team.objects.filter(
                    parent__isnull=True,
                    is_active=True,
                ).values_list('id', flat=True)
            )
        if not root_ids:
            return success_response([])

        role_order = Case(
            *[
                When(role=role, then=Value(priority))
                for priority, role in enumerate(TEAM_ROLE_PRIORITY)
            ],
            default=Value(len(TEAM_ROLE_PRIORITY)),
            output_field=IntegerField(),
        )
        root_order = Case(
            When(team__parent__isnull=True, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
        memberships = (
            TeamMember.objects
            .filter(
                Q(team_id__in=root_ids) | Q(team__parent_id__in=root_ids),
                status__in=[
                    TeamMember.Status.ACTIVE,
                    TeamMember.Status.ON_LEAVE,
                ],
                user__is_active=True,
                user__membership_status__in=[
                    User.MembershipStatus.ACTIVE,
                    User.MembershipStatus.ON_LEAVE,
                ],
            )
            .select_related('user', 'team')
            .annotate(_root_order=root_order, _role_order=role_order)
            .order_by('_root_order', '_role_order', 'user__name', 'user_id')
        )

        existing_user_ids = set(
            competition.participants.values_list('user_id', flat=True)
        )
        directory = {}
        for membership in memberships:
            if membership.user_id in existing_user_ids:
                continue
            directory.setdefault(membership.user_id, membership)

        search = request.query_params.get('search', '')
        school = normalize_search_text(request.query_params.get('school', ''))
        team_role = (request.query_params.get('team_role') or '').strip()
        membership_status = (
            request.query_params.get('membership_status') or ''
        ).strip()

        candidates = []
        for membership in directory.values():
            user = membership.user
            if school and normalize_search_text(user.school) != school:
                continue
            if team_role and membership.role != team_role:
                continue
            if (
                membership_status
                and user.membership_status != membership_status
            ):
                continue
            if not member_matches_search(
                query=search,
                name=user.name,
                values=[
                    user.name,
                    user.username,
                    user.email,
                    user.school,
                    user.grade,
                    user.major,
                    user.get_global_role_display(),
                    user.get_membership_status_display(),
                    membership.get_role_display(),
                    membership.get_status_display(),
                ],
            ):
                continue
            candidates.append({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'school': user.school,
                'grade': user.grade,
                'major': user.major,
                'global_role': user.global_role,
                'global_role_display': user.get_global_role_display(),
                'team_role': membership.role,
                'team_role_display': membership.get_role_display(),
                'membership_status': user.membership_status,
                'membership_status_display': (
                    user.get_membership_status_display()
                ),
                'team_status': membership.status,
                'team_status_display': membership.get_status_display(),
                'is_active': user.is_active,
            })
            if len(candidates) >= 200:
                break
        return success_response(candidates)

    @action(detail=True, methods=['get', 'post'])
    def award_tracking(self, request, pk=None):
        """
        比赛获奖记录管理
        GET /api/v1/competitions/{id}/award_tracking/
            - 获取该比赛的所有获奖记录
        POST /api/v1/competitions/{id}/award_tracking/
            - 创建获奖记录
            body: {"award_name": "一等奖", "award_level": "校级", "award_date": "2026-07-01", "recipients": [1,2], "notes": ""}
        """
        competition = self.get_object()

        if request.method == 'GET':
            awards = competition.awards.all().order_by('-award_date', '-created_at')
            serializer = CompetitionAwardSerializer(awards, many=True)
            return success_response(serializer.data, message='获奖记录查询成功')

        # POST: 创建获奖记录
        # 权限校验：项目负责人/老师/管理员
        self.check_object_permissions(request, competition)
        if not can_manage_competition(request.user, competition):
            return error_response(
                message='仅项目负责人/老师/管理员可创建获奖记录', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['competition'] = competition.id
        serializer = CompetitionAwardCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        award = serializer.save(competition=competition)
        self._sync_award_summary(competition)

        return success_response(
            CompetitionAwardSerializer(award).data,
            message='获奖记录创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path=r'awards/(?P<award_id>[0-9]+)',
    )
    def award_record(self, request, pk=None, award_id=None):
        """修改或删除一条比赛获奖记录。"""
        competition = self.get_object()
        if not can_manage_competition(request.user, competition):
            return error_response(
                message='仅比赛负责人、项目负责人、操作老师或管理员可维护获奖记录',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        award = CompetitionAward.objects.filter(
            competition=competition,
            pk=award_id,
        ).prefetch_related('recipients').first()
        if award is None:
            return error_response(
                message='获奖记录不存在',
                code=2404,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == 'DELETE':
            award.delete()
            self._sync_award_summary(competition)
            return success_response(message='获奖记录已删除')

        serializer = CompetitionAwardCreateSerializer(
            award,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        award = serializer.save()
        self._sync_award_summary(competition)
        return success_response(
            CompetitionAwardSerializer(award).data,
            message='获奖记录更新成功',
        )

    @staticmethod
    def _sync_award_summary(competition):
        """Keep the legacy summary fields aligned with the full award ledger."""
        awards = competition.awards.order_by('-award_date', '-created_at')
        latest = awards.first()
        competition.is_awarded = latest is not None
        competition.award_level = (
            latest.award_level or latest.award_name
            if latest is not None
            else ''
        )
        competition.save(update_fields=['is_awarded', 'award_level', 'updated_at'])
