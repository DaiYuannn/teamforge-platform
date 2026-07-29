"""排名周期、单次计分及可追溯快照。"""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.contributions.models import Contribution, MemberRanking, RankingObjection
from apps.contributions.services import RANKING_RULE_VERSION, RankingService
from apps.projects.models import ProjectMember


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestRankingRules:
    def test_operating_teacher_can_review_assigned_contribution_without_self_review(
        self, make_project, make_user
    ):
        project = make_project()
        member = make_user(email='teacher-review-member@test.com')
        assigned_reviewer = make_user(
            email='teacher-review-assigned@test.com',
        )
        operating_teacher = make_user(
            email='teacher-review-operator@test.com',
            global_role='teacher',
        )
        ProjectMember.objects.create(project=project, user=member)
        contribution = Contribution.objects.create(
            project=project,
            user=member,
            filled_by=project.leader,
            reviewer=assigned_reviewer,
            contribution_type=Contribution.ContributionType.STAGE_TASK,
            content='已交付比赛材料',
            weight=Decimal('10'),
        )

        response = client_for(operating_teacher).patch(
            (
                '/api/v1/contributions/contributions/'
                f'{contribution.id}/review/'
            ),
            {
                'status': Contribution.Status.APPROVED,
                'review_opinion': '操作老师兜底核验通过',
                'weight': '12.00',
            },
            format='json',
        )

        assert response.status_code == 200, response.json()
        contribution.refresh_from_db()
        assert contribution.reviewer_id == operating_teacher.id
        assert contribution.status == Contribution.Status.APPROVED

    def test_project_leader_confirms_ranking_but_member_cannot(
        self, make_project, make_user
    ):
        project = make_project()
        member = make_user(email='ranking-confirm-member@test.com')
        ProjectMember.objects.create(project=project, user=member)
        ranking = MemberRanking.objects.create(
            project=project,
            user=member,
            period='2026-08',
            rank=1,
            total_score=Decimal('20'),
        )

        denied = client_for(member).post(
            '/api/v1/contributions/rankings/confirm/',
            {'ids': [ranking.id]},
            format='json',
        )
        confirmed = client_for(project.leader).post(
            '/api/v1/contributions/rankings/confirm/',
            {'ids': [ranking.id]},
            format='json',
        )

        assert denied.status_code == 403, denied.json()
        assert confirmed.status_code == 200, confirmed.json()
        ranking.refresh_from_db()
        assert ranking.status == MemberRanking.Status.CONFIRMED
        assert ranking.is_public is True
        assert ranking.confirmed_by_id == project.leader_id

    def test_ranking_objection_requires_two_independent_reviewers(
        self, make_project, make_user
    ):
        project = make_project()
        co_lead = make_user(email='ranking-independent-co-lead@test.com')
        objector = make_user(email='ranking-independent-objector@test.com')
        ProjectMember.objects.create(
            project=project,
            user=co_lead,
            role_in_project=ProjectMember.RoleInProject.LEADER,
        )
        ProjectMember.objects.create(project=project, user=objector)
        ranking = MemberRanking.objects.create(
            project=project,
            user=objector,
            period='2026-08',
            rank=1,
            total_score=Decimal('20'),
            status=MemberRanking.Status.CONFIRMED,
            is_public=True,
            is_published=True,
        )
        objection = RankingObjection.objects.create(
            ranking=ranking,
            objector=objector,
            content='贡献证据需要重新核对',
        )
        initial_url = (
            f'/api/v1/contributions/objections/{objection.id}/leader_review/'
        )
        final_url = (
            f'/api/v1/contributions/objections/{objection.id}/teacher_confirm/'
        )

        self_review = client_for(objector).patch(
            initial_url,
            {'action': 'leader_review', 'leader_opinion': '我确认自己的异议'},
            format='json',
        )
        initial_review = client_for(co_lead).patch(
            initial_url,
            {'action': 'leader_review', 'leader_opinion': '证据需要复核'},
            format='json',
        )
        duplicate_review = client_for(co_lead).patch(
            final_url,
            {
                'action': 'teacher_confirm',
                'final_status': 'rejected',
                'teacher_opinion': '同一人再次审核',
            },
            format='json',
        )
        final_review = client_for(project.leader).patch(
            final_url,
            {
                'action': 'teacher_confirm',
                'final_status': 'rejected',
                'teacher_opinion': '第二位负责人独立复核',
            },
            format='json',
        )

        assert self_review.status_code == 403, self_review.json()
        assert initial_review.status_code == 200, initial_review.json()
        assert duplicate_review.status_code == 403, duplicate_review.json()
        assert final_review.status_code == 200, final_review.json()
        objection.refresh_from_db()
        assert objection.status == RankingObjection.Status.REJECTED
        assert objection.leader_reviewer_id == co_lead.id
        assert objection.teacher_confirmer_id == project.leader_id

    def test_category_priority_precedes_total_score(
        self, make_project, make_user
    ):
        project = make_project()
        actual_member = make_user(email='ranking-actual@test.com')
        resource_member = make_user(email='ranking-resource@test.com')
        ProjectMember.objects.create(project=project, user=actual_member)
        ProjectMember.objects.create(project=project, user=resource_member)
        Contribution.objects.create(
            user=actual_member,
            project=project,
            contribution_type=Contribution.ContributionType.TASK_COMPLETE,
            weight=Decimal('1'),
            status=Contribution.Status.APPROVED,
            period='2026-07',
        )
        Contribution.objects.create(
            user=resource_member,
            project=project,
            contribution_type=Contribution.ContributionType.RESOURCE,
            weight=Decimal('1000'),
            status=Contribution.Status.APPROVED,
            period='2026-07',
        )

        _, rankings = RankingService.generate_ranking_draft(project, '2026-07')
        rank_by_user = {item.user_id: item.rank for item in rankings}

        assert rank_by_user[actual_member.id] < rank_by_user[resource_member.id]
        resource_ranking = next(
            item for item in rankings if item.user_id == resource_member.id
        )
        actual_ranking = next(
            item for item in rankings if item.user_id == actual_member.id
        )
        assert resource_ranking.total_score > actual_ranking.total_score

    def test_exact_period_filter_and_no_duplicate_scoring(
        self, make_project, make_user
    ):
        project = make_project()
        member = make_user(email='ranking-period@test.com')
        ProjectMember.objects.create(project=project, user=member)
        included = Contribution.objects.create(
            user=member,
            project=project,
            contribution_type=Contribution.ContributionType.TASK_COMPLETE,
            weight=Decimal('10'),
            status=Contribution.Status.APPROVED,
            period='2026-07',
        )
        Contribution.objects.create(
            user=member,
            project=project,
            contribution_type=Contribution.ContributionType.COMPETITION,
            weight=Decimal('100'),
            status=Contribution.Status.APPROVED,
            period='2026-06',
        )
        Contribution.objects.create(
            user=member,
            project=project,
            contribution_type=Contribution.ContributionType.RESOURCE,
            weight=Decimal('100'),
            status=Contribution.Status.PENDING,
            period='2026-07',
        )

        success, rankings = RankingService.generate_ranking_draft(
            project, period='2026-07'
        )
        assert success is True
        ranking = next(item for item in rankings if item.user_id == member.id)
        # 任务贡献只计算审核权重一次，不再额外叠加旧版固定任务分。
        assert ranking.total_score == Decimal('10.00')
        assert ranking.task_completed_count == 1
        assert ranking.rule_version == RANKING_RULE_VERSION
        assert ranking.score_snapshot['evidence_count'] == 1
        assert ranking.score_snapshot['evidence'][0]['contribution_id'] == included.id

    def test_type_multiplier_and_arbitrary_named_period(
        self, make_project, make_user
    ):
        project = make_project()
        member = make_user(email='ranking-rule@test.com')
        ProjectMember.objects.create(project=project, user=member)
        Contribution.objects.create(
            user=member,
            project=project,
            contribution_type=Contribution.ContributionType.RESOURCE,
            weight=Decimal('10'),
            status=Contribution.Status.APPROVED,
            period='2026春季',
        )
        _, rankings = RankingService.generate_ranking_draft(
            project, period='2026春季'
        )
        ranking = next(item for item in rankings if item.user_id == member.id)
        assert ranking.total_score == Decimal('8.00')
        assert ranking.score_snapshot['breakdown']['resource'] == '8.00'
        assert ranking.rule_snapshot['type_multipliers']['resource'] == '0.80'

    def test_regeneration_replaces_draft_without_duplicating_evidence(
        self, make_project, make_user
    ):
        project = make_project()
        member = make_user(email='ranking-regenerate@test.com')
        ProjectMember.objects.create(project=project, user=member)
        Contribution.objects.create(
            user=member,
            project=project,
            contribution_type=Contribution.ContributionType.STAGE_TASK,
            weight=Decimal('25'),
            status=Contribution.Status.APPROVED,
            period='2026-07',
        )
        RankingService.generate_ranking_draft(project, '2026-07')
        RankingService.generate_ranking_draft(project, '2026-07')
        rankings = MemberRanking.objects.filter(
            project=project, user=member, period='2026-07'
        )
        assert rankings.count() == 1
        assert rankings.get().score_snapshot['evidence_count'] == 1

    def test_confirmation_freezes_rule_snapshot(
        self, make_project, make_user
    ):
        project = make_project()
        member = make_user(email='ranking-confirm@test.com')
        ProjectMember.objects.create(project=project, user=member)
        Contribution.objects.create(
            user=member,
            project=project,
            contribution_type=Contribution.ContributionType.STAGE_TASK,
            weight=Decimal('20'),
            status=Contribution.Status.APPROVED,
            period='2026-07',
        )
        _, rankings = RankingService.generate_ranking_draft(project, '2026-07')
        ranking = next(item for item in rankings if item.user_id == member.id)
        rule_snapshot = ranking.rule_snapshot
        success, count = RankingService.confirm_ranking([ranking.id], project.leader)
        assert success is True
        assert count == 1
        ranking.refresh_from_db()
        assert ranking.status == MemberRanking.Status.CONFIRMED
        assert ranking.confirmed_by == project.leader
        assert ranking.confirmed_at is not None
        assert ranking.rule_snapshot == rule_snapshot

        # 同周期重新生成不得覆盖已确认结果。
        RankingService.generate_ranking_draft(project, '2026-07')
        ranking.refresh_from_db()
        assert ranking.status == MemberRanking.Status.CONFIRMED

    def test_approved_objection_reorders_public_ranking_and_records_audit(
        self, make_project, make_user
    ):
        project = make_project()
        second = make_user(email='ranking-objection-second@test.com')
        third = make_user(email='ranking-objection-third@test.com')
        teacher = make_user(
            email='ranking-objection-teacher@test.com',
            global_role='teacher',
        )
        ProjectMember.objects.create(project=project, user=second)
        ProjectMember.objects.create(project=project, user=third)
        users = [project.leader, second, third]
        rankings = [
            MemberRanking.objects.create(
                project=project,
                user=user,
                period='2026-07',
                rank=index,
                total_score=Decimal(str(40 - index * 5)),
                status=MemberRanking.Status.CONFIRMED,
                is_public=True,
                is_published=True,
                score_snapshot={'seed_rank': index},
            )
            for index, user in enumerate(users, start=1)
        ]
        objection = RankingObjection.objects.create(
            ranking=rankings[2],
            objector=third,
            content='实际项目产出未完整计入',
            status=RankingObjection.Status.LEADER_REVIEWED,
            leader_reviewer=project.leader,
        )

        success, result = RankingService.resolve_objection(
            objection,
            teacher,
            RankingObjection.Status.APPROVED,
            corrected_rank=1,
            corrected_total_score=Decimal('42.50'),
        )

        assert success is True
        for ranking in rankings:
            ranking.refresh_from_db()
        result.refresh_from_db()
        assert [rankings[2].rank, rankings[0].rank, rankings[1].rank] == [1, 2, 3]
        assert rankings[2].total_score == Decimal('42.50')
        assert result.original_rank == 3
        assert result.corrected_rank == 1
        assert result.adjustment_applied_by_id == teacher.id
        assert result.adjustment_applied_at is not None
        assert len(result.adjustment_snapshot['rank_changes']) == 3
        assert rankings[2].score_snapshot['objection_adjustments'][0][
            'objection_id'
        ] == objection.id

    def test_approved_objection_rejects_noop_adjustment(
        self, make_project, make_user
    ):
        project = make_project()
        teacher = make_user(
            email='ranking-noop-teacher@test.com',
            global_role='teacher',
        )
        ranking = MemberRanking.objects.create(
            project=project,
            user=project.leader,
            period='2026-07',
            rank=1,
            total_score=Decimal('20'),
            status=MemberRanking.Status.CONFIRMED,
            is_public=True,
        )
        objection = RankingObjection.objects.create(
            ranking=ranking,
            objector=project.leader,
            content='请求复核',
            status=RankingObjection.Status.LEADER_REVIEWED,
        )

        success, message = RankingService.resolve_objection(
            objection,
            teacher,
            RankingObjection.Status.APPROVED,
            corrected_rank=1,
            corrected_total_score=Decimal('20'),
        )

        assert success is False
        assert '实际变化' in message
        objection.refresh_from_db()
        ranking.refresh_from_db()
        assert objection.status == RankingObjection.Status.LEADER_REVIEWED
        assert ranking.rank == 1
