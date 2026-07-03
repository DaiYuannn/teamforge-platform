"""
成员序列化器
包含技能标签、成员技能、灵活工时、成员详情等序列化器
"""
from rest_framework import serializers

from apps.users.models import User
from apps.users.serializers import UserListSerializer
from apps.projects.serializers import ProjectListSerializer
from .models import SkillTag, MemberSkill, FlexibleWorkSchedule


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
        fields = ('id', 'user', 'user_name', 'skill', 'skill_name', 'proficiency', 'created_at')
        read_only_fields = ('id', 'created_at')


class FlexibleWorkScheduleSerializer(serializers.ModelSerializer):
    """灵活工时序列化器"""
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
    """灵活工时创建序列化器（用户填写当前半月周期）"""

    class Meta:
        model = FlexibleWorkSchedule
        fields = (
            'id', 'period_start', 'period_end',
            'work_hours', 'detail', 'can_offline', 'can_urgent',
            'is_saturated', 'notes',
        )
        read_only_fields = ('id',)

    def validate_proficiency_range(self, value):
        """校验工时范围"""
        if value < 0:
            raise serializers.ValidationError('可用工时不能为负数')
        return value

    def validate(self, attrs):
        """校验时段"""
        period_start = attrs.get('period_start')
        period_end = attrs.get('period_end')
        if period_start and period_end and period_end <= period_start:
            raise serializers.ValidationError({'period_end': '时段结束必须晚于时段开始'})
        return attrs

    def create(self, validated_data):
        """创建灵活工时记录时自动设置当前用户"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class MemberListSerializer(serializers.ModelSerializer):
    """成员列表精简序列化器（返回用户基本信息+联系方式）"""
    global_role_display = serializers.CharField(source='get_global_role_display', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'name', 'email', 'phone', 'avatar',
            'global_role', 'global_role_display', 'is_student', 'grade', 'major',
        )
        read_only_fields = fields


class MemberSerializer(serializers.ModelSerializer):
    """成员详情序列化器（返回用户基本信息+参与项目+联系方式）"""
    global_role_display = serializers.CharField(source='get_global_role_display', read_only=True)
    # 参与的项目
    projects = serializers.SerializerMethodField()
    # 参与的项目数量
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'name', 'email', 'phone', 'avatar',
            'global_role', 'global_role_display', 'is_student', 'grade', 'major',
            'projects', 'project_count', 'date_joined',
        )
        read_only_fields = fields

    def get_projects(self, obj):
        """获取用户参与的项目列表"""
        from apps.projects.models import ProjectMember
        memberships = ProjectMember.objects.filter(user=obj).select_related('project', 'user')
        result = []
        for membership in memberships:
            project = membership.project
            result.append({
                'project_id': project.id,
                'project_name': project.name,
                'project_code': project.code,
                'role_in_project': membership.role_in_project,
                'role_in_project_display': membership.get_role_in_project_display(),
                'project_status': project.status,
            })
        return result

    def get_project_count(self, obj):
        """获取用户参与的项目数量"""
        from apps.projects.models import ProjectMember
        return ProjectMember.objects.filter(user=obj).count()


class MemberDetailSerializer(serializers.ModelSerializer):
    """
    成员详情序列化器
    返回用户基本信息 + 技能列表 + 灵活工作时间 + 参与项目 + 任务
    """
    global_role_display = serializers.CharField(source='get_global_role_display', read_only=True)
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

    class Meta:
        model = User
        fields = (
            'id', 'username', 'name', 'email', 'phone', 'avatar',
            'global_role', 'global_role_display', 'is_student', 'grade', 'major',
            'skills', 'latest_work_schedule',
            'projects', 'project_count',
            'tasks', 'task_count',
            'date_joined',
        )
        read_only_fields = fields

    def get_skills(self, obj):
        """获取用户的技能列表"""
        skills = MemberSkill.objects.filter(user=obj).select_related('skill')
        return MemberSkillSerializer(skills, many=True).data

    def get_latest_work_schedule(self, obj):
        """获取用户最新的灵活工作时间"""
        schedule = FlexibleWorkSchedule.objects.filter(user=obj).first()
        if schedule:
            return FlexibleWorkScheduleSerializer(schedule).data
        return None

    def get_projects(self, obj):
        """获取用户参与的项目列表"""
        from apps.projects.models import ProjectMember
        memberships = ProjectMember.objects.filter(user=obj).select_related('project', 'user')
        result = []
        for membership in memberships:
            project = membership.project
            result.append({
                'project_id': project.id,
                'project_name': project.name,
                'project_code': project.code,
                'role_in_project': membership.role_in_project,
                'role_in_project_display': membership.get_role_in_project_display(),
                'project_status': project.status,
            })
        return result

    def get_project_count(self, obj):
        """获取用户参与的项目数量"""
        from apps.projects.models import ProjectMember
        return ProjectMember.objects.filter(user=obj).count()

    def get_tasks(self, obj):
        """获取分配给用户的任务列表（进行中/待办）"""
        from apps.tasks.models import Task
        tasks = Task.objects.filter(
            assignee=obj,
            status__in=['todo', 'doing', 'pending_review'],
        ).select_related('project').order_by('-created_at')[:20]
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

    def get_task_count(self, obj):
        """获取分配给用户的未完成任务数量"""
        from apps.tasks.models import Task
        return Task.objects.filter(
            assignee=obj,
            status__in=['todo', 'doing', 'pending_review'],
        ).count()
