"""Competition-entry work items, workload assessments, and objections."""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from common.response import success_response
from apps.competitions.models import Competition
from apps.competitions.permissions import can_manage_competition
from apps.contributions.models import Contribution

from .models import Task, TaskLog
from .workload_models import (
    CompetitionWorkloadAllocation,
    CompetitionWorkloadAssessment,
    CompetitionWorkloadObjection,
)
from .workload_permissions import (
    can_view_competition_entry,
    eligible_allocation_participants,
    is_active_competition_participant,
)
from .workload_serializers import (
    CompetitionWorkItemSerializer,
    CompetitionWorkloadAssessmentSerializer,
    CompetitionWorkloadDraftInputSerializer,
    CompetitionWorkloadObjectionCreateSerializer,
    CompetitionWorkloadObjectionResolveSerializer,
    CompetitionWorkloadObjectionSerializer,
)


def _competition_queryset():
    return Competition.objects.select_related(
        'event',
        'project',
        'project__leader',
    ).prefetch_related(
        'project__members',
        'project__teams',
    )


def _resolve_competition(user, competition_id):
    if competition_id in (None, ''):
        raise ValidationError({'competition': '必须提供 competition 查询参数'})
    competition = get_object_or_404(_competition_queryset(), pk=competition_id)
    if not can_view_competition_entry(user, competition):
        raise PermissionDenied('无权访问该参赛队')
    return competition


def _validate_work_item_assignee(competition, assignee):
    if not eligible_allocation_participants(competition).filter(
        user=assignee,
    ).exists():
        raise ValidationError({
            'assignee': '负责人必须是该参赛队当前有效的负责人或成员',
        })


def _sync_published_workload_contributions(assessment, allocations, decided_by, now):
    """把当前发布版本固化为可追溯的已核验比赛贡献，不重复累计版本。"""
    competition = assessment.competition
    marker = '比赛有效工作量评议：'
    period = (
        getattr(getattr(competition, 'event', None), 'edition', '')
        or competition.name
    )[:20]
    allocated_user_ids = {allocation.user_id for allocation in allocations}

    (
        Contribution.objects.filter(
            project=competition.project,
            source_type=Contribution.SourceType.COMPETITION,
            related_object_id=competition.id,
            content__startswith=marker,
        )
        .exclude(user_id__in=allocated_user_ids)
        .update(
            score=Decimal('0.00'),
            weight=Decimal('0.00'),
            status=Contribution.Status.REJECTED,
            source_verified=False,
            reviewer=decided_by,
            reviewed_at=now,
            review_opinion='已被最新发布的比赛工作量版本移出',
            updated_at=now,
        )
    )

    entry_label = competition.entry_name or competition.name
    for allocation in allocations:
        content = (
            f'{marker}{entry_label} v{assessment.version}，'
            f'有效工作量占比 {allocation.percentage}%'
        )
        existing = (
            Contribution.objects.filter(
                project=competition.project,
                user_id=allocation.user_id,
                source_type=Contribution.SourceType.COMPETITION,
                related_object_id=competition.id,
                content__startswith=marker,
            )
            .order_by('id')
            .first()
        )
        values = {
            'contribution_type': Contribution.ContributionType.COMPETITION,
            'description': content,
            'content': content,
            'score': allocation.percentage,
            'weight': allocation.percentage,
            'status': Contribution.Status.APPROVED,
            'source_verified': True,
            'period': period,
            'filled_by': decided_by,
            'reviewer': decided_by,
            'reviewed_at': now,
            'review_opinion': (
                f'参赛队负责人发布工作量评议 v{assessment.version}；'
                f'{allocation.rationale or "未填写补充依据"}'
            ),
        }
        if existing is None:
            Contribution.objects.create(
                project=competition.project,
                user_id=allocation.user_id,
                source_type=Contribution.SourceType.COMPETITION,
                related_object_id=competition.id,
                **values,
            )
        else:
            for field, value in values.items():
                setattr(existing, field, value)
            existing.save(update_fields=[*values, 'updated_at'])


class CompetitionWorkItemViewSet(ModelViewSet):
    """Task-backed work items scoped to one exact competition entry."""

    serializer_class = CompetitionWorkItemSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    queryset = (
        Task.objects
        .filter(competition_entry__isnull=False)
        .select_related(
            'competition_entry__event',
            'competition_entry__project',
            'project',
            'assignee',
            'creator',
            'reviewer',
        )
        .prefetch_related(
            'collaborators',
            'subtasks__assignee',
        )
        .order_by('deadline', '-created_at')
    )

    def _ensure_can_change(self, task):
        competition = task.competition_entry
        if (
            task.assignee_id != self.request.user.id
            and task.reviewer_id != self.request.user.id
            and not can_manage_competition(self.request.user, competition)
        ):
            raise PermissionDenied('只能维护自己负责、待自己验收或有管理权限的工作项')
        return competition

    def get_object(self):
        task = super().get_object()
        if not can_view_competition_entry(
            self.request.user,
            task.competition_entry,
        ):
            raise PermissionDenied('无权访问该参赛队工作项')
        return task

    def list(self, request, *args, **kwargs):
        competition = _resolve_competition(
            request.user,
            request.query_params.get('competition'),
        )
        queryset = self.filter_queryset(
            self.get_queryset().filter(competition_entry=competition),
        )
        if request.query_params.get('mine') == '1':
            queryset = queryset.filter(
                Q(assignee=request.user)
                | Q(collaborators=request.user)
                | Q(reviewer=request.user)
            ).distinct()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if not data.get('assignee'):
            data['assignee'] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        competition = serializer.validated_data['competition_entry']
        if not can_view_competition_entry(request.user, competition):
            raise PermissionDenied('无权访问该参赛队')

        assignee = serializer.validated_data['assignee']
        _validate_work_item_assignee(competition, assignee)
        manager = can_manage_competition(request.user, competition)
        if not manager and assignee.id != request.user.id:
            raise PermissionDenied('普通成员只能给自己创建工作项')
        reviewer = serializer.validated_data.get('reviewer')
        if (
            serializer.validated_data.get('status') == Task.Status.DONE
            and reviewer is not None
            and reviewer.id != request.user.id
            and not manager
        ):
            raise ValidationError({
                'status': '已指定验收人时，任务负责人应先提交“待审核”，由验收人确认完成',
            })

        with transaction.atomic():
            task = serializer.save(
                project=competition.project,
                creator=request.user,
            )
            if task.status == Task.Status.DONE:
                task.completed_at = timezone.now()
                task.save(update_fields=['completed_at', 'updated_at'])
            TaskLog.objects.create(
                task=task,
                from_status='',
                to_status=task.status,
                operator=request.user,
            )
        return success_response(
            self.get_serializer(task).data,
            message='比赛工作项已创建',
            http_status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()
        competition = self._ensure_can_change(task)
        manager = can_manage_competition(request.user, competition)
        assignee_actor = task.assignee_id == request.user.id
        reviewer_actor = task.reviewer_id == request.user.id

        with transaction.atomic():
            task = (
                Task.objects.select_for_update()
                .get(pk=task.pk)
            )
            serializer = self.get_serializer(
                task,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)

            if reviewer_actor and not assignee_actor and not manager:
                unsupported = set(request.data.keys()) - {
                    'status',
                    'completion_note',
                }
                if unsupported:
                    raise PermissionDenied(
                        '验收人只能确认任务状态并填写验收说明',
                    )

            assignee = serializer.validated_data.get(
                'assignee',
                task.assignee,
            )
            if assignee.id != task.assignee_id and not manager:
                raise PermissionDenied('普通成员不能转派工作项')
            _validate_work_item_assignee(competition, assignee)

            old_status = task.status
            requested_status = serializer.validated_data.get('status', old_status)
            reviewer = serializer.validated_data.get('reviewer', task.reviewer)
            if (
                requested_status == Task.Status.DONE
                and reviewer is not None
                and assignee_actor
                and not manager
                and reviewer.id != request.user.id
            ):
                raise ValidationError({
                    'status': '请先提交“待审核”，由指定验收人确认完成',
                })
            if (
                reviewer_actor
                and not manager
                and requested_status not in {
                    Task.Status.PENDING_REVIEW,
                    Task.Status.DOING,
                    Task.Status.DONE,
                }
            ):
                raise ValidationError({
                    'status': '验收人只能确认完成或退回进行中',
                })
            task = serializer.save(project=competition.project)
            update_fields = []
            if task.status == Task.Status.DONE and old_status != Task.Status.DONE:
                task.completed_at = timezone.now()
                update_fields.append('completed_at')
            elif old_status == Task.Status.DONE and task.status != Task.Status.DONE:
                task.completed_at = None
                update_fields.append('completed_at')
            if update_fields:
                task.save(update_fields=update_fields + ['updated_at'])
            if old_status != task.status:
                TaskLog.objects.create(
                    task=task,
                    from_status=old_status,
                    to_status=task.status,
                    operator=request.user,
                )
        return success_response(
            self.get_serializer(task).data,
            message='比赛工作项已更新',
        )

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        self._ensure_can_change(task)
        task.soft_delete(request.user)
        return success_response(message='比赛工作项已删除')


def _assessment_queryset():
    return (
        CompetitionWorkloadAssessment.objects
        .select_related(
            'competition__event',
            'competition__project',
            'competition__project__leader',
            'decided_by',
        )
        .prefetch_related(
            'competition__project__members',
            'competition__project__teams',
            'allocations__user',
            'allocations__objections',
        )
        .order_by('-version', '-created_at')
    )


class CompetitionWorkloadAssessmentViewSet(
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """Versioned, publishable workload decisions for a competition entry."""

    serializer_class = CompetitionWorkloadAssessmentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']
    queryset = _assessment_queryset()

    def get_object(self):
        assessment = super().get_object()
        competition = assessment.competition
        if not can_view_competition_entry(self.request.user, competition):
            raise PermissionDenied('无权访问该参赛队评议')
        if (
            assessment.status
            == CompetitionWorkloadAssessment.Status.DRAFT
            and not can_manage_competition(self.request.user, competition)
        ):
            raise PermissionDenied('评议草稿仅负责人可见')
        return assessment

    def list(self, request, *args, **kwargs):
        competition = _resolve_competition(
            request.user,
            request.query_params.get('competition'),
        )
        queryset = self.get_queryset().filter(competition=competition)
        if not can_manage_competition(request.user, competition):
            queryset = queryset.exclude(
                status=CompetitionWorkloadAssessment.Status.DRAFT,
            )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    @action(detail=False, methods=['post'], url_path='save-draft')
    def save_draft(self, request):
        input_serializer = CompetitionWorkloadDraftInputSerializer(
            data=request.data,
        )
        input_serializer.is_valid(raise_exception=True)
        competition = input_serializer.validated_data['competition']
        if not can_manage_competition(request.user, competition):
            raise PermissionDenied('仅参赛队负责人可保存评议草稿')

        incoming = input_serializer.validated_data['allocations']
        eligible_ids = {
            participant.user_id
            for participant in eligible_allocation_participants(competition)
        }
        incoming_ids = {item['user'].id for item in incoming}
        if not incoming_ids.issubset(eligible_ids):
            raise ValidationError({
                'allocations': '只能为该参赛队当前有效的负责人或成员分配比例',
            })

        with transaction.atomic():
            locked_competition = Competition.objects.select_for_update().get(
                pk=competition.pk,
            )
            assessments = (
                CompetitionWorkloadAssessment.objects
                .select_for_update()
                .filter(competition=locked_competition)
            )
            draft = assessments.filter(
                status=CompetitionWorkloadAssessment.Status.DRAFT,
            ).order_by('-version').first()
            created = draft is None
            if draft is None:
                max_version = assessments.aggregate(
                    max_version=Max('version'),
                )['max_version'] or 0
                draft = CompetitionWorkloadAssessment.objects.create(
                    competition=locked_competition,
                    version=max_version + 1,
                    status=CompetitionWorkloadAssessment.Status.DRAFT,
                    decision_note=input_serializer.validated_data[
                        'decision_note'
                    ],
                    decided_by=request.user,
                    is_current=False,
                )
            else:
                draft.decision_note = input_serializer.validated_data[
                    'decision_note'
                ]
                draft.decided_by = request.user
                draft.save(
                    update_fields=[
                        'decision_note',
                        'decided_by',
                        'updated_at',
                    ],
                )

            draft.allocations.all().delete()
            CompetitionWorkloadAllocation.objects.bulk_create([
                CompetitionWorkloadAllocation(
                    assessment=draft,
                    user=item['user'],
                    percentage=item['percentage'],
                    rationale=item['rationale'],
                )
                for item in incoming
            ])

        draft = _assessment_queryset().get(pk=draft.pk)
        return success_response(
            self.get_serializer(draft).data,
            message='评议草稿已保存',
            http_status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        assessment = self.get_object()
        competition = assessment.competition
        if not can_manage_competition(request.user, competition):
            raise PermissionDenied('仅参赛队负责人可发布评议')

        with transaction.atomic():
            assessment = (
                CompetitionWorkloadAssessment.objects
                .select_for_update()
                .select_related('competition')
                .get(pk=assessment.pk)
            )
            if (
                assessment.status
                != CompetitionWorkloadAssessment.Status.DRAFT
            ):
                raise ValidationError({
                    'status': '只有草稿评议可以发布',
                })

            eligible_ids = {
                participant.user_id
                for participant in eligible_allocation_participants(
                    assessment.competition,
                )
            }
            allocations = list(
                CompetitionWorkloadAllocation.objects
                .select_for_update()
                .filter(assessment=assessment)
            )
            allocated_ids = {
                allocation.user_id for allocation in allocations
            }
            if allocated_ids != eligible_ids:
                raise ValidationError({
                    'allocations': '发布前必须覆盖全部当前有效负责人和成员，且不能包含无效成员',
                })

            total = sum(
                (allocation.percentage for allocation in allocations),
                Decimal('0.00'),
            )
            if total != Decimal('100.00'):
                raise ValidationError({
                    'allocations': '贡献比例合计必须精确等于 100.00',
                })

            now = timezone.now()
            (
                CompetitionWorkloadAssessment.objects
                .filter(
                    competition=assessment.competition,
                    is_current=True,
                )
                .exclude(pk=assessment.pk)
                .update(
                    status=CompetitionWorkloadAssessment.Status.SUPERSEDED,
                    is_current=False,
                    updated_at=now,
                )
            )
            assessment.status = (
                CompetitionWorkloadAssessment.Status.PUBLISHED
            )
            assessment.is_current = True
            assessment.decided_by = request.user
            assessment.published_at = now
            assessment.save(
                update_fields=[
                    'status',
                    'is_current',
                    'decided_by',
                    'published_at',
                    'updated_at',
                ],
            )
            _sync_published_workload_contributions(
                assessment,
                allocations,
                request.user,
                now,
            )

        assessment = _assessment_queryset().get(pk=assessment.pk)
        return success_response(
            self.get_serializer(assessment).data,
            message='评议已发布',
        )


def _objection_queryset():
    return (
        CompetitionWorkloadObjection.objects
        .select_related(
            'allocation__user',
            'allocation__assessment__competition__event',
            'allocation__assessment__competition__project',
            'allocation__assessment__competition__project__leader',
            'raised_by',
            'resolved_by',
        )
        .prefetch_related(
            'allocation__assessment__competition__project__members',
            'allocation__assessment__competition__project__teams',
        )
        .order_by('-created_at')
    )


class CompetitionWorkloadObjectionViewSet(
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """Participant objections to the current published workload decision."""

    serializer_class = CompetitionWorkloadObjectionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']
    queryset = _objection_queryset()

    def get_object(self):
        objection = super().get_object()
        competition = objection.allocation.assessment.competition
        if not can_view_competition_entry(self.request.user, competition):
            raise PermissionDenied('无权访问该参赛队异议')
        return objection

    def list(self, request, *args, **kwargs):
        competition = _resolve_competition(
            request.user,
            request.query_params.get('competition'),
        )
        queryset = self.get_queryset().filter(
            allocation__assessment__competition=competition,
        )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        input_serializer = CompetitionWorkloadObjectionCreateSerializer(
            data=request.data,
        )
        input_serializer.is_valid(raise_exception=True)
        allocation = input_serializer.validated_data['allocation']
        assessment = allocation.assessment
        competition = assessment.competition
        if (
            assessment.status
            != CompetitionWorkloadAssessment.Status.PUBLISHED
            or not assessment.is_current
        ):
            raise ValidationError({
                'allocation': '只能对当前已发布评议提出异议',
            })
        if not is_active_competition_participant(
            request.user,
            competition,
        ):
            raise PermissionDenied('仅该参赛队当前成员可提出异议')
        if CompetitionWorkloadObjection.objects.filter(
            allocation=allocation,
            raised_by=request.user,
            status=CompetitionWorkloadObjection.Status.OPEN,
        ).exists():
            raise ValidationError({
                'allocation': '你对该分配已有一条待处理异议',
            })

        try:
            with transaction.atomic():
                objection = CompetitionWorkloadObjection.objects.create(
                    allocation=allocation,
                    raised_by=request.user,
                    reason=input_serializer.validated_data['reason'],
                )
        except IntegrityError as exc:
            raise ValidationError({
                'allocation': '你对该分配已有一条待处理异议',
            }) from exc

        objection = _objection_queryset().get(pk=objection.pk)
        return success_response(
            self.get_serializer(objection).data,
            message='异议已提交',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        objection = self.get_object()
        competition = objection.allocation.assessment.competition
        if not can_manage_competition(request.user, competition):
            raise PermissionDenied('仅参赛队负责人可处理异议')
        input_serializer = CompetitionWorkloadObjectionResolveSerializer(
            data=request.data,
        )
        input_serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            objection = (
                CompetitionWorkloadObjection.objects
                .select_for_update()
                .get(pk=objection.pk)
            )
            if objection.status != CompetitionWorkloadObjection.Status.OPEN:
                raise ValidationError({
                    'status': '该异议已经处理',
                })
            objection.status = input_serializer.validated_data['status']
            objection.response = input_serializer.validated_data['response']
            objection.resolved_by = request.user
            objection.resolved_at = timezone.now()
            objection.save(
                update_fields=[
                    'status',
                    'response',
                    'resolved_by',
                    'resolved_at',
                    'updated_at',
                ],
            )

        objection = _objection_queryset().get(pk=objection.pk)
        return success_response(
            self.get_serializer(objection).data,
            message='异议已处理',
        )
