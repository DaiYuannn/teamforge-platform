"""Serializers for competition-entry work items and workload assessments."""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.competitions.models import Competition
from apps.competitions.permissions import can_manage_competition
from apps.users.models import User

from .models import Task
from .subtask_models import SubTask
from .workload_models import (
    CompetitionWorkloadAllocation,
    CompetitionWorkloadAssessment,
    CompetitionWorkloadObjection,
)
from .workload_permissions import is_active_competition_participant


class CompetitionSubTaskSerializer(serializers.ModelSerializer):
    """Compact nested checklist item used by the competition workspace."""

    id = serializers.IntegerField(required=False)
    assignee_name = serializers.CharField(
        source='assignee.name',
        read_only=True,
        default='',
    )

    class Meta:
        model = SubTask
        fields = (
            'id',
            'title',
            'assignee',
            'assignee_name',
            'is_completed',
            'completed_at',
            'sort_order',
        )
        read_only_fields = ('completed_at',)
        extra_kwargs = {
            'title': {'required': True, 'allow_blank': False},
            'assignee': {'required': False, 'allow_null': True},
            'is_completed': {'required': False},
            'sort_order': {'required': False},
        }


class CompetitionWorkItemSerializer(serializers.ModelSerializer):
    competition = serializers.PrimaryKeyRelatedField(
        source='competition_entry',
        queryset=Competition.objects.all(),
    )
    event_name = serializers.CharField(
        source='competition_entry.event.name',
        read_only=True,
        default='',
    )
    event_edition = serializers.CharField(
        source='competition_entry.event.edition',
        read_only=True,
        default='',
    )
    entry_name = serializers.CharField(
        source='competition_entry.entry_name',
        read_only=True,
        default='',
    )
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.name', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
    )
    created_by_name = serializers.CharField(
        source='creator.name',
        read_only=True,
        default='',
    )
    collaborator_names = serializers.SerializerMethodField()
    reviewer_name = serializers.CharField(
        source='reviewer.name',
        read_only=True,
        default='',
    )
    subtasks = CompetitionSubTaskSerializer(many=True, required=False)
    can_manage = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            'id',
            'competition',
            'event_name',
            'event_edition',
            'entry_name',
            'project',
            'project_name',
            'assignee',
            'assignee_name',
            'collaborators',
            'collaborator_names',
            'reviewer',
            'reviewer_name',
            'title',
            'description',
            'deadline',
            'priority',
            'status',
            'status_display',
            'completed_at',
            'completion_note',
            'reference_note',
            'subtasks',
            'created_by_name',
            'can_manage',
            'can_edit',
            'can_review',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'project',
            'completed_at',
            'created_at',
            'updated_at',
        )
        extra_kwargs = {
            'assignee': {'required': True},
            'title': {'required': True, 'allow_blank': False},
            'deadline': {'required': True, 'allow_null': False},
        }

    def validate_competition(self, competition):
        if (
            self.instance is not None
            and competition.pk != self.instance.competition_entry_id
        ):
            raise serializers.ValidationError('工作项所属参赛队不可变更')
        return competition

    def get_can_manage(self, obj):
        return self.get_can_edit(obj) or self.get_can_review(obj)

    def get_can_edit(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return (
            obj.assignee_id == user.id
            or can_manage_competition(user, obj.competition_entry)
        )

    def get_can_review(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return (
            obj.reviewer_id == user.id
            or can_manage_competition(user, obj.competition_entry)
        )

    def get_collaborator_names(self, obj):
        return [user.name for user in obj.collaborators.all()]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        competition = attrs.get(
            'competition_entry',
            getattr(self.instance, 'competition_entry', None),
        )
        if competition is None:
            return attrs

        assignee = attrs.get('assignee', getattr(self.instance, 'assignee', None))
        collaborators = attrs.get('collaborators')
        if collaborators is None and self.instance is not None:
            collaborators = list(self.instance.collaborators.all())
        collaborators = collaborators or []
        reviewer = attrs.get('reviewer', getattr(self.instance, 'reviewer', None))
        subtasks = attrs.get('subtasks')

        eligible_ids = set(
            competition.participants.filter(
                role__in=['leader', 'member'],
            ).exclude(
                participation_status='withdrawn',
            ).values_list('user_id', flat=True)
        )
        people = [assignee, reviewer, *collaborators]
        if subtasks is not None:
            people.extend(item.get('assignee') for item in subtasks)
        invalid_names = sorted({
            person.name
            for person in people
            if person is not None and person.id not in eligible_ids
        })
        if invalid_names:
            raise serializers.ValidationError({
                'assignee': (
                    '任务负责人、协作者、验收人和子任务负责人都必须来自'
                    f'本参赛队有效成员：{"、".join(invalid_names)}'
                ),
            })
        if assignee is not None and any(
            collaborator.id == assignee.id
            for collaborator in collaborators
        ):
            raise serializers.ValidationError({
                'collaborators': '任务负责人无需重复加入协作者',
            })
        if (
            reviewer is not None
            and assignee is not None
            and reviewer.id == assignee.id
        ):
            raise serializers.ValidationError({
                'reviewer': '任务负责人不能验收自己的任务',
            })
        if subtasks is not None:
            subtask_ids = [
                item['id']
                for item in subtasks
                if item.get('id') is not None
            ]
            if len(subtask_ids) != len(set(subtask_ids)):
                raise serializers.ValidationError({
                    'subtasks': '同一子任务不能重复提交',
                })
        return attrs

    def create(self, validated_data):
        subtasks = validated_data.pop('subtasks', [])
        task = super().create(validated_data)
        self._replace_subtasks(task, subtasks)
        return task

    def update(self, instance, validated_data):
        subtasks = validated_data.pop('subtasks', None)
        task = super().update(instance, validated_data)
        if subtasks is not None:
            self._replace_subtasks(task, subtasks)
        return task

    @staticmethod
    def _replace_subtasks(task, incoming):
        existing = {subtask.id: subtask for subtask in task.subtasks.all()}
        kept_ids = []
        for index, payload in enumerate(incoming):
            values = dict(payload)
            subtask_id = values.pop('id', None)
            values.setdefault('sort_order', index)
            is_completed = values.get('is_completed', False)
            values['completed_at'] = (
                timezone.now() if is_completed else None
            )
            if subtask_id is not None:
                subtask = existing.get(subtask_id)
                if subtask is None:
                    raise serializers.ValidationError({
                        'subtasks': f'子任务 {subtask_id} 不属于当前任务',
                    })
                for field, value in values.items():
                    setattr(subtask, field, value)
                subtask.save()
            else:
                subtask = SubTask.objects.create(parent=task, **values)
            kept_ids.append(subtask.id)
        task.subtasks.exclude(id__in=kept_ids).delete()


class CompetitionWorkloadAllocationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = CompetitionWorkloadAllocation
        fields = ('id', 'user', 'user_name', 'percentage', 'rationale')
        read_only_fields = fields


class CompetitionWorkloadAssessmentSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(
        source='competition.event.name',
        read_only=True,
        default='',
    )
    event_edition = serializers.CharField(
        source='competition.event.edition',
        read_only=True,
        default='',
    )
    entry_name = serializers.CharField(
        source='competition.entry_name',
        read_only=True,
        default='',
    )
    project = serializers.PrimaryKeyRelatedField(
        source='competition.project',
        read_only=True,
    )
    project_name = serializers.CharField(
        source='competition.project.name',
        read_only=True,
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
    )
    decided_by_name = serializers.CharField(
        source='decided_by.name',
        read_only=True,
        default='',
    )
    allocations = CompetitionWorkloadAllocationSerializer(
        many=True,
        read_only=True,
    )
    allocation_total = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    objection_count = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    can_object = serializers.SerializerMethodField()

    class Meta:
        model = CompetitionWorkloadAssessment
        fields = (
            'id',
            'competition',
            'event_name',
            'event_edition',
            'entry_name',
            'project',
            'project_name',
            'version',
            'status',
            'status_display',
            'decision_note',
            'decided_by',
            'decided_by_name',
            'published_at',
            'is_current',
            'allocations',
            'allocation_total',
            'total',
            'objection_count',
            'can_manage',
            'can_object',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_total(self, obj):
        return sum(
            (allocation.percentage for allocation in obj.allocations.all()),
            Decimal('0.00'),
        )

    def get_allocation_total(self, obj):
        return self.get_total(obj)

    def get_objection_count(self, obj):
        return sum(
            allocation.objections.count()
            for allocation in obj.allocations.all()
        )

    def get_can_manage(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(
            user
            and user.is_authenticated
            and can_manage_competition(user, obj.competition)
        )

    def get_can_object(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(
            obj.status == CompetitionWorkloadAssessment.Status.PUBLISHED
            and obj.is_current
            and is_active_competition_participant(user, obj.competition)
        )


class CompetitionWorkloadAllocationInputSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    rationale = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_percentage(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError('贡献比例必须在 0 到 100 之间')
        return value


class CompetitionWorkloadDraftInputSerializer(serializers.Serializer):
    competition = serializers.PrimaryKeyRelatedField(
        queryset=Competition.objects.all(),
    )
    decision_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )
    allocations = CompetitionWorkloadAllocationInputSerializer(many=True)

    def validate_allocations(self, allocations):
        user_ids = [item['user'].id for item in allocations]
        if len(user_ids) != len(set(user_ids)):
            raise serializers.ValidationError('同一成员不能重复分配贡献比例')
        return allocations


class CompetitionWorkloadObjectionSerializer(serializers.ModelSerializer):
    assessment = serializers.PrimaryKeyRelatedField(
        source='allocation.assessment',
        read_only=True,
    )
    competition = serializers.PrimaryKeyRelatedField(
        source='allocation.assessment.competition',
        read_only=True,
    )
    allocation_user = serializers.PrimaryKeyRelatedField(
        source='allocation.user',
        read_only=True,
    )
    allocation_user_name = serializers.CharField(
        source='allocation.user.name',
        read_only=True,
    )
    raised_by_name = serializers.CharField(
        source='raised_by.name',
        read_only=True,
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
    )
    resolved_by_name = serializers.CharField(
        source='resolved_by.name',
        read_only=True,
        default='',
    )
    can_resolve = serializers.SerializerMethodField()

    class Meta:
        model = CompetitionWorkloadObjection
        fields = (
            'id',
            'allocation',
            'assessment',
            'competition',
            'allocation_user',
            'allocation_user_name',
            'raised_by',
            'raised_by_name',
            'reason',
            'status',
            'status_display',
            'response',
            'resolved_by_name',
            'created_at',
            'resolved_at',
            'can_resolve',
        )
        read_only_fields = fields

    def get_can_resolve(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(
            user
            and user.is_authenticated
            and can_manage_competition(
                user,
                obj.allocation.assessment.competition,
            )
        )


class CompetitionWorkloadObjectionCreateSerializer(serializers.Serializer):
    allocation = serializers.PrimaryKeyRelatedField(
        queryset=CompetitionWorkloadAllocation.objects.select_related(
            'assessment__competition',
        ),
    )
    reason = serializers.CharField(allow_blank=False)


class CompetitionWorkloadObjectionResolveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            CompetitionWorkloadObjection.Status.RESOLVED,
            CompetitionWorkloadObjection.Status.REJECTED,
        ),
    )
    response = serializers.CharField(allow_blank=False)
