"""
成员视图
- MemberViewSet: 只读列表+详情，所有认证用户可查看联系方式
- SkillTagViewSet: 技能标签 CRUD（管理员可管理标签）
- MemberSkillViewSet: 成员技能管理（自己管理自己的技能，可查看他人技能）
- FlexibleWorkScheduleViewSet: 灵活工时管理（每半月一次填写）
- MemberDetailView: 获取成员详情（基本信息+技能+灵活工时+项目+任务）
"""

from django.utils import timezone
from django.db.models import (
    Case,
    Exists,
    F,
    IntegerField,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Value,
    When,
)
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsSysAdmin
from common.project_access import (
    active_user_root_team_ids,
    is_external_collaborator,
    scope_organization_users,
)
from common.schema import success_response_schema
from apps.users.models import User
from apps.users.serializers import ExternalCollaboratorUserSerializer
from apps.competitions.member_search import (
    member_matches_search,
    normalize_search_text,
)
from .models import SkillTag, MemberSkill, FlexibleWorkSchedule
from .periods import get_half_month_period
from .serializers import (
    SkillTagSerializer,
    MemberSkillSerializer,
    FlexibleWorkScheduleSerializer,
    FlexibleWorkScheduleCreateSerializer,
    MemberSerializer,
    MemberListSerializer,
    MemberDetailSerializer,
    CURRENT_TEAM_MEMBERSHIP_STATUSES,
    TEAM_MEMBER_ROLE_PRIORITY,
)


class MemberViewSet(MultiSerializerMixin, ReadOnlyModelViewSet):
    """
    成员管理 ViewSet（只读）
    - list: 所有认证用户可查看成员列表（含联系方式）
    - retrieve: 所有认证用户可查看成员详情（含联系方式和参与项目）
    """
    queryset = User.objects.all().order_by('-date_joined')

    serializer_classes_by_action = {
        'list': MemberListSerializer,
        'retrieve': MemberSerializer,
    }

    permission_classes = [IsAuthenticated]

    filterset_fields = [
        'global_role', 'membership_status', 'is_active', 'is_student',
    ]
    # SearchFilter cannot preserve pinyin matches because it applies a second
    # database-only search after our member matcher. Keep exact dropdown
    # filtering through DjangoFilterBackend and handle text search below.
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['date_joined', 'name']

    @staticmethod
    def _first_query_value(query_params, *names):
        for name in names:
            value = normalize_search_text(query_params.get(name, ''))
            if value:
                return value
        return ''

    def _apply_member_field_text_filters(self, queryset):
        """Apply partial text matching to free-text directory fields."""
        query_params = self.request.query_params
        for field_name in ('school', 'grade', 'major'):
            value = self._first_query_value(
                query_params,
                field_name,
                f'{field_name}_search',
                f'{field_name}_text',
            )
            if value:
                queryset = queryset.filter(
                    **{f'{field_name}__icontains': value},
                )

            exact_value = self._first_query_value(
                query_params,
                f'{field_name}_exact',
            )
            if exact_value:
                queryset = queryset.filter(
                    **{f'{field_name}__iexact': exact_value},
                )
        return queryset

    @staticmethod
    def _member_text_values(member, *, team_id=None):
        """Build general, role-only, and status-only searchable values."""
        from apps.common.team_models import TeamMember

        role_labels = dict(TeamMember.Role.choices)
        memberships = list(getattr(
            member,
            'prefetched_current_team_memberships',
            [],
        ))
        owned_teams = list(getattr(
            member,
            'prefetched_context_owned_teams',
            [],
        ))
        role_values = [
            member.global_role,
            member.get_global_role_display(),
        ]
        status_values = [
            member.membership_status,
            member.get_membership_status_display(),
            '启用' if member.is_active else '停用',
            'active' if member.is_active else 'inactive',
        ]
        if team_id is not None:
            memberships = [
                membership
                for membership in memberships
                if membership.team_id == team_id
            ]
            owned_teams = [
                team for team in owned_teams if team.id == team_id
            ]

        role_priority = getattr(member, '_team_role_priority', None)
        if role_priority is not None:
            try:
                team_role = TEAM_MEMBER_ROLE_PRIORITY[int(role_priority)]
            except (IndexError, TypeError, ValueError):
                team_role = ''
            if team_role:
                role_values.extend([
                    team_role,
                    role_labels.get(team_role, ''),
                ])

        association_values = []
        for membership in memberships:
            role_values.extend([
                membership.role,
                membership.get_role_display(),
            ])
            status_values.extend([
                membership.status,
                membership.get_status_display(),
            ])
            association_values.extend([
                membership.team.name,
                (
                    membership.team.parent.name
                    if membership.team.parent
                    else ''
                ),
            ])
        for team in owned_teams:
            association_values.extend([
                team.name,
                (
                    team.parent.name
                    if team_id is None and team.parent
                    else ''
                ),
            ])

        general_values = [
            member.name,
            member.username,
            member.phone,
            member.email,
            member.school,
            member.major,
            member.grade,
            *role_values,
            *status_values,
            *association_values,
        ]
        return general_values, role_values, status_values

    def _apply_member_text_search(self, queryset):
        """Apply normalized substring, Chinese-name pinyin, and initials search."""
        query_params = self.request.query_params
        keyword = self._first_query_value(
            query_params,
            'search',
            'keyword',
            'q',
        )
        role_text = self._first_query_value(
            query_params,
            'role_search',
            'role_text',
            'team_role_search',
            'global_role_search',
        )
        status_text = self._first_query_value(
            query_params,
            'status_search',
            'status_text',
            'membership_status_search',
        )
        if not any((keyword, role_text, status_text)):
            return queryset

        raw_team_id = query_params.get('team')
        try:
            team_id = (
                int(raw_team_id)
                if raw_team_id not in (None, '')
                else None
            )
        except (TypeError, ValueError):
            team_id = None
        matching_ids = []
        for member in queryset:
            general_values, role_values, status_values = (
                self._member_text_values(member, team_id=team_id)
            )
            if keyword and not member_matches_search(
                query=keyword,
                values=general_values,
                name=member.name,
            ):
                continue
            if role_text and not member_matches_search(
                query=role_text,
                values=role_values,
                name='',
            ):
                continue
            if status_text and not member_matches_search(
                query=status_text,
                values=status_values,
                name='',
            ):
                continue
            matching_ids.append(member.id)
        return queryset.filter(pk__in=matching_ids)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self._apply_member_field_text_filters(queryset)
        return self._apply_member_text_search(queryset)

    def get_queryset(self):
        from apps.common.team_models import Team, TeamMember

        queryset = super().get_queryset()
        if is_external_collaborator(self.request.user):
            return queryset.filter(pk=self.request.user.pk)

        root_ids = active_user_root_team_ids(self.request.user)
        queryset = scope_organization_users(queryset, self.request.user)
        current_statuses = list(CURRENT_TEAM_MEMBERSHIP_STATUSES)

        # Global roles historically received a broad member directory. Once
        # they are attached to a root organization, this endpoint follows that
        # tenant context so identities from another root cannot affect either
        # visibility or importance.
        if root_ids:
            queryset = queryset.filter(
                Q(
                    teammember__team_id__in=root_ids,
                    teammember__status__in=current_statuses,
                )
                | Q(
                    teammember__team__parent_id__in=root_ids,
                    teammember__status__in=current_statuses,
                )
                | Q(owned_teams__id__in=root_ids)
                | Q(owned_teams__parent_id__in=root_ids)
            ).distinct()

        raw_team_id = self.request.query_params.get('team')
        team_id = None
        if raw_team_id not in (None, ''):
            try:
                team_id = int(raw_team_id)
            except (TypeError, ValueError):
                return queryset.none()
            team = Team.objects.filter(pk=team_id, is_active=True).only(
                'id',
                'parent_id',
            ).first()
            if team is None:
                return queryset.none()
            target_root_id = team.parent_id or team.id
            if root_ids and target_root_id not in root_ids:
                return queryset.none()

        membership_scope = Q(
            teammember__status__in=current_statuses,
        )
        owner_scope = Team.objects.filter(
            owner_id=OuterRef('pk'),
            is_active=True,
        )
        if team_id is not None:
            membership_scope &= Q(teammember__team_id=team_id)
            owner_scope = owner_scope.filter(pk=team_id)
        elif root_ids:
            membership_scope &= (
                Q(teammember__team_id__in=root_ids)
                | Q(teammember__team__parent_id__in=root_ids)
            )
            owner_scope = owner_scope.filter(
                Q(id__in=root_ids) | Q(parent_id__in=root_ids)
            )

        queryset = queryset.annotate(
            _owns_context_team=Exists(owner_scope),
        )
        if team_id is not None:
            queryset = queryset.filter(
                membership_scope | Q(_owns_context_team=True)
            ).distinct()

        role_value = (
            self.request.query_params.get('team_role')
            or self.request.query_params.get('role')
            or ''
        ).strip()
        if role_value:
            if role_value not in TEAM_MEMBER_ROLE_PRIORITY:
                return queryset.none()

        role_case = Case(
            *[
                When(
                    membership_scope
                    & Q(teammember__role=role),
                    then=Value(priority),
                )
                for priority, role in enumerate(TEAM_MEMBER_ROLE_PRIORITY)
            ],
            default=Value(len(TEAM_MEMBER_ROLE_PRIORITY)),
            output_field=IntegerField(),
        )
        queryset = queryset.annotate(
            _membership_role_priority=Min(role_case),
        ).annotate(
            _team_role_priority=Case(
                When(_membership_role_priority=0, then=Value(0)),
                When(_owns_context_team=True, then=Value(1)),
                default=F('_membership_role_priority'),
                output_field=IntegerField(),
            ),
        ).order_by(
            '_team_role_priority',
            'name',
            'email',
            'id',
        )
        if role_value:
            queryset = queryset.filter(
                _team_role_priority=TEAM_MEMBER_ROLE_PRIORITY.index(
                    role_value,
                )
            )

        membership_prefetch = TeamMember.objects.filter(
            status__in=current_statuses,
        ).select_related('team', 'team__parent')
        if root_ids:
            membership_prefetch = membership_prefetch.filter(
                Q(team_id__in=root_ids)
                | Q(team__parent_id__in=root_ids)
            )
        owned_team_prefetch = Team.objects.filter(
            is_active=True,
        ).select_related('parent')
        if root_ids:
            owned_team_prefetch = owned_team_prefetch.filter(
                Q(id__in=root_ids) | Q(parent_id__in=root_ids)
            )
        return queryset.prefetch_related(
            Prefetch(
                'teammember_set',
                queryset=membership_prefetch,
                to_attr='prefetched_current_team_memberships',
            ),
            Prefetch(
                'owned_teams',
                queryset=owned_team_prefetch,
                to_attr='prefetched_context_owned_teams',
            ),
        )

    def get_serializer_class(self):
        if is_external_collaborator(self.request.user):
            return ExternalCollaboratorUserSerializer
        return super().get_serializer_class()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='team_role',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=list(TEAM_MEMBER_ROLE_PRIORITY),
                description=(
                    '按当前查询上下文中的最高团队身份筛选；'
                    '指定 team 时仅计算该团队身份。'
                ),
            ),
            OpenApiParameter(
                name='role',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=list(TEAM_MEMBER_ROLE_PRIORITY),
                description='team_role 的兼容别名。',
            ),
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    '通用关键词；支持姓名、用户名、手机号、邮箱、学校、'
                    '专业、年级、团队名、角色与状态，并支持中文姓名全拼、'
                    '拼音首字母和单字符搜索。'
                ),
            ),
            OpenApiParameter(
                name='role_search',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='按全局或团队角色编码/显示词进行部分匹配。',
            ),
            OpenApiParameter(
                name='status_search',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='按账号或成员状态编码/显示词进行部分匹配。',
            ),
            OpenApiParameter(
                name='school',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='学校名称，大小写不敏感的部分匹配。',
            ),
            OpenApiParameter(
                name='grade',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='年级，大小写不敏感的部分匹配。',
            ),
            OpenApiParameter(
                name='major',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description='专业，大小写不敏感的部分匹配。',
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        """成员列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """成员详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)


class SkillTagViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    技能标签管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 仅管理员可管理
    """
    queryset = SkillTag.objects.all()
    serializer_class = SkillTagSerializer

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsSysAdmin],
        'update': [IsSysAdmin],
        'partial_update': [IsSysAdmin],
        'destroy': [IsSysAdmin],
    }
    permission_classes = [IsAuthenticated]

    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def list(self, request, *args, **kwargs):
        """技能标签列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """技能标签详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """创建技能标签（仅管理员）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = serializer.save()
        return success_response(
            SkillTagSerializer(tag).data,
            message='技能标签创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新技能标签（仅管理员）"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        tag = serializer.save()
        return success_response(SkillTagSerializer(tag).data, message='技能标签更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除技能标签（仅管理员）"""
        instance = self.get_object()
        instance.delete()
        return success_response(message='技能标签删除成功')


class MemberSkillViewSet(MultiSerializerMixin, ModelViewSet):
    """
    成员技能管理 ViewSet
    - list: 当前用户的技能列表
    - create/update: 添加/修改自己的技能
    - by_user: 查看指定用户的技能（所有登录成员可见）
    - retrieve: 查看技能详情
    """
    queryset = MemberSkill.objects.select_related('user', 'skill').all()
    serializer_class = MemberSkillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """默认返回当前用户的技能"""
        if self.action == 'by_user':
            # by_user action 返回指定用户的技能
            return self.queryset
        # 默认只返回当前用户的技能
        return self.queryset.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """当前用户的技能列表"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """技能详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """添加自己的技能"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 强制设置为当前用户
        serializer.validated_data['user'] = request.user
        # 检查是否已存在
        skill_id = serializer.validated_data.get('skill')
        if MemberSkill.objects.filter(user=request.user, skill=skill_id).exists():
            return error_response(message='您已添加过该技能，请直接修改', code=1007,
                                  http_status=status.HTTP_400_BAD_REQUEST)
        skill = serializer.save()
        return success_response(
            MemberSkillSerializer(skill).data,
            message='技能添加成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """修改自己的技能"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # 权限校验：只能修改自己的技能
        if instance.user_id != request.user.id:
            return error_response(message='只能修改自己的技能', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)
        # 不允许修改 user 字段
        data = request.data.copy()
        data.pop('user', None)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        skill = serializer.save()
        return success_response(MemberSkillSerializer(skill).data, message='技能修改成功')

    def partial_update(self, request, *args, **kwargs):
        """部分修改自己的技能"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除自己的技能"""
        instance = self.get_object()
        # 权限校验：只能删除自己的技能
        if instance.user_id != request.user.id:
            return error_response(message='只能删除自己的技能', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return success_response(message='技能删除成功')

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """
        查看指定用户的技能（所有登录成员可见）
        GET /api/v1/members/skills/by_user/?user_id=1
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return error_response(message='请提供 user_id 参数')
        if (
            is_external_collaborator(request.user)
            and str(request.user.id) != str(user_id)
        ):
            return error_response(
                message='外部协作者只能查看自己的技能',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = scope_organization_users(
                User.objects.filter(is_active=True),
                request.user,
            ).get(id=user_id)
        except User.DoesNotExist:
            return error_response(message='用户不存在', code=1004,
                                  http_status=status.HTTP_404_NOT_FOUND)

        skills = MemberSkill.objects.filter(user=user).select_related('skill')
        serializer = MemberSkillSerializer(skills, many=True)
        return success_response(serializer.data)


class FlexibleWorkScheduleViewSet(MultiSerializerMixin, ModelViewSet):
    """
    灵活工时管理 ViewSet
    - list: 当前用户的灵活工作时间
    - create: 填写（每半月一次，检查 unique_together）
    - current_period: 获取当前半月周期
    - all_latest: 所有成员最新灵活工作时间（所有登录成员可见）
    - by_user: 查看指定用户的灵活工作时间
    """
    queryset = FlexibleWorkSchedule.objects.select_related('user').all()

    serializer_classes_by_action = {
        'list': FlexibleWorkScheduleSerializer,
        'retrieve': FlexibleWorkScheduleSerializer,
        'create': FlexibleWorkScheduleCreateSerializer,
        'update': FlexibleWorkScheduleCreateSerializer,
        'partial_update': FlexibleWorkScheduleCreateSerializer,
    }
    permission_classes = [IsAuthenticated]

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        """默认返回当前用户的灵活工时"""
        if self.action in ('all_latest', 'by_user'):
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """当前用户的灵活工作时间列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """灵活工时详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """填写灵活工时（每半月一次）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 检查当前周期是否已填写
        period_start = serializer.validated_data.get('period_start')
        if FlexibleWorkSchedule.objects.filter(
            user=request.user, period_start=period_start
        ).exists():
            return error_response(
                message='当前周期已填写灵活工作时间，请勿重复填写',
                code=1007,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        schedule = serializer.save()
        return success_response(
            FlexibleWorkScheduleSerializer(schedule).data,
            message='灵活工作时间填写成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """修改自己的灵活工时"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # 权限校验：只能修改自己的灵活工时
        if instance.user_id != request.user.id:
            return error_response(message='只能修改自己的灵活工作时间', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)
        # 不允许修改 user 字段
        data = request.data.copy()
        data.pop('user', None)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        return success_response(
            FlexibleWorkScheduleSerializer(schedule).data,
            message='灵活工作时间更新成功',
        )

    def partial_update(self, request, *args, **kwargs):
        """部分修改自己的灵活工时"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """删除自己的灵活工时"""
        instance = self.get_object()
        if instance.user_id != request.user.id:
            return error_response(message='只能删除自己的灵活工作时间', code=1003,
                                  http_status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return success_response(message='灵活工作时间删除成功')

    @action(detail=False, methods=['get'])
    def current_period(self, request):
        """
        获取当前半月周期
        GET /api/v1/members/work-schedules/current_period/
        返回当前半月周期的起止日期及当前用户是否已填写
        """
        today = timezone.now().date()
        period_start, period_end = get_half_month_period(today)

        # 检查当前用户是否已填写
        filled = FlexibleWorkSchedule.objects.filter(
            user=request.user, period_start=period_start
        ).first()

        result = {
            'period_start': period_start,
            'period_end': period_end,
            'is_filled': filled is not None,
        }
        if filled:
            result['schedule'] = FlexibleWorkScheduleSerializer(filled).data
        return success_response(result)

    @action(detail=False, methods=['get'])
    def all_latest(self, request):
        """
        所有成员最新灵活工作时间（所有登录成员可见）
        GET /api/v1/members/work-schedules/all_latest/
        返回每个成员最新的一条灵活工时记录
        """
        if is_external_collaborator(request.user):
            return error_response(
                message='外部协作者无权查看团队排期',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        # 获取所有活跃用户的最新灵活工时
        users = scope_organization_users(
            User.objects.filter(is_active=True),
            request.user,
        ).order_by('name')
        result = []
        for user in users:
            schedule = FlexibleWorkSchedule.objects.filter(user=user).first()
            if schedule:
                result.append(FlexibleWorkScheduleSerializer(schedule).data)
        return success_response(result)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """
        查看指定用户的灵活工作时间（所有登录成员可见）
        GET /api/v1/members/work-schedules/by_user/?user_id=1
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return error_response(message='请提供 user_id 参数')
        if (
            is_external_collaborator(request.user)
            and str(request.user.id) != str(user_id)
        ):
            return error_response(
                message='外部协作者只能查看自己的灵活工时',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = scope_organization_users(
                User.objects.filter(is_active=True),
                request.user,
            ).get(id=user_id)
        except User.DoesNotExist:
            return error_response(message='用户不存在', code=1004,
                                  http_status=status.HTTP_404_NOT_FOUND)

        schedules = FlexibleWorkSchedule.objects.filter(user=user).select_related('user')
        serializer = FlexibleWorkScheduleSerializer(schedules, many=True)
        return success_response(serializer.data)


class MemberDetailView(APIView):
    """
    成员详情视图
    GET /api/v1/members/detail/?user_id=1
    返回成员基本信息 + 技能列表 + 灵活工作时间 + 参与项目 + 任务
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='成员 ID；省略时返回当前登录用户。',
            ),
        ],
        responses={
            200: success_response_schema(
                'MemberDetailResponse',
                MemberDetailSerializer(),
            ),
        },
    )
    def get(self, request):
        """获取成员详情"""
        user_id = request.query_params.get('user_id') or request.user.id
        if (
            is_external_collaborator(request.user)
            and str(request.user.id) != str(user_id)
        ):
            return error_response(
                message='外部协作者只能查看自己的成员档案',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = scope_organization_users(
                User.objects.filter(is_active=True),
                request.user,
            ).get(id=user_id)
        except User.DoesNotExist:
            return error_response(message='用户不存在', code=1004,
                                  http_status=status.HTTP_404_NOT_FOUND)

        serializer = MemberDetailSerializer(
            user,
            context={'request': request},
        )
        return success_response(serializer.data)


class MemberGrowthTimelineView(APIView):
    """
    成员成长时间线
    GET /api/v1/members/growth-timeline/?user_id=1
    聚合成员的贡献记录、项目参与、比赛、知识产权、任务完成等,按时间倒序返回成长事件
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='成员 ID；省略时返回当前登录用户。',
            ),
        ],
        responses={
            200: success_response_schema(
                'MemberGrowthTimelineResponse',
                inline_serializer(
                    name='MemberGrowthTimelineData',
                    fields={
                        'user_id': serializers.IntegerField(),
                        'user_name': serializers.CharField(),
                        'contrib_summary': inline_serializer(
                            name='MemberGrowthContributionSummary',
                            fields={
                                'total': serializers.IntegerField(),
                                'approved': serializers.IntegerField(),
                                'pending': serializers.IntegerField(),
                                'total_weight': serializers.FloatField(),
                            },
                        ),
                        'events': inline_serializer(
                            name='MemberGrowthEvent',
                            fields={
                                'id': serializers.CharField(),
                                'type': serializers.CharField(),
                                'title': serializers.CharField(),
                                'description': serializers.CharField(),
                                'timestamp': serializers.DateTimeField(allow_null=True),
                                'date': serializers.DateField(allow_null=True),
                                'project_name': serializers.CharField(),
                                'metadata': serializers.JSONField(),
                            },
                            many=True,
                        ),
                        'total_events': serializers.IntegerField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        from apps.contributions.models import Contribution
        from apps.competitions.models import Competition
        from apps.intellectual_property.models import (
            IntellectualPropertyApplication,
            IPApplicationContributor,
        )
        from apps.tasks.models import Task
        from apps.projects.models import (
            Project,
            ProjectMember,
            ProjectMembershipEvent,
        )
        from common.project_access import scope_project_queryset
        from apps.intellectual_property.permissions import (
            accessible_ip_applications,
        )
        from apps.users.models import UserLifecycleEvent

        user_id = request.query_params.get('user_id') or request.user.id
        if (
            is_external_collaborator(request.user)
            and str(request.user.id) != str(user_id)
        ):
            return error_response(
                message='外部协作者只能查看自己的成长记录',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            user = scope_organization_users(
                User.objects.all(),
                request.user,
            ).get(id=user_id)
        except User.DoesNotExist:
            return error_response(message='用户不存在', code=1004,
                                  http_status=status.HTTP_404_NOT_FOUND)

        events = []
        visible_project_ids = scope_project_queryset(
            Project.objects.all(),
            request.user,
            project_lookup='',
        ).values_list('id', flat=True)

        # 1. 贡献记录
        contribs = Contribution.objects.filter(
            user=user,
            project_id__in=visible_project_ids,
        ).select_related('project').order_by('-created_at')
        contrib_summary = {
            'total': contribs.count(),
            'approved': contribs.filter(status='approved').count(),
            'pending': contribs.filter(status='pending').count(),
            'total_weight': sum(c.weight for c in contribs),
        }
        for c in contribs[:100]:
            events.append({
                'id': f'contrib_{c.id}',
                'type': 'contribution',
                'title': c.get_contribution_type_display(),
                'description': c.content[:80] if c.content else c.description[:80],
                'timestamp': c.created_at.isoformat() if c.created_at else None,
                'date': c.created_at.date().isoformat() if c.created_at else None,
                'project_name': c.project.name if c.project else '',
                'metadata': {
                    'status': c.status,
                    'weight': str(c.weight),
                    'score': str(c.score),
                },
            })

        # 2. 项目参与
        memberships = ProjectMember.objects.filter(
            user=user,
            project_id__in=visible_project_ids,
        ).select_related('project').order_by('-joined_at')
        for m in memberships:
            events.append({
                'id': f'project_join_{m.id}',
                'type': 'project_join',
                'title': f'加入项目: {m.project.name}',
                'description': f'角色: {m.get_role_in_project_display()}',
                'timestamp': m.joined_at.isoformat() if m.joined_at else None,
                'date': m.joined_at.date().isoformat() if m.joined_at else None,
                'project_name': m.project.name,
                'metadata': {
                    'project_id': m.project_id,
                    'role_in_project': m.role_in_project,
                },
            })

        # 2.1 项目角色、暂离、退出和交接记录
        membership_events = ProjectMembershipEvent.objects.filter(
            membership__user=user,
            membership__project_id__in=visible_project_ids,
        ).select_related('membership__project', 'handover_to__user', 'operator')
        for item in membership_events:
            if item.event_type == ProjectMembershipEvent.EventType.JOINED:
                continue
            detail_parts = []
            if item.from_role != item.to_role:
                detail_parts.append(f'角色：{item.from_role or "-"} → {item.to_role or "-"}')
            if item.from_status != item.to_status:
                detail_parts.append(f'状态：{item.from_status or "-"} → {item.to_status or "-"}')
            if item.handover_to:
                detail_parts.append(f'交接给：{item.handover_to.user.name}')
            if item.reason:
                detail_parts.append(f'原因：{item.reason}')
            events.append({
                'id': f'project_membership_{item.id}',
                'type': 'project_membership',
                'title': f'{item.get_event_type_display()}: {item.membership.project.name}',
                'description': '；'.join(detail_parts),
                'timestamp': item.created_at.isoformat(),
                'date': item.created_at.date().isoformat(),
                'project_name': item.membership.project.name,
                'metadata': {'event_type': item.event_type},
            })

        # 2.2 团队成员生命周期
        for item in UserLifecycleEvent.objects.filter(user=user).select_related(
            'handover_to', 'operator'
        ):
            detail_parts = []
            if item.from_status != item.to_status:
                detail_parts.append(f'状态：{item.from_status or "-"} → {item.to_status or "-"}')
            if item.from_role != item.to_role:
                detail_parts.append(f'角色：{item.from_role or "-"} → {item.to_role or "-"}')
            if item.handover_to:
                detail_parts.append(f'交接给：{item.handover_to.name}')
            if item.reason:
                detail_parts.append(f'原因：{item.reason}')
            events.append({
                'id': f'user_lifecycle_{item.id}',
                'type': 'member_status',
                'title': item.get_event_type_display(),
                'description': '；'.join(detail_parts),
                'timestamp': item.created_at.isoformat(),
                'date': item.created_at.date().isoformat(),
                'project_name': '',
                'metadata': {'event_type': item.event_type},
            })

        # 3. 比赛参与(通过项目关联)
        comp_qs = Competition.objects.filter(
            project__members__user=user,
            project_id__in=visible_project_ids,
        ).select_related('project').distinct()
        for comp in comp_qs:
            if comp.result_date:
                events.append({
                    'id': f'competition_{comp.id}',
                    'type': 'competition',
                    'title': f'比赛: {comp.name}',
                    'description': f'{comp.get_level_display()} - {"获奖: " + comp.award_level if comp.is_awarded else "未获奖"}',
                    'timestamp': f'{comp.result_date}T00:00:00',
                    'date': comp.result_date.isoformat(),
                    'project_name': comp.project.name if comp.project else '',
                    'metadata': {
                        'level': comp.level,
                        'is_awarded': comp.is_awarded,
                        'award_level': comp.award_level,
                        'is_promoted': comp.is_promoted,
                    },
                })

        # 4. 知识产权贡献
        ip_contribs = IPApplicationContributor.objects.filter(
            user=user,
            application_id__in=accessible_ip_applications(
                request.user,
            ).values_list('id', flat=True),
        ).select_related(
            'application'
        ).order_by('-created_at')
        for ic in ip_contribs:
            events.append({
                'id': f'ip_contrib_{ic.id}',
                'type': 'ip_contribution',
                'title': f'知识产权: {ic.application.title}',
                'description': f'{ic.get_role_display()} - {ic.contribution_description[:60] if ic.contribution_description else ""}',
                'timestamp': ic.created_at.isoformat() if ic.created_at else None,
                'date': ic.created_at.date().isoformat() if ic.created_at else None,
                'project_name': ic.application.related_project.name if ic.application.related_project else '',
                'metadata': {
                    'ip_id': ic.application_id,
                    'ip_status': ic.application.status,
                    'is_confirmed': ic.is_confirmed,
                },
            })

        # 5. 任务完成
        done_tasks = Task.objects.filter(
            assignee=user,
            status='done',
            project_id__in=visible_project_ids,
        ).select_related('project').order_by('-completed_at')
        for t in done_tasks[:50]:
            events.append({
                'id': f'task_done_{t.id}',
                'type': 'task_completed',
                'title': f'完成任务: {t.title}',
                'description': f'{t.project.name if t.project else ""}',
                'timestamp': t.completed_at.isoformat() if t.completed_at else None,
                'date': t.completed_at.date().isoformat() if t.completed_at else None,
                'project_name': t.project.name if t.project else '',
                'metadata': {'task_id': t.id},
            })

        # 按时间倒序
        events.sort(key=lambda x: x.get('timestamp') or '', reverse=True)

        data = {
            'user_id': user.id,
            'user_name': user.name,
            'contrib_summary': contrib_summary,
            'events': events[:200],
            'total_events': len(events),
        }
        return success_response(data, message='success')
