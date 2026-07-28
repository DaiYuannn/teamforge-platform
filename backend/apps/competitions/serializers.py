"""
比赛序列化器
"""
from rest_framework import serializers

from .models import Competition, CompetitionParticipant
from apps.contributions.models import Contribution
from apps.projects.models import ProjectMember
from apps.users.serializers import (
    ExternalCollaboratorUserSerializer,
    UserListSerializer,
)
from common.project_access import (
    is_external_collaborator,
    project_can_manage,
    scope_project_queryset,
)
from .permissions import can_manage_competition


class CompetitionContributionEvidenceSerializer(serializers.ModelSerializer):
    """比赛执行页使用的精简贡献证据，保留其真实来源与审核状态。"""

    user_name = serializers.CharField(source='user.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    contribution_type_display = serializers.CharField(
        source='get_contribution_type_display',
        read_only=True,
    )
    source_type_display = serializers.CharField(
        source='get_source_type_display',
        read_only=True,
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    proof_file_name = serializers.CharField(
        source='proof_file.name',
        read_only=True,
        default='',
    )
    origin_competition_name = serializers.SerializerMethodField()
    reuse_scope = serializers.SerializerMethodField()
    reuse_scope_display = serializers.SerializerMethodField()
    reuse_eligible = serializers.SerializerMethodField()
    reuse_reason = serializers.SerializerMethodField()

    class Meta:
        model = Contribution
        fields = (
            'id', 'project', 'project_name', 'user', 'user_name',
            'contribution_type', 'contribution_type_display',
            'content', 'description', 'weight',
            'status', 'status_display',
            'source_type', 'source_type_display', 'source_verified',
            'related_object_id', 'origin_competition_name',
            'proof_file', 'proof_file_name',
            'reuse_scope', 'reuse_scope_display',
            'reuse_eligible', 'reuse_reason',
            'created_at',
        )
        read_only_fields = fields

    def get_origin_competition_name(self, obj):
        if (
            obj.source_type != Contribution.SourceType.COMPETITION
            or not obj.related_object_id
        ):
            return ''
        competition_names = self.context.get('competition_names', {})
        return competition_names.get(obj.related_object_id, '')

    def get_reuse_scope(self, obj):
        competition = self.context.get('competition')
        if competition and obj.project_id == competition.project_id:
            return 'same_project'
        return 'visible_other_project'

    def get_reuse_scope_display(self, obj):
        if self.get_reuse_scope(obj) == 'same_project':
            return '同项目可引用'
        return '其他可见项目可引用'

    def get_reuse_eligible(self, obj):
        return (
            obj.status == Contribution.Status.APPROVED
            and obj.source_verified
        )

    def get_reuse_reason(self, obj):
        if obj.status != Contribution.Status.APPROVED:
            return '贡献尚未审核通过，不能作为已确认成果复用'
        if not obj.source_verified:
            return '贡献来源尚未核验，不能作为已确认成果复用'
        return '可引用内容和证明材料；原记录仍归属来源项目，不重复计分'


def _competition_project_leader_names(competition):
    names = [competition.project.leader.name]
    prefetched_members = getattr(
        competition.project,
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
                and member.user_id != competition.project.leader_id
            )
        ]
    else:
        co_leader_names = competition.project.members.filter(
            role_in_project=ProjectMember.RoleInProject.LEADER,
            status=ProjectMember.Status.ACTIVE,
        ).exclude(
            user_id=competition.project.leader_id,
        ).order_by('joined_at', 'id').values_list('user__name', flat=True)
    names.extend(co_leader_names)
    return list(dict.fromkeys(name for name in names if name))


def _competition_team_names(competition):
    prefetched_teams = getattr(
        competition.project,
        '_prefetched_objects_cache',
        {},
    ).get('teams')
    if prefetched_teams is not None:
        return [
            team.name
            for team in sorted(
                prefetched_teams,
                key=lambda team: (team.parent_id or 0, team.name, team.id),
            )
        ]
    return list(
        competition.project.teams.order_by('parent_id', 'name', 'id')
        .values_list('name', flat=True)
    )


def _contribution_evidence_data(contributions, competition, context):
    contributions = list(contributions)
    origin_competition_ids = {
        item.related_object_id
        for item in contributions
        if (
            item.source_type == Contribution.SourceType.COMPETITION
            and item.related_object_id
        )
    }
    competition_names = dict(
        Competition.objects.filter(id__in=origin_competition_ids)
        .values_list('id', 'name')
    )
    serializer_context = {
        **context,
        'competition': competition,
        'competition_names': competition_names,
    }
    return CompetitionContributionEvidenceSerializer(
        contributions,
        many=True,
        context=serializer_context,
    ).data


class CompetitionParticipantSerializer(serializers.ModelSerializer):
    """比赛负责人和参赛成员。"""

    user_detail = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    participation_status_display = serializers.CharField(
        source='get_participation_status_display',
        read_only=True,
    )

    class Meta:
        model = CompetitionParticipant
        fields = (
            'id', 'competition', 'user', 'user_detail',
            'role', 'role_display',
            'participation_status', 'participation_status_display',
            'responsibility', 'joined_at', 'updated_at',
        )
        read_only_fields = ('id', 'joined_at', 'updated_at')

    def get_user_detail(self, obj):
        request = self.context.get('request')
        viewer = getattr(request, 'user', None)
        serializer_class = (
            ExternalCollaboratorUserSerializer
            if is_external_collaborator(viewer)
            else UserListSerializer
        )
        return serializer_class(obj.user, context=self.context).data

    def validate(self, attrs):
        competition = attrs.get(
            'competition',
            getattr(self.instance, 'competition', None),
        )
        user = attrs.get('user', getattr(self.instance, 'user', None))
        if self.instance and 'competition' in attrs:
            if attrs['competition'].pk != self.instance.competition_id:
                raise serializers.ValidationError({
                    'competition': '参赛成员所属比赛不可变更'
                })
        if user and (
            not user.is_active
            or user.membership_status not in ('active', 'on_leave')
        ):
            raise serializers.ValidationError({
                'user': '参赛成员必须是在队或暂离且账号有效的团队成员'
            })
        if competition and user:
            is_project_member = (
                competition.project.leader_id == user.id
                or ProjectMember.objects.filter(
                    project=competition.project,
                    user=user,
                    status=ProjectMember.Status.ACTIVE,
                ).exists()
            )
            if not is_project_member:
                raise serializers.ValidationError({
                    'user': '参赛成员必须是所属项目的活动成员'
                })
        return attrs


class CompetitionSerializer(serializers.ModelSerializer):
    """比赛完整序列化器"""
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    participants = CompetitionParticipantSerializer(many=True, read_only=True)
    participant_count = serializers.SerializerMethodField()
    leader_names = serializers.SerializerMethodField()
    project_leader_names = serializers.SerializerMethodField()
    project_team_names = serializers.SerializerMethodField()
    competition_contributions = serializers.SerializerMethodField()
    reusable_contributions = serializers.SerializerMethodField()
    contribution_reuse_note = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = (
            'id', 'project', 'project_name', 'name', 'comp_type',
            'level', 'level_display', 'organizer',
            'register_date', 'material_deadline', 'review_date', 'defense_date',
            'school_date', 'city_date', 'province_date', 'national_date', 'result_date',
            'status', 'status_display',
            'is_promoted', 'is_awarded', 'award_level',
            'not_promoted_reason', 'improvement_suggestion', 'review_summary',
            'current_stage', 'participants', 'participant_count', 'leader_names',
            'project_leader_names', 'project_team_names',
            'competition_contributions', 'reusable_contributions',
            'contribution_reuse_note',
            'can_manage',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        target_project = attrs.get(
            'project',
            getattr(self.instance, 'project', None),
        )
        if (
            self.instance
            and target_project
            and target_project.pk != self.instance.project_id
        ):
            request = self.context.get('request')
            user = getattr(request, 'user', None)
            if not project_can_manage(user, target_project):
                raise serializers.ValidationError({
                    'project': '只有目标项目负责人可以将比赛迁移到该项目'
                })

            participant_user_ids = set(
                self.instance.participants.exclude(
                    participation_status=(
                        CompetitionParticipant.ParticipationStatus.WITHDRAWN
                    ),
                ).values_list('user_id', flat=True)
            )
            if participant_user_ids:
                allowed_user_ids = set(
                    ProjectMember.objects.filter(
                        project=target_project,
                        status=ProjectMember.Status.ACTIVE,
                    ).values_list('user_id', flat=True)
                )
                allowed_user_ids.add(target_project.leader_id)
                if participant_user_ids - allowed_user_ids:
                    raise serializers.ValidationError({
                        'project': '现有参赛名单中包含非目标项目成员，请先调整名单'
                    })
        return attrs

    def get_participant_count(self, obj):
        return obj.participants.exclude(
            participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
        ).count()

    def get_leader_names(self, obj):
        return list(
            obj.participants.filter(
                role=CompetitionParticipant.Role.LEADER,
            ).exclude(
                participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
            ).values_list('user__name', flat=True)
        )

    def get_project_leader_names(self, obj):
        return _competition_project_leader_names(obj)

    def get_project_team_names(self, obj):
        return _competition_team_names(obj)

    def get_competition_contributions(self, obj):
        contributions = Contribution.objects.filter(
            project=obj.project,
            source_type=Contribution.SourceType.COMPETITION,
            related_object_id=obj.id,
        ).select_related(
            'project', 'user', 'proof_file',
        ).order_by('user__name', '-created_at', '-id')
        return _contribution_evidence_data(
            contributions,
            obj,
            self.context,
        )

    def get_reusable_contributions(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return []

        participant_user_ids = obj.participants.exclude(
            participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
        ).values_list('user_id', flat=True)
        contributions = Contribution.objects.filter(
            user_id__in=participant_user_ids,
            status=Contribution.Status.APPROVED,
            source_verified=True,
        ).exclude(
            project=obj.project,
            source_type=Contribution.SourceType.COMPETITION,
            related_object_id=obj.id,
        ).select_related(
            'project', 'user', 'proof_file',
        ).order_by('-created_at', '-id')
        contributions = scope_project_queryset(
            contributions,
            user,
            project_lookup='project',
        )[:50]
        return _contribution_evidence_data(
            contributions,
            obj,
            self.context,
        )

    def get_contribution_reuse_note(self, obj):
        return (
            '可复用列表只表示内容和证明材料可被后续比赛或项目引用；'
            '原贡献仍归属来源项目，不会自动复制或重复计分。'
        )

    def get_can_manage(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and can_manage_competition(request.user, obj)
        )


class CompetitionListSerializer(serializers.ModelSerializer):
    """比赛列表精简序列化器"""
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    participant_count = serializers.SerializerMethodField()
    leader_names = serializers.SerializerMethodField()
    project_leader_names = serializers.SerializerMethodField()
    project_team_names = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = (
            'id', 'project', 'project_name', 'name', 'comp_type',
            'level', 'level_display', 'organizer', 'status', 'status_display',
            'is_promoted', 'is_awarded', 'award_level',
            'current_stage',
            'participant_count', 'leader_names',
            'project_leader_names', 'project_team_names',
            'can_manage',
            'register_date', 'defense_date', 'result_date',
            'created_at',
        )
        read_only_fields = fields

    def get_participant_count(self, obj):
        return obj.participants.exclude(
            participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
        ).count()

    def get_leader_names(self, obj):
        return list(
            obj.participants.filter(
                role=CompetitionParticipant.Role.LEADER,
            ).exclude(
                participation_status=CompetitionParticipant.ParticipationStatus.WITHDRAWN,
            ).values_list('user__name', flat=True)
        )

    def get_project_leader_names(self, obj):
        return _competition_project_leader_names(obj)

    def get_project_team_names(self, obj):
        return _competition_team_names(obj)

    def get_can_manage(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and can_manage_competition(request.user, obj)
        )
