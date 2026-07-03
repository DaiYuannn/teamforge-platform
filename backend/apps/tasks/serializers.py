"""
任务序列化器
"""
from rest_framework import serializers

from .models import Task, TaskLog
from apps.users.models import User
from apps.users.serializers import UserListSerializer


class TaskLogSerializer(serializers.ModelSerializer):
    """任务日志序列化器"""
    operator_name = serializers.CharField(source='operator.name', read_only=True, default='')
    from_status_display = serializers.CharField(source='get_from_status_display', read_only=True)
    to_status_display = serializers.CharField(source='get_to_status_display', read_only=True)

    class Meta:
        model = TaskLog
        fields = (
            'id', 'task', 'from_status', 'from_status_display',
            'to_status', 'to_status_display', 'operator', 'operator_name',
            'created_at',
        )
        read_only_fields = ('id', 'task', 'operator', 'created_at')


class TaskSerializer(serializers.ModelSerializer):
    """任务完整序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_detail = UserListSerializer(source='assignee', read_only=True)
    creator_name = serializers.CharField(source='creator.name', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default='')
    collaborators_detail = UserListSerializer(source='collaborators', many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    status_logs = TaskLogSerializer(many=True, read_only=True)
    collaborator_ids = serializers.PrimaryKeyRelatedField(
        source='collaborators', many=True, write_only=True,
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = Task
        fields = (
            'id', 'project', 'project_name', 'title', 'description',
            'assignee', 'assignee_detail', 'creator', 'creator_name',
            'collaborators', 'collaborator_ids', 'collaborators_detail',
            'deadline', 'status', 'status_display',
            'completed_at', 'overdue_reminded', 'is_overdue',
            'delay_reason', 'reviewer', 'reviewer_name',
            'attachments', 'status_logs',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'completed_at', 'overdue_reminded', 'created_at', 'updated_at')


class TaskListSerializer(serializers.ModelSerializer):
    """任务列表精简序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.name', read_only=True)
    creator_name = serializers.CharField(source='creator.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'project', 'project_name', 'title',
            'assignee', 'assignee_name', 'creator', 'creator_name',
            'deadline', 'status', 'status_display',
            'completed_at', 'is_overdue', 'created_at',
        )
        read_only_fields = fields


class TaskCreateSerializer(serializers.ModelSerializer):
    """任务创建序列化器"""
    collaborator_ids = serializers.PrimaryKeyRelatedField(
        source='collaborators', many=True, write_only=True,
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = Task
        fields = (
            'id', 'project', 'title', 'description',
            'assignee', 'collaborator_ids',
            'deadline', 'status', 'reviewer', 'attachments',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        """创建任务时自动设置创建者"""
        collaborators = validated_data.pop('collaborators', [])
        # 设置创建者
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['creator'] = request.user

        task = Task.objects.create(**validated_data)
        if collaborators:
            task.collaborators.set(collaborators)

        # 创建初始状态日志
        TaskLog.objects.create(
            task=task,
            from_status='',
            to_status=task.status,
            operator=request.user if request else None,
        )
        return task
