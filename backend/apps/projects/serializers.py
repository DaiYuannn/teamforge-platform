"""
项目序列化器
"""
from decimal import Decimal

from rest_framework import serializers
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema_field

from common.project_access import is_external_collaborator
from .models import Project, ProjectMember, ProjectMembershipEvent, ProjectStageLog
from apps.users.serializers import (
    ExternalCollaboratorUserSerializer,
    UserListSerializer,
)


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
        read_only_fields = ('id', 'project', 'joined_at')

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

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'code', 'leader', 'leader_name',
            'current_stage', 'current_stage_display',
            'status', 'status_display', 'priority', 'priority_display',
            'start_date', 'planned_end_date', 'actual_end_date',
            'intro',
            'last_leader_update', 'archived_at', 'is_archived',
            'member_count', 'task_count', 'competition_count',
            'finance_balance', 'created_at',
        )
        read_only_fields = fields

    def get_member_count(self, obj) -> int:
        annotated_count = getattr(obj, 'active_member_count', None)
        if annotated_count is not None:
            return annotated_count
        return obj.members.filter(status=ProjectMember.Status.ACTIVE).count()

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

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'code', 'leader', 'leader_name',
            'current_stage', 'current_stage_display',
            'status', 'status_display', 'priority', 'priority_display',
            'start_date', 'planned_end_date', 'actual_end_date',
            'intro', 'last_leader_update', 'archived_at', 'is_archived',
            'members', 'stage_logs',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'last_leader_update', 'archived_at', 'created_at', 'updated_at')


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'code', 'leader', 'current_stage',
            'status', 'priority', 'start_date', 'planned_end_date',
            'actual_end_date', 'intro',
        )
        read_only_fields = ('id',)

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
