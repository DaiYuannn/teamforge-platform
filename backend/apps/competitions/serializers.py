"""
比赛序列化器
"""
from rest_framework import serializers

from .models import Competition, CompetitionParticipant
from apps.projects.models import ProjectMember
from apps.users.serializers import (
    ExternalCollaboratorUserSerializer,
    UserListSerializer,
)
from common.project_access import is_external_collaborator, project_can_manage
from .permissions import can_manage_competition


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
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = (
            'id', 'project', 'project_name', 'name', 'comp_type',
            'level', 'level_display', 'organizer', 'status', 'status_display',
            'is_promoted', 'is_awarded', 'award_level',
            'current_stage',
            'participant_count', 'leader_names',
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

    def get_can_manage(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and can_manage_competition(request.user, obj)
        )
