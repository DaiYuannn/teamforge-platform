"""
成员序列化器
包含技能标签、成员技能、灵活工时、成员详情等序列化器
"""
from decimal import Decimal, InvalidOperation

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.users.models import User
from apps.users.serializers import UserListSerializer
from apps.projects.serializers import ProjectListSerializer
from .models import SkillTag, MemberSkill, FlexibleWorkSchedule


TEAM_MEMBER_ROLE_PRIORITY = (
    'teacher',
    'owner',
    'co_lead',
    'admin',
    'advisor',
    'member',
    'external',
)
TEAM_MEMBER_ROLE_PRIORITY_MAP = {
    role: priority
    for priority, role in enumerate(TEAM_MEMBER_ROLE_PRIORITY)
}
CURRENT_TEAM_MEMBERSHIP_STATUSES = ('active', 'on_leave')


def _viewer(serializer):
    request = serializer.context.get('request')
    return getattr(request, 'user', None)


def _get_active_team_memberships(user, viewer=None):
    """返回并稳定排列成员当前有效的团队关系。

    ``on_leave`` 仍是当前关系，只代表暂时无法投入，不应让成员从团队
    目录和详情中消失。已离队关系继续保留在历史记录中，不出现在这里。
    """
    from apps.common.team_models import TeamMember

    memberships = getattr(user, 'prefetched_current_team_memberships', None)
    if memberships is None:
        # 兼容仍使用旧预取属性的调用方。
        memberships = getattr(user, 'prefetched_active_team_memberships', None)
    if memberships is None:
        memberships = TeamMember.objects.filter(
            user=user,
            status__in=CURRENT_TEAM_MEMBERSHIP_STATUSES,
        ).select_related('team', 'team__parent')
    viewer_root_ids = set()
    if viewer and getattr(viewer, 'is_authenticated', False):
        from common.project_access import active_user_root_team_ids

        viewer_root_ids = active_user_root_team_ids(viewer)
    if viewer_root_ids:
        memberships = [
            membership
            for membership in memberships
            if (
                membership.team_id in viewer_root_ids
                or membership.team.parent_id in viewer_root_ids
            )
        ]
    memberships = sorted(
        memberships,
        key=lambda membership: (
            0 if membership.team.parent_id is None else 1,
            TEAM_MEMBER_ROLE_PRIORITY_MAP.get(
                membership.role,
                len(TEAM_MEMBER_ROLE_PRIORITY),
            ),
            0 if membership.status == TeamMember.Status.ACTIVE else 1,
            (membership.team.parent.name if membership.team.parent else ''),
            membership.team.name,
            membership.team_id,
            membership.id,
        ),
    )
    return [
        {
            'team_id': membership.team_id,
            'team_name': membership.team.name,
            'parent_id': membership.team.parent_id,
            'parent_name': membership.team.parent.name if membership.team.parent else '',
            'role': membership.role,
            'role_display': membership.get_role_display(),
            'status': membership.status,
        }
        for membership in memberships
    ]


class SkillTagSerializer(serializers.ModelSerializer):
    """技能标签序列化器"""

    class Meta:
        model = SkillTag
        fields = ('id', 'name', 'created_at')
        read_only_fields = ('id', 'created_at')


class MemberSkillSerializer(serializers.ModelSerializer):
    """成员技能序列化器"""
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = MemberSkill
        ref_name = 'TaggedMemberSkill'
        fields = ('id', 'user', 'user_name', 'skill', 'skill_name', 'proficiency', 'created_at')
        read_only_fields = ('id', 'created_at')


class FlexibleWorkScheduleSerializer(serializers.ModelSerializer):
    """成员可投入安排序列化器。"""
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = FlexibleWorkSchedule
        fields = (
            'id', 'user', 'user_name', 'period_start', 'period_end',
            'work_hours', 'detail', 'can_offline', 'can_urgent',
            'is_saturated', 'notes', 'filled_at',
        )
        read_only_fields = ('id', 'filled_at')


class FlexibleWorkScheduleCreateSerializer(serializers.ModelSerializer):
    """成员可投入安排创建序列化器（用户填写当前半月周期）。"""

    class Meta:
        model = FlexibleWorkSchedule
        fields = (
            'id', 'period_start', 'period_end',
            'work_hours', 'detail', 'can_offline', 'can_urgent',
            'is_saturated', 'notes',
        )
        read_only_fields = ('id',)

    def validate_work_hours(self, value):
        """兼容旧客户端的工时字段，禁止绕过前端提交负数。"""
        if value < 0:
            raise serializers.ValidationError('可用工时不能为负数')
        return value

    def validate(self, attrs):
        """校验周期及 detail.availability_windows 结构。"""
        period_start = attrs.get(
            'period_start',
            getattr(self.instance, 'period_start', None),
        )
        period_end = attrs.get(
            'period_end',
            getattr(self.instance, 'period_end', None),
        )
        if period_start and period_end and period_end <= period_start:
            raise serializers.ValidationError({'period_end': '时段结束必须晚于时段开始'})

        detail = attrs.get('detail', getattr(self.instance, 'detail', {})) or {}
        if not isinstance(detail, dict):
            raise serializers.ValidationError({'detail': '可投入安排必须为对象'})
        windows = detail.get('availability_windows', [])
        if not isinstance(windows, list):
            raise serializers.ValidationError({'detail': '可投入日期必须为列表'})

        normalized_windows = []
        total_capacity_days = Decimal('0')
        date_field = serializers.DateField()
        for index, window in enumerate(windows):
            if not isinstance(window, dict):
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个可投入日期格式不正确',
                })
            try:
                start_date = date_field.to_internal_value(window.get('start_date'))
                end_date = date_field.to_internal_value(window.get('end_date'))
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个可投入日期无效',
                }) from exc
            if end_date < start_date:
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个日期区间结束时间不能早于开始时间',
                })
            if period_start and start_date < period_start:
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个日期区间不能早于当前周期',
                })
            if period_end and end_date > period_end:
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个日期区间不能晚于当前周期',
                })
            try:
                capacity_days = Decimal(str(window.get('capacity_days')))
            except (InvalidOperation, TypeError, ValueError):
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个预计投入量无效',
                })
            if capacity_days <= 0 or capacity_days % Decimal('0.5') != 0:
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个预计投入量须为大于 0 的 0.5 天倍数',
                })
            inclusive_days = (end_date - start_date).days + 1
            if capacity_days > inclusive_days:
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个预计投入量不能超过日期区间天数',
                })
            note = str(window.get('note') or '').strip()
            if len(note) > 200:
                raise serializers.ValidationError({
                    'detail': f'第 {index + 1} 个安排备注不能超过 200 字',
                })
            normalized_windows.append({
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'capacity_days': float(capacity_days),
                'note': note,
            })
            total_capacity_days += capacity_days

        detail['availability_windows'] = normalized_windows
        attrs['detail'] = detail
        # 旧报表和接口仍读取 work_hours；按每天 8 小时生成兼容值，
        # 页面不再把它展示为实际投入时长。
        attrs['work_hours'] = total_capacity_days * Decimal('8')
        return attrs

    def create(self, validated_data):
        """创建灵活工时记录时自动设置当前用户"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class MemberProjectSummarySerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    project_code = serializers.CharField()
    role_in_project = serializers.CharField()
    role_in_project_display = serializers.CharField()
    membership_status = serializers.CharField()
    membership_status_display = serializers.CharField()
    exited_at = serializers.DateTimeField(allow_null=True)
    exit_reason = serializers.CharField(allow_blank=True)
    project_status = serializers.CharField()


class MemberTaskSummarySerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    title = serializers.CharField()
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    deadline = serializers.DateTimeField(allow_null=True)
    is_overdue = serializers.BooleanField()


class MemberCompetitionParticipationSerializer(serializers.Serializer):
    participant_id = serializers.IntegerField()
    competition_id = serializers.IntegerField()
    competition_name = serializers.CharField()
    event_id = serializers.IntegerField(allow_null=True)
    event_name = serializers.CharField()
    event_edition = serializers.CharField()
    event_organizer = serializers.CharField()
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    project_code = serializers.CharField()
    entry_name = serializers.CharField()
    role = serializers.CharField()
    role_display = serializers.CharField()
    participation_status = serializers.CharField()
    participation_status_display = serializers.CharField()
    responsibility = serializers.CharField()
    joined_at = serializers.DateTimeField()


def _get_competition_participations(user, viewer=None):
    """Return exact roster records instead of inferring entry membership by project."""
    from apps.competitions.models import CompetitionParticipant
    from common.project_access import scope_project_queryset

    participations = CompetitionParticipant.objects.filter(
        user=user,
    ).select_related(
        'competition__project',
        'competition__event',
    )
    if viewer is not None:
        participations = scope_project_queryset(
            participations,
            viewer,
            project_lookup='competition__project',
        )
    participations = participations.order_by(
        '-competition__event__edition',
        'competition__event__name',
        'competition__project__name',
        'competition__entry_name',
        'id',
    )
    result = []
    for participation in participations:
        competition = participation.competition
        event = competition.event
        project = competition.project
        result.append({
            'participant_id': participation.id,
            'competition_id': competition.id,
            'competition_name': competition.name,
            'event_id': event.id if event else None,
            'event_name': event.name if event else competition.name,
            'event_edition': event.edition if event else '',
            'event_organizer': event.organizer if event else competition.organizer,
            'project_id': project.id,
            'project_name': project.name,
            'project_code': project.code,
            'entry_name': competition.entry_name,
            'role': participation.role,
            'role_display': participation.get_role_display(),
            'participation_status': participation.participation_status,
            'participation_status_display': participation.get_participation_status_display(),
            'responsibility': participation.responsibility,
            'joined_at': participation.joined_at,
        })
    return result


class MemberListSerializer(serializers.ModelSerializer):
    """成员列表精简序列化器（返回用户基本信息+联系方式）"""
    global_role_display = serializers.CharField(source='get_global_role_display', read_only=True)
    team_memberships = serializers.SerializerMethodField()
    team_role = serializers.SerializerMethodField()
    team_role_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'name', 'email', 'phone', 'avatar',
            'global_role', 'global_role_display', 'is_student', 'school', 'grade', 'major',
            'membership_status', 'team_joined_at', 'team_left_at', 'is_active',
            'team_memberships', 'team_role', 'team_role_display',
        )
        read_only_fields = fields

    def get_team_memberships(self, obj):
        return _get_active_team_memberships(obj, _viewer(self))

    def get_team_role(self, obj):
        priority = getattr(obj, '_team_role_priority', None)
        if (
            isinstance(priority, int)
            and 0 <= priority < len(TEAM_MEMBER_ROLE_PRIORITY)
        ):
            return TEAM_MEMBER_ROLE_PRIORITY[priority]
        return ''

    def get_team_role_display(self, obj):
        role = self.get_team_role(obj)
        if not role:
            return ''
        from apps.common.team_models import TeamMember

        return TeamMember.Role(role).label


class MemberSerializer(serializers.ModelSerializer):
    """成员详情序列化器（返回用户基本信息+参与项目+联系方式）"""
    global_role_display = serializers.CharField(source='get_global_role_display', read_only=True)
    team_memberships = serializers.SerializerMethodField()
    # 参与的项目
    projects = serializers.SerializerMethodField()
    # 参与的项目数量
    project_count = serializers.SerializerMethodField()
    competition_participations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'name', 'email', 'phone', 'avatar',
            'global_role', 'global_role_display', 'is_student', 'school', 'grade', 'major',
            'membership_status', 'team_joined_at', 'team_left_at', 'exit_reason',
            'handover_to', 'handover_notes', 'is_active',
            'projects', 'project_count', 'competition_participations',
            'team_memberships', 'date_joined',
        )
        read_only_fields = fields

    @extend_schema_field(MemberProjectSummarySerializer(many=True))
    def get_projects(self, obj):
        """获取用户参与的项目列表"""
        from apps.projects.models import ProjectMember
        from common.project_access import scope_project_queryset

        memberships = ProjectMember.objects.filter(
            user=obj,
        ).select_related('project', 'user')
        viewer = _viewer(self)
        if viewer is not None:
            memberships = scope_project_queryset(
                memberships,
                viewer,
                project_lookup='project',
            )
        result = []
        for membership in memberships:
            project = membership.project
            result.append({
                'project_id': project.id,
                'project_name': project.name,
                'project_code': project.code,
                'role_in_project': membership.role_in_project,
                'role_in_project_display': membership.get_role_in_project_display(),
                'membership_status': membership.status,
                'membership_status_display': membership.get_status_display(),
                'exited_at': membership.exited_at,
                'exit_reason': membership.exit_reason,
                'project_status': project.status,
            })
        return result

    def get_project_count(self, obj) -> int:
        """获取用户参与的项目数量"""
        from apps.projects.models import ProjectMember
        from common.project_access import scope_project_queryset

        memberships = ProjectMember.objects.filter(
            user=obj, status=ProjectMember.Status.ACTIVE
        )
        viewer = _viewer(self)
        if viewer is not None:
            memberships = scope_project_queryset(
                memberships,
                viewer,
                project_lookup='project',
            )
        return memberships.count()

    def get_team_memberships(self, obj):
        return _get_active_team_memberships(obj, _viewer(self))

    @extend_schema_field(MemberCompetitionParticipationSerializer(many=True))
    def get_competition_participations(self, obj):
        return _get_competition_participations(obj, _viewer(self))


class MemberDetailSerializer(serializers.ModelSerializer):
    """
    成员详情序列化器
    返回用户基本信息 + 技能列表 + 灵活工作时间 + 参与项目 + 任务
    """
    global_role_display = serializers.CharField(source='get_global_role_display', read_only=True)
    team_memberships = serializers.SerializerMethodField()
    # 技能列表
    skills = serializers.SerializerMethodField()
    # 灵活工作时间（最新一条）
    latest_work_schedule = serializers.SerializerMethodField()
    # 参与的项目
    projects = serializers.SerializerMethodField()
    # 参与的项目数量
    project_count = serializers.SerializerMethodField()
    # 分配的任务（进行中/待办）
    tasks = serializers.SerializerMethodField()
    # 任务数量
    task_count = serializers.SerializerMethodField()
    competition_participations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'name', 'email', 'phone', 'avatar',
            'global_role', 'global_role_display', 'is_student', 'school', 'grade', 'major',
            'membership_status', 'team_joined_at', 'team_left_at', 'exit_reason',
            'handover_to', 'handover_notes', 'is_active',
            'skills', 'latest_work_schedule',
            'projects', 'project_count', 'competition_participations', 'team_memberships',
            'tasks', 'task_count',
            'date_joined',
        )
        read_only_fields = fields

    @extend_schema_field(MemberSkillSerializer(many=True))
    def get_skills(self, obj):
        """获取用户的技能列表"""
        skills = MemberSkill.objects.filter(user=obj).select_related('skill')
        return MemberSkillSerializer(skills, many=True).data

    @extend_schema_field(FlexibleWorkScheduleSerializer(allow_null=True))
    def get_latest_work_schedule(self, obj):
        """获取用户最新的灵活工作时间"""
        schedule = FlexibleWorkSchedule.objects.filter(user=obj).first()
        if schedule:
            return FlexibleWorkScheduleSerializer(schedule).data
        return None

    @extend_schema_field(MemberProjectSummarySerializer(many=True))
    def get_projects(self, obj):
        """获取用户参与的项目列表"""
        from apps.projects.models import ProjectMember
        from common.project_access import scope_project_queryset

        memberships = ProjectMember.objects.filter(
            user=obj,
        ).select_related('project', 'user')
        viewer = _viewer(self)
        if viewer is not None:
            memberships = scope_project_queryset(
                memberships,
                viewer,
                project_lookup='project',
            )
        result = []
        for membership in memberships:
            project = membership.project
            result.append({
                'project_id': project.id,
                'project_name': project.name,
                'project_code': project.code,
                'role_in_project': membership.role_in_project,
                'role_in_project_display': membership.get_role_in_project_display(),
                'membership_status': membership.status,
                'membership_status_display': membership.get_status_display(),
                'exited_at': membership.exited_at,
                'exit_reason': membership.exit_reason,
                'project_status': project.status,
            })
        return result

    def get_project_count(self, obj) -> int:
        """获取用户参与的项目数量"""
        from apps.projects.models import ProjectMember
        from common.project_access import scope_project_queryset

        memberships = ProjectMember.objects.filter(
            user=obj, status=ProjectMember.Status.ACTIVE
        )
        viewer = _viewer(self)
        if viewer is not None:
            memberships = scope_project_queryset(
                memberships,
                viewer,
                project_lookup='project',
            )
        return memberships.count()

    @extend_schema_field(MemberTaskSummarySerializer(many=True))
    def get_tasks(self, obj):
        """获取分配给用户的任务列表（进行中/待办）"""
        from apps.tasks.models import Task
        from common.project_access import scope_project_queryset

        tasks = Task.objects.filter(
            assignee=obj,
            status__in=['todo', 'doing', 'pending_review'],
        ).select_related('project')
        viewer = _viewer(self)
        if viewer is not None:
            tasks = scope_project_queryset(
                tasks,
                viewer,
                project_lookup='project',
            )
        tasks = tasks.order_by('-created_at')[:20]
        result = []
        for task in tasks:
            result.append({
                'task_id': task.id,
                'title': task.title,
                'project_id': task.project_id,
                'project_name': task.project.name if task.project else '',
                'status': task.status,
                'status_display': task.get_status_display(),
                'deadline': task.deadline,
                'is_overdue': task.is_overdue,
            })
        return result

    def get_task_count(self, obj) -> int:
        """获取分配给用户的未完成任务数量"""
        from apps.tasks.models import Task
        from common.project_access import scope_project_queryset

        tasks = Task.objects.filter(
            assignee=obj,
            status__in=['todo', 'doing', 'pending_review'],
        )
        viewer = _viewer(self)
        if viewer is not None:
            tasks = scope_project_queryset(
                tasks,
                viewer,
                project_lookup='project',
            )
        return tasks.count()

    def get_team_memberships(self, obj):
        return _get_active_team_memberships(obj, _viewer(self))

    @extend_schema_field(MemberCompetitionParticipationSerializer(many=True))
    def get_competition_participations(self, obj):
        return _get_competition_participations(obj, _viewer(self))
