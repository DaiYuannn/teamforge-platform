"""
任务序列化器
"""
from rest_framework import serializers

from .models import Task, TaskLog
from apps.users.models import User
from apps.users.serializers import UserListSerializer
from apps.files.models import FileAsset
from apps.files.serializers import FileAssetListSerializer


def _visible_attachment_queryset(task, request):
    """只返回当前请求用户可在文件中心看到的任务附件。"""
    queryset = task.attachment_files.all()
    if not request or not request.user.is_authenticated:
        return queryset.none()
    user = request.user
    if user.global_role in ('sys_admin', 'teacher'):
        return queryset

    from django.db.models import Q
    from apps.projects.models import ProjectMember, Project

    member_ids = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
    leader_ids = Project.objects.filter(leader=user).values_list('id', flat=True)
    return queryset.filter(
        Q(level=FileAsset.Level.PUBLIC)
        | Q(level=FileAsset.Level.INTERNAL, project_id__in=member_ids)
        | Q(level=FileAsset.Level.INTERNAL, project_id__in=leader_ids)
    ).distinct()


class TaskAttachmentMixin:
    def get_attachment_files(self, obj):
        request = self.context.get('request')
        queryset = _visible_attachment_queryset(obj, request)
        return FileAssetListSerializer(queryset, many=True, context=self.context).data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get('project', getattr(self.instance, 'project', None))
        task_status = attrs.get(
            'status',
            getattr(self.instance, 'status', Task.Status.TODO),
        )
        delay_reason = attrs.get(
            'delay_reason',
            getattr(self.instance, 'delay_reason', ''),
        )
        if self.instance is None and task_status != Task.Status.TODO:
            raise serializers.ValidationError({
                'status': '新任务必须从待办状态开始，请创建后按流程推进。'
            })
        if (
            task_status == Task.Status.OVERDUE
            and not str(delay_reason or '').strip()
        ):
            raise serializers.ValidationError({
                'delay_reason': '进入已逾期状态必须填写延期原因。'
            })

        files = attrs.get('attachment_files')
        if files is not None and project:
            mismatched = [file.name for file in files if file.project_id != project.id]
            if mismatched:
                raise serializers.ValidationError({
                    'attachment_ids': f'附件必须属于任务所在项目：{"、".join(mismatched)}'
                })
            sensitive = [
                file.name for file in files
                if file.level == FileAsset.Level.SENSITIVE
            ]
            if sensitive:
                raise serializers.ValidationError({
                    'attachment_ids': (
                        f'敏感文件不能直接作为任务附件，请通过敏感资料审批访问：'
                        f'{"、".join(sensitive)}'
                    )
                })
        return attrs


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


class TaskSerializer(TaskAttachmentMixin, serializers.ModelSerializer):
    """任务完整序列化器"""
    attachment_files = serializers.SerializerMethodField()
    attachment_ids = serializers.PrimaryKeyRelatedField(
        source='attachment_files',
        many=True,
        write_only=True,
        queryset=FileAsset.objects.all(),
        required=False,
    )
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_detail = UserListSerializer(source='assignee', read_only=True)
    creator_name = serializers.CharField(source='creator.name', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default='')
    collaborators_detail = UserListSerializer(source='collaborators', many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    status_logs = TaskLogSerializer(many=True, read_only=True)
    collaborator_ids = serializers.PrimaryKeyRelatedField(
        source='collaborators', many=True,
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = Task
        fields = (
            'id', 'project', 'project_name', 'title', 'description',
            'assignee', 'assignee_detail', 'creator', 'creator_name',
            'collaborators', 'collaborator_ids', 'collaborators_detail',
            'deadline', 'start_date', 'priority', 'priority_display',
            'status', 'status_display',
            'completed_at', 'overdue_reminded', 'is_overdue',
            'delay_reason', 'completion_note',
            'reviewer', 'reviewer_name',
            'attachments', 'attachment_files', 'attachment_ids', 'status_logs',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'creator', 'completed_at', 'overdue_reminded',
            'created_at', 'updated_at',
        )


class TaskListSerializer(serializers.ModelSerializer):
    """任务列表精简序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.name', read_only=True)
    creator_name = serializers.CharField(source='creator.name', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    collaborator_ids = serializers.PrimaryKeyRelatedField(
        source='collaborators', many=True, read_only=True
    )
    attachment_count = serializers.IntegerField(
        source='attachment_files.count', read_only=True
    )

    class Meta:
        model = Task
        fields = (
            'id', 'project', 'project_name', 'title',
            'assignee', 'assignee_name', 'creator', 'creator_name',
            'reviewer', 'reviewer_name', 'collaborator_ids',
            'deadline', 'start_date', 'priority', 'priority_display',
            'status', 'status_display',
            'completed_at', 'is_overdue', 'delay_reason', 'completion_note',
            'attachment_count', 'created_at',
        )
        read_only_fields = fields


class TaskCreateSerializer(TaskAttachmentMixin, serializers.ModelSerializer):
    """任务创建序列化器"""
    attachment_files = serializers.SerializerMethodField()
    attachment_ids = serializers.PrimaryKeyRelatedField(
        source='attachment_files',
        many=True,
        write_only=True,
        queryset=FileAsset.objects.all(),
        required=False,
    )
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
            'deadline', 'start_date', 'priority',
            'status', 'delay_reason', 'completion_note', 'reviewer',
            'attachments', 'attachment_files', 'attachment_ids',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        """创建任务时自动设置创建者"""
        collaborators = validated_data.pop('collaborators', [])
        attachment_files = validated_data.pop('attachment_files', [])
        # 设置创建者
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['creator'] = request.user

        task = Task.objects.create(**validated_data)
        if collaborators:
            task.collaborators.set(collaborators)
        if attachment_files:
            task.attachment_files.set(attachment_files)

        # 创建初始状态日志
        TaskLog.objects.create(
            task=task,
            from_status='',
            to_status=task.status,
            operator=request.user if request else None,
        )
        return task
