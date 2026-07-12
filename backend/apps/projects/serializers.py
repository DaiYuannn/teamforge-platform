"""
项目序列化器
"""
from rest_framework import serializers

from .models import Project, ProjectMember, ProjectStageLog
from apps.users.serializers import UserListSerializer


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
    user_detail = UserListSerializer(source='user', read_only=True)
    role_in_project_display = serializers.CharField(source='get_role_in_project_display', read_only=True)

    class Meta:
        model = ProjectMember
        fields = (
            'id', 'project', 'user', 'user_detail',
            'role_in_project', 'role_in_project_display', 'joined_at',
        )
        read_only_fields = ('id', 'project', 'joined_at')


class ProjectListSerializer(serializers.ModelSerializer):
    """项目列表精简序列化器"""
    leader_name = serializers.CharField(source='leader.name', read_only=True)
    current_stage_display = serializers.CharField(source='get_current_stage_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    member_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'code', 'leader', 'leader_name',
            'current_stage', 'current_stage_display',
            'status', 'status_display', 'priority', 'priority_display',
            'start_date', 'planned_end_date', 'actual_end_date',
            'last_leader_update', 'archived_at', 'is_archived',
            'member_count', 'created_at',
        )
        read_only_fields = fields


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
        ProjectMember.objects.create(
            project=project,
            user=project.leader,
            role_in_project=ProjectMember.RoleInProject.LEADER,
        )
        return project
