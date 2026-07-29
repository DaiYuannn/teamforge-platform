from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.team_models import Team, TeamMember
from apps.competitions.models import (
    Competition,
    CompetitionEvent,
    CompetitionParticipant,
)
from apps.contributions.models import Contribution
from apps.tasks.models import Task
from apps.tasks.workload_models import CompetitionWorkloadAssessment


WORK_ITEMS_URL = '/api/v1/members/competition-work-items/'
ASSESSMENTS_URL = '/api/v1/members/workload-assessments/'
OBJECTIONS_URL = '/api/v1/members/workload-objections/'


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def response_data(response):
    payload = response.json()
    return payload.get('data', payload)


def response_rows(response):
    data = response_data(response)
    return data.get('results', data)


@pytest.fixture
def workload_context(make_project, make_user):
    manager = make_user(
        email='workload-manager@test.com',
        name='参赛队负责人',
    )
    member = make_user(
        email='workload-member@test.com',
        name='参赛成员',
    )
    entry_two_member = make_user(
        email='entry-two-member@test.com',
        name='其他参赛队成员',
    )
    advisor = make_user(
        email='workload-advisor@test.com',
        name='参赛顾问',
    )
    cross_root_teacher = make_user(
        email='cross-root-teacher@test.com',
        name='其他组织老师',
        global_role='teacher',
    )

    root = Team.objects.create(
        name='工作量测试总团队',
        code='WORKLOAD-ROOT',
        owner=manager,
    )
    other_root = Team.objects.create(
        name='其他工作量测试总团队',
        code='OTHER-WORKLOAD-ROOT',
        owner=cross_root_teacher,
    )
    for user, role in (
        (manager, TeamMember.Role.OWNER),
        (member, TeamMember.Role.MEMBER),
        (entry_two_member, TeamMember.Role.MEMBER),
        (advisor, TeamMember.Role.TEACHER),
    ):
        TeamMember.objects.create(team=root, user=user, role=role)
    TeamMember.objects.create(
        team=other_root,
        user=cross_root_teacher,
        role=TeamMember.Role.TEACHER,
    )

    project = make_project(
        leader=manager,
        name='工作量测试项目',
        code='WORKLOAD-PROJECT',
    )
    project.teams.add(root)
    event = CompetitionEvent.objects.create(
        organization=root,
        name='工作量测试比赛',
        edition='2026',
    )
    entry = Competition.objects.create(
        project=project,
        event=event,
        name=event.name,
        entry_name='第一参赛队',
    )
    entry_two = Competition.objects.create(
        project=project,
        event=event,
        name=event.name,
        entry_name='第二参赛队',
    )
    for user, role in (
        (manager, CompetitionParticipant.Role.LEADER),
        (member, CompetitionParticipant.Role.MEMBER),
        (advisor, CompetitionParticipant.Role.ADVISOR),
    ):
        CompetitionParticipant.objects.create(
            competition=entry,
            user=user,
            role=role,
            participation_status=(
                CompetitionParticipant.ParticipationStatus.CONFIRMED
            ),
        )
    CompetitionParticipant.objects.create(
        competition=entry_two,
        user=entry_two_member,
        role=CompetitionParticipant.Role.MEMBER,
        participation_status=(
            CompetitionParticipant.ParticipationStatus.CONFIRMED
        ),
    )
    return {
        'manager': manager,
        'member': member,
        'entry_two_member': entry_two_member,
        'advisor': advisor,
        'cross_root_teacher': cross_root_teacher,
        'project': project,
        'entry': entry,
        'entry_two': entry_two,
    }


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_work_items_require_entry_derive_project_and_isolate_entries(
    workload_context,
):
    ctx = workload_context
    member_client = client_for(ctx['member'])
    deadline = timezone.now() + timedelta(days=2)

    missing_query = member_client.get(WORK_ITEMS_URL)
    assert missing_query.status_code == 400, missing_query.json()

    created = member_client.post(
        WORK_ITEMS_URL,
        {
            'competition': ctx['entry'].id,
            'project': 999999,
            'title': '准备路演材料',
            'deadline': deadline.isoformat(),
            'status': Task.Status.DONE,
            'reference_note': '参考上一届答辩结构',
        },
        format='json',
    )
    assert created.status_code == 201, created.json()
    item = response_data(created)
    assert item['competition'] == ctx['entry'].id
    assert item['project'] == ctx['project'].id
    assert item['assignee'] == ctx['member'].id
    assert item['status'] == Task.Status.DONE
    assert item['completed_at'] is not None
    assert item['reference_note'] == '参考上一届答辩结构'
    assert set(item) == {
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
    }
    legacy_list = client_for(ctx['entry_two_member']).get(
        '/api/v1/tasks/',
        {'project': ctx['project'].id},
    )
    assert legacy_list.status_code == 200, legacy_list.json()
    assert response_rows(legacy_list) == []
    legacy_detail = member_client.get(f"/api/v1/tasks/{item['id']}/")
    assert legacy_detail.status_code == 404, legacy_detail.json()

    same_values = member_client.patch(
        f"{WORK_ITEMS_URL}{item['id']}/",
        {
            'competition': ctx['entry'].id,
            'assignee': ctx['member'].id,
            'title': '准备最终路演材料',
        },
        format='json',
    )
    assert same_values.status_code == 200, same_values.json()

    transfer = member_client.patch(
        f"{WORK_ITEMS_URL}{item['id']}/",
        {'assignee': ctx['manager'].id},
        format='json',
    )
    assert transfer.status_code == 403, transfer.json()

    cross_entry = member_client.get(
        WORK_ITEMS_URL,
        {'competition': ctx['entry_two'].id},
    )
    assert cross_entry.status_code == 403, cross_entry.json()
    cross_root = client_for(ctx['cross_root_teacher']).get(
        WORK_ITEMS_URL,
        {'competition': ctx['entry'].id},
    )
    assert cross_root.status_code == 200, cross_root.json()

    advisor_assignment = client_for(ctx['manager']).post(
        WORK_ITEMS_URL,
        {
            'competition': ctx['entry'].id,
            'assignee': ctx['advisor'].id,
            'title': '不应分配给顾问',
            'deadline': deadline.isoformat(),
        },
        format='json',
    )
    assert advisor_assignment.status_code == 400, advisor_assignment.json()


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_competition_work_item_exposes_collaboration_subtasks_and_review(
    workload_context,
):
    ctx = workload_context
    member_client = client_for(ctx['member'])
    manager_client = client_for(ctx['manager'])
    deadline = timezone.now() + timedelta(days=4)

    created = member_client.post(
        WORK_ITEMS_URL,
        {
            'competition': ctx['entry'].id,
            'title': '完成答辩演示与讲稿',
            'deadline': deadline.isoformat(),
            'priority': Task.Priority.HIGH,
            'collaborators': [ctx['manager'].id],
            'reviewer': ctx['manager'].id,
            'status': Task.Status.PENDING_REVIEW,
            'completion_note': '演示稿与讲稿均已提交',
            'subtasks': [
                {
                    'title': '整理演示稿',
                    'assignee': ctx['member'].id,
                    'is_completed': True,
                    'sort_order': 0,
                },
                {
                    'title': '复核答辩讲稿',
                    'assignee': ctx['manager'].id,
                    'is_completed': False,
                    'sort_order': 1,
                },
            ],
        },
        format='json',
    )
    assert created.status_code == 201, created.json()
    item = response_data(created)
    assert item['collaborators'] == [ctx['manager'].id]
    assert item['collaborator_names'] == [ctx['manager'].name]
    assert item['reviewer'] == ctx['manager'].id
    assert item['reviewer_name'] == ctx['manager'].name
    assert item['priority'] == Task.Priority.HIGH
    assert len(item['subtasks']) == 2
    assert item['subtasks'][0]['is_completed'] is True
    assert item['can_edit'] is True

    self_approve = member_client.patch(
        f"{WORK_ITEMS_URL}{item['id']}/",
        {'status': Task.Status.DONE},
        format='json',
    )
    assert self_approve.status_code == 400, self_approve.json()

    reviewer_view = manager_client.get(
        WORK_ITEMS_URL,
        {'competition': ctx['entry'].id},
    )
    reviewer_item = response_rows(reviewer_view)[0]
    assert reviewer_item['can_review'] is True

    reviewed = manager_client.patch(
        f"{WORK_ITEMS_URL}{item['id']}/",
        {
            'status': Task.Status.DONE,
            'completion_note': '验收通过，成果可用于现场答辩',
        },
        format='json',
    )
    assert reviewed.status_code == 200, reviewed.json()
    reviewed_item = response_data(reviewed)
    assert reviewed_item['status'] == Task.Status.DONE
    assert reviewed_item['completed_at'] is not None
    assert reviewed_item['completion_note'] == '验收通过，成果可用于现场答辩'

    invalid_collaborator = member_client.post(
        WORK_ITEMS_URL,
        {
            'competition': ctx['entry'].id,
            'title': '非法跨参赛队协作',
            'deadline': deadline.isoformat(),
            'collaborators': [ctx['entry_two_member'].id],
        },
        format='json',
    )
    assert invalid_collaborator.status_code == 400, invalid_collaborator.json()


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_workload_publish_requires_full_roster_and_exactly_one_hundred(
    workload_context,
):
    ctx = workload_context
    manager_client = client_for(ctx['manager'])
    member_client = client_for(ctx['member'])

    missing_roster = manager_client.post(
        f'{ASSESSMENTS_URL}save-draft/',
        {
            'competition': ctx['entry'].id,
            'decision_note': '第一轮评议',
            'allocations': [
                {
                    'user': ctx['manager'].id,
                    'percentage': '100.00',
                    'rationale': '统筹',
                },
            ],
        },
        format='json',
    )
    assert missing_roster.status_code == 201, missing_roster.json()
    assessment_id = response_data(missing_roster)['id']
    publish_missing = manager_client.post(
        f'{ASSESSMENTS_URL}{assessment_id}/publish/',
        {},
        format='json',
    )
    assert publish_missing.status_code == 400, publish_missing.json()

    wrong_total = manager_client.post(
        f'{ASSESSMENTS_URL}save-draft/',
        {
            'competition': ctx['entry'].id,
            'decision_note': '第二轮评议',
            'allocations': [
                {
                    'user': ctx['manager'].id,
                    'percentage': '50.00',
                    'rationale': '统筹',
                },
                {
                    'user': ctx['member'].id,
                    'percentage': '40.00',
                    'rationale': '执行',
                },
            ],
        },
        format='json',
    )
    assert wrong_total.status_code == 200, wrong_total.json()
    assert response_data(wrong_total)['id'] == assessment_id
    publish_wrong_total = manager_client.post(
        f'{ASSESSMENTS_URL}{assessment_id}/publish/',
        {},
        format='json',
    )
    assert publish_wrong_total.status_code == 400

    complete = manager_client.post(
        f'{ASSESSMENTS_URL}save-draft/',
        {
            'competition': ctx['entry'].id,
            'decision_note': '最终评议',
            'allocations': [
                {
                    'user': ctx['manager'].id,
                    'percentage': '55.00',
                    'rationale': '统筹与核心方案',
                },
                {
                    'user': ctx['member'].id,
                    'percentage': '45.00',
                    'rationale': '材料与答辩',
                },
            ],
        },
        format='json',
    )
    assert complete.status_code == 200, complete.json()
    published = manager_client.post(
        f'{ASSESSMENTS_URL}{assessment_id}/publish/',
        {},
        format='json',
    )
    assert published.status_code == 200, published.json()
    published_data = response_data(published)
    assert published_data['status'] == 'published'
    assert published_data['is_current'] is True
    assert Decimal(str(published_data['allocation_total'])) == Decimal('100')
    assert Decimal(str(published_data['total'])) == Decimal('100')
    evidence = Contribution.objects.filter(
        project=ctx['project'],
        source_type=Contribution.SourceType.COMPETITION,
        related_object_id=ctx['entry'].id,
        source_verified=True,
        status=Contribution.Status.APPROVED,
    ).order_by('user_id')
    assert evidence.count() == 2
    assert {
        row.user_id: row.weight
        for row in evidence
    } == {
        ctx['manager'].id: Decimal('55.00'),
        ctx['member'].id: Decimal('45.00'),
    }

    member_rows = response_rows(
        member_client.get(
            ASSESSMENTS_URL,
            {'competition': ctx['entry'].id},
        ),
    )
    assert [row['id'] for row in member_rows] == [assessment_id]
    assert member_rows[0]['can_object'] is True

    new_draft = manager_client.post(
        f'{ASSESSMENTS_URL}save-draft/',
        {
            'competition': ctx['entry'].id,
            'decision_note': '新版本',
            'allocations': [
                {
                    'user': ctx['manager'].id,
                    'percentage': '50.00',
                    'rationale': '',
                },
                {
                    'user': ctx['member'].id,
                    'percentage': '50.00',
                    'rationale': '',
                },
            ],
        },
        format='json',
    )
    assert new_draft.status_code == 201, new_draft.json()
    new_draft_data = response_data(new_draft)
    assert new_draft_data['version'] == 2

    # Ordinary participants cannot see the current draft.
    member_rows_with_draft = response_rows(
        member_client.get(
            ASSESSMENTS_URL,
            {'competition': ctx['entry'].id},
        ),
    )
    assert [row['id'] for row in member_rows_with_draft] == [assessment_id]

    second_publish = manager_client.post(
        f"{ASSESSMENTS_URL}{new_draft_data['id']}/publish/",
        {},
        format='json',
    )
    assert second_publish.status_code == 200, second_publish.json()
    old = CompetitionWorkloadAssessment.objects.get(pk=assessment_id)
    assert old.status == CompetitionWorkloadAssessment.Status.SUPERSEDED
    assert old.is_current is False
    refreshed_evidence = Contribution.objects.filter(
        project=ctx['project'],
        source_type=Contribution.SourceType.COMPETITION,
        related_object_id=ctx['entry'].id,
        source_verified=True,
        status=Contribution.Status.APPROVED,
    )
    assert refreshed_evidence.count() == 2
    assert {
        row.user_id: row.weight
        for row in refreshed_evidence
    } == {
        ctx['manager'].id: Decimal('50.00'),
        ctx['member'].id: Decimal('50.00'),
    }


@pytest.mark.api
@pytest.mark.permission
@pytest.mark.django_db
def test_current_participant_can_object_and_manager_can_resolve(
    workload_context,
):
    ctx = workload_context
    manager_client = client_for(ctx['manager'])
    member_client = client_for(ctx['member'])
    draft = manager_client.post(
        f'{ASSESSMENTS_URL}save-draft/',
        {
            'competition': ctx['entry'].id,
            'decision_note': '用于异议测试',
            'allocations': [
                {
                    'user': ctx['manager'].id,
                    'percentage': '60.00',
                    'rationale': '',
                },
                {
                    'user': ctx['member'].id,
                    'percentage': '40.00',
                    'rationale': '',
                },
            ],
        },
        format='json',
    )
    assessment_id = response_data(draft)['id']
    published = manager_client.post(
        f'{ASSESSMENTS_URL}{assessment_id}/publish/',
        {},
        format='json',
    )
    allocations = response_data(published)['allocations']
    manager_allocation = next(
        row for row in allocations if row['user'] == ctx['manager'].id
    )

    created = member_client.post(
        OBJECTIONS_URL,
        {
            'allocation': manager_allocation['id'],
            'reason': '对统筹工作量的依据有疑问',
        },
        format='json',
    )
    assert created.status_code == 201, created.json()
    objection = response_data(created)
    assert objection['competition'] == ctx['entry'].id
    assert objection['assessment'] == assessment_id
    assert objection['raised_by'] == ctx['member'].id
    assert objection['can_resolve'] is False

    duplicate = member_client.post(
        OBJECTIONS_URL,
        {
            'allocation': manager_allocation['id'],
            'reason': '重复异议',
        },
        format='json',
    )
    assert duplicate.status_code == 400, duplicate.json()

    cross_entry = client_for(ctx['entry_two_member']).post(
        OBJECTIONS_URL,
        {
            'allocation': manager_allocation['id'],
            'reason': '不属于这个参赛队',
        },
        format='json',
    )
    assert cross_entry.status_code == 403, cross_entry.json()

    member_resolve = member_client.post(
        f"{OBJECTIONS_URL}{objection['id']}/resolve/",
        {
            'status': 'resolved',
            'response': '无权处理',
        },
        format='json',
    )
    assert member_resolve.status_code == 403

    resolved = manager_client.post(
        f"{OBJECTIONS_URL}{objection['id']}/resolve/",
        {
            'status': 'resolved',
            'response': '已补充评议依据',
        },
        format='json',
    )
    assert resolved.status_code == 200, resolved.json()
    resolved_data = response_data(resolved)
    assert resolved_data['status'] == 'resolved'
    assert resolved_data['resolved_by_name'] == ctx['manager'].name
    assert resolved_data['resolved_at'] is not None

    # A resolved objection no longer blocks a later open objection.
    reopened = member_client.post(
        OBJECTIONS_URL,
        {
            'allocation': manager_allocation['id'],
            'reason': '补充新的事实',
        },
        format='json',
    )
    assert reopened.status_code == 201, reopened.json()

    cross_root_list = client_for(ctx['cross_root_teacher']).get(
        OBJECTIONS_URL,
        {'competition': ctx['entry'].id},
    )
    assert cross_root_list.status_code == 200, cross_root_list.json()
