"""
项目序列化器
"""
from decimal import Decimal

from rest_framework import serializers
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema_field

from common.project_access import (
    active_user_root_team_ids,
    is_external_collaborator,
    project_can_manage,
    project_root_team_ids,
    user_can_join_project,
)
from .models import Project, ProjectMember, ProjectMembershipEvent, ProjectStageLog
from apps.common.team_models import Team, TeamMember
from apps.users.serializers import (
    ExternalCollaboratorUserSerializer,
    UserListSerializer,
)


def _validate_project_leader(attrs, *, instance=None, request=None):
    """Validate that a project leader is active and belongs to its selected teams."""
    leader = attrs.get('leader', getattr(instance, 'leader', None))
    if leader is None:
        return attrs
    if (
        not leader.is_active
        or getattr(leader, 'membership_status', '') != 'active'
    ):
        raise serializers.ValidationError({
            'leader': '项目牵头负责人必须是在队且账号有效的团队成员'
        })

    if 'teams' in attrs:
        selected_teams = list(attrs['teams'])
    elif instance is not None:
        selected_teams = list(instance.teams.all())
    else:
        selected_teams = []
    if not selected_teams:
        return attrs
    selected_root_ids = {
        team.parent_id or team.id
        for team in selected_teams
    }
    if len(selected_root_ids) > 1:
        raise serializers.ValidationError({
            'teams': '一个项目只能归属于一个总团队'
        })

    operator = getattr(request, 'user', None)
    if operator and operator.global_role == 'sys_admin':
        return attrs

    selected_team_ids = {team.id for team in selected_teams}
    root_team_ids = {
        team.id for team in selected_teams if team.parent_id is None
    }
    eligible_team_ids = set(selected_team_ids)
    if root_team_ids:
        eligible_team_ids.update(
            Team.objects.filter(
                parent_id__in=root_team_ids,
                is_active=True,
            ).values_list('id', flat=True)
        )
    belongs_to_selected_team = (
        Team.objects.filter(
            id__in=eligible_team_ids,
            owner=leader,
            is_active=True,
        ).exists()
        or TeamMember.objects.filter(
            team_id__in=eligible_team_ids,
            user=leader,
            status=TeamMember.Status.ACTIVE,
            team__is_active=True,
        ).exists()
    )
    if not belongs_to_selected_team:
        raise serializers.ValidationError({
            'leader': '项目牵头负责人必须是所选团队或其直属小团队的活动成员'
        })
    return attrs


def _validate_project_organization_transition(attrs, *, instance=None, request=None):
    """阻止项目负责人借更新 leader/teams 把项目迁到另一根团队。"""
    if instance is None:
        return attrs
    operator = getattr(request, 'user', None)

    active_root_ids = set(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)
    )
    if not active_root_ids:
        # 完全没有 Team 的旧部署维持原有更新行为。
        return attrs

    current_project_roots = project_root_team_ids(instance)
    original_leader_roots = active_user_root_team_ids(instance.leader)
    operator_roots = active_user_root_team_ids(operator) if operator else set()

    if current_project_roots:
        allowed_roots = current_project_roots
    elif len(active_root_ids) == 1 and (
        active_root_ids & (original_leader_roots | operator_roots)
    ):
        allowed_roots = active_root_ids
    else:
        # 多根部署中的未关联旧项目只能以原负责人所属组织为锚点。
        allowed_roots = original_leader_roots

    if 'teams' in attrs:
        selected_teams = list(attrs['teams'])
        selected_roots = {
            team.parent_id or team.id
            for team in selected_teams
        }
        if current_project_roots and not selected_roots:
            raise serializers.ValidationError({
                'teams': '已归属团队的项目不能清空关联团队'
            })
        if selected_roots and (
            not allowed_roots
            or not selected_roots.issubset(allowed_roots)
        ):
            raise serializers.ValidationError({
                'teams': '项目不能迁移到另一总团队'
            })

    new_leader = attrs.get('leader')
    if new_leader is not None and new_leader.id != instance.leader_id:
        target_roots = active_user_root_team_ids(new_leader)
        if allowed_roots and not (target_roots & allowed_roots):
            raise serializers.ValidationError({
                'leader': '新负责人必须属于项目当前所在的总团队'
            })
        if not allowed_roots and len(active_root_ids) > 1:
            raise serializers.ValidationError({
                'leader': '未归属团队的旧项目需先由系统管理员确认组织范围'
            })
    return attrs


def _project_leader_names(project):
    names = [project.leader.name] if project.leader_id else []
    prefetched_members = getattr(
        project,
        '_prefetched_objects_cache',
        {},
    ).get('members')
    if prefetched_members is not None:
        co_leader_names = [
            member.user.name
            for member in prefetched_members
            if (
                member.role_in_project == ProjectMember.RoleInProject.LEADER
                and member.status == ProjectMember.Status.ACTIVE
                and member.user_id != project.leader_id
            )
        ]
    else:
        co_leader_names = project.members.filter(
            role_in_project=ProjectMember.RoleInProject.LEADER,
            status=ProjectMember.Status.ACTIVE,
        ).exclude(user_id=project.leader_id).values_list('user__name', flat=True)
    names.extend(co_leader_names)
    return names


def _project_team_names(project):
    prefetched_teams = getattr(
        project,
        '_prefetched_objects_cache',
        {},
    ).get('teams')
    if prefetched_teams is not None:
        return [team.name for team in prefetched_teams]
    return list(project.teams.values_list('name', flat=True))


def _has_custom_project_manage_permission(context, user, project_id):
    """Resolve all project-management role grants once per serializer request."""
    cache_key = '_project_manage_permission_scope'
    cached_scope = context.get(cache_key)
    if cached_scope is None or cached_scope[0] != user.id:
        has_global_grant = False
        granted_project_ids = set()
        assignments = user.role_assignments.select_related('role').only(
            'project_id',
            'role__permissions',
        )
        for assignment in assignments:
            if 'project.manage' not in (assignment.role.permissions or []):
                continue
            if assignment.project_id is None:
                has_global_grant = True
            else:
                granted_project_ids.add(assignment.project_id)
        cached_scope = (user.id, has_global_grant, granted_project_ids)
        context[cache_key] = cached_scope
    return cached_scope[1] or project_id in cached_scope[2]


class ProjectStageLogSerializer(serializers.ModelSerializer):
    """项目阶段日志序列化器"""
    operator_name = serializers.CharField(source='operator.name', read_only=True, default='')
    from_stage_display = serializers.CharField(source='get_from_stage_display', read_only=True)
    to_stage_display = serializers.CharField(source='get_to_stage_display', read_only=True)

    class Meta:
        model = ProjectStageLog
        fields = (
            'id', 'project', 'from_stage', 'from_stage_display',
            'to_stage', 'to_stage_display', 'operator', 'operator_name',
            'note', 'created_at',
        )
        read_only_fields = ('id', 'project', 'operator', 'created_at')


class ProjectMemberSerializer(serializers.ModelSerializer):
    """项目成员序列化器"""
    user_detail = serializers.SerializerMethodField()
    role_in_project_display = serializers.CharField(source='get_role_in_project_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    handover_to_name = serializers.CharField(source='handover_to.user.name', read_only=True, default='')

    class Meta:
        model = ProjectMember
        fields = (
            'id', 'project', 'user', 'user_detail',
            'role_in_project', 'role_in_project_display', 'joined_at',
            'status', 'status_display', 'exited_at', 'exit_reason',
            'handover_to', 'handover_to_name', 'handover_notes',
        )
        read_only_fields = ('id', 'joined_at')

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name='ProjectMemberUserDetail',
            serializers=[
                ExternalCollaboratorUserSerializer,
                UserListSerializer,
            ],
            resource_type_field_name=None,
        )
    )
    def get_user_detail(self, obj):
        request = self.context.get('request')
        serializer_class = (
            ExternalCollaboratorUserSerializer
            if request and is_external_collaborator(request.user)
            else UserListSerializer
        )
        return serializer_class(obj.user, context=self.context).data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get('project', getattr(self.instance, 'project', None))
        user = attrs.get('user', getattr(self.instance, 'user', None))
        if (
            self.instance
            and 'project' in attrs
            and attrs['project'].pk != self.instance.project_id
        ):
            raise serializers.ValidationError({
                'project': '项目成员记录不能迁移到其他项目'
            })
        if (
            self.instance
            and 'user' in attrs
            and attrs['user'].pk != self.instance.user_id
        ):
            raise serializers.ValidationError({
                'user': '项目成员记录不能改绑为其他用户'
            })
        role = attrs.get(
            'role_in_project',
            getattr(self.instance, 'role_in_project', ProjectMember.RoleInProject.PARTICIPANT),
        )
        needs_scope_check = (
            self.instance is None
            or 'user' in attrs
            or 'role_in_project' in attrs
            or attrs.get('status') == ProjectMember.Status.ACTIVE
        )
        if (
            needs_scope_check
            and project
            and user
            and not user_can_join_project(user, project, role=role)
        ):
            raise serializers.ValidationError({
                'user': '项目成员必须属于同一总团队；外部协作者请使用外部协作者角色'
            })
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and is_external_collaborator(request.user):
            for field in (
                'exited_at', 'exit_reason', 'handover_to',
                'handover_to_name', 'handover_notes',
            ):
                data.pop(field, None)
        return data


class ProjectMembershipEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    operator_name = serializers.CharField(source='operator.name', read_only=True, default='')
    handover_to_name = serializers.CharField(source='handover_to.user.name', read_only=True, default='')

    class Meta:
        model = ProjectMembershipEvent
        fields = (
            'id', 'event_type', 'event_type_display', 'from_role', 'to_role',
            'from_status', 'to_status', 'reason', 'handover_to',
            'handover_to_name', 'handover_notes', 'operator', 'operator_name',
            'created_at',
        )
        read_only_fields = fields


class ProjectListSerializer(serializers.ModelSerializer):
    """项目列表精简序列化器"""
    leader_name = serializers.CharField(source='leader.name', read_only=True)
    current_stage_display = serializers.CharField(source='get_current_stage_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    member_count = serializers.SerializerMethodField()
    task_count = serializers.IntegerField(read_only=True)
    competition_count = serializers.IntegerField(read_only=True)
    finance_balance = serializers.SerializerMethodField()
    leader_names = serializers.SerializerMethodField()
    team_names = serializers.SerializerMethodField()
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'code', 'leader', 'leader_name', 'leader_names',
            'teams', 'team_names', 'visibility', 'visibility_display',
            'current_stage', 'current_stage_display',
            'status', 'status_display', 'priority', 'priority_display',
            'start_date', 'planned_end_date', 'actual_end_date',
            'intro',
            'last_leader_update', 'archived_at', 'is_archived',
            'member_count', 'task_count', 'competition_count',
            'finance_balance', 'created_at',
            'can_manage',
        )
        read_only_fields = fields

    def get_member_count(self, obj) -> int:
        annotated_count = getattr(obj, 'active_member_count', None)
        if annotated_count is not None:
            return annotated_count
        return obj.members.filter(status=ProjectMember.Status.ACTIVE).count()

    def get_leader_names(self, obj):
        return _project_leader_names(obj)

    def get_team_names(self, obj):
        return _project_team_names(obj)

    def get_can_manage(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(
            user
            and user.is_authenticated
            and (
                project_can_manage(user, obj)
                or _has_custom_project_manage_permission(
                    self.context,
                    user,
                    obj.id,
                )
            )
        )

    @extend_schema_field(
        serializers.DecimalField(
            max_digits=None,
            decimal_places=2,
            allow_null=True,
            read_only=True,
        )
    )
    def get_finance_balance(self, obj):
        """返回项目各预算周期的可用余额，列表查询已预取预算避免 N+1。"""
        request = self.context.get('request')
        if request and is_external_collaborator(request.user):
            return None
        budgets = obj.budgets.all()
        return sum((budget.remaining_amount for budget in budgets), Decimal('0'))


class ProjectSerializer(serializers.ModelSerializer):
    """项目详情序列化器"""
    leader_name = serializers.CharField(source='leader.name', read_only=True)
    current_stage_display = serializers.CharField(source='get_current_stage_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    stage_logs = ProjectStageLogSerializer(many=True, read_only=True)
    leader_names = serializers.SerializerMethodField()
    team_names = serializers.SerializerMethodField()
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'code', 'leader', 'leader_name', 'leader_names',
            'teams', 'team_names', 'visibility', 'visibility_display',
            'current_stage', 'current_stage_display',
            'status', 'status_display', 'priority', 'priority_display',
            'start_date', 'planned_end_date', 'actual_end_date',
            'intro', 'last_leader_update', 'archived_at', 'is_archived',
            'members', 'stage_logs',
            'can_manage',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'last_leader_update', 'archived_at', 'created_at', 'updated_at')

    def get_leader_names(self, obj):
        return _project_leader_names(obj)

    def get_team_names(self, obj):
        return _project_team_names(obj)

    def get_can_manage(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(
            user
            and user.is_authenticated
            and (
                project_can_manage(user, obj)
                or _has_custom_project_manage_permission(
                    self.context,
                    user,
                    obj.id,
                )
            )
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs = _validate_project_leader(
            attrs,
            instance=self.instance,
            request=self.context.get('request'),
        )
        return _validate_project_organization_transition(
            attrs,
            instance=self.instance,
            request=self.context.get('request'),
        )

    def update(self, instance, validated_data):
        project = super().update(instance, validated_data)
        membership, _ = ProjectMember.objects.get_or_create(
            project=project,
            user=project.leader,
            defaults={'role_in_project': ProjectMember.RoleInProject.LEADER},
        )
        update_fields = []
        if membership.role_in_project != ProjectMember.RoleInProject.LEADER:
            membership.role_in_project = ProjectMember.RoleInProject.LEADER
            update_fields.append('role_in_project')
        if membership.status != ProjectMember.Status.ACTIVE:
            membership.status = ProjectMember.Status.ACTIVE
            membership.exited_at = None
            update_fields.extend(['status', 'exited_at'])
        if update_fields:
            membership.save(update_fields=update_fields)
        return project


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'code', 'leader', 'current_stage',
            'status', 'priority', 'start_date', 'planned_end_date',
            'actual_end_date', 'intro', 'teams', 'visibility',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return _validate_project_leader(
            attrs,
            request=self.context.get('request'),
        )

    def create(self, validated_data):
        """创建项目时自动创建阶段日志和项目负责人成员记录"""
        project = super().create(validated_data)
        # 创建初始阶段日志
        ProjectStageLog.objects.create(
            project=project,
            from_stage=None,
            to_stage=project.current_stage,
            operator=self.context['request'].user if 'request' in self.context else None,
            note='项目创建',
        )
        # 自动将项目负责人加入项目成员
        membership = ProjectMember.objects.create(
            project=project,
            user=project.leader,
            role_in_project=ProjectMember.RoleInProject.LEADER,
        )
        ProjectMembershipEvent.objects.create(
            membership=membership,
            event_type=ProjectMembershipEvent.EventType.JOINED,
            to_role=membership.role_in_project,
            to_status=membership.status,
            operator=self.context['request'].user if 'request' in self.context else None,
        )
        return project
