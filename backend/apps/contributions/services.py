"""
贡献度业务逻辑服务
包含：排名草案生成、排名确认、操作日志记录
排名计算只使用指定周期内已审核的贡献记录，每条记录只计分一次。
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import Contribution, MemberRanking, RankingObjection
from apps.projects.models import ProjectMember, Project
from apps.audit.models import OperationLog


# ============ 排序计算权重配置 ============
RANKING_RULE_VERSION = '2026.2'
POINT_QUANTUM = Decimal('0.01')
RANKING_RULE = {
    'version': RANKING_RULE_VERSION,
    'base_score': '优先采用审核权重 weight；权重为 0 时采用 score',
    'counting': '每条已审核贡献仅计分一次，不再叠加任务/IP/比赛固定分',
    'period_filter': 'Contribution.period 必须与排名 period 完全一致',
    'priority_order': [
        'actual_project',
        'resource',
        'management',
        'team_history',
        'join_time',
    ],
    'type_multipliers': {
        # 实际项目产出
        'task_complete': '1.00',
        'stage_task': '1.00',
        'competition': '1.00',
        'ip_writing': '1.00',
        'ip_execution': '1.00',
        'ip_return_fix': '1.00',
        'ip_archive': '1.00',
        'ip_material': '1.00',
        # 资源贡献
        'resource': '0.80',
        'file_upload': '0.80',
        # 管理责任
        'project_lead': '0.60',
        'project_leader': '0.60',
        'core': '0.60',
        'finance_manage': '0.60',
        # 团队历史贡献
        'long_term': '0.40',
        'exited_contribution': '0.40',
        # 其他
        'temporary_help': '0.25',
        'other': '0.50',
        'nominal': '0.00',
    },
    'ranking_order': [
        '实际项目贡献分',
        '资源贡献分',
        '管理责任分',
        '团队历史贡献分',
        '加入时间较早者',
        '用户ID',
    ],
}

ACTUAL_PROJECT_TYPES = {
    Contribution.ContributionType.TASK_COMPLETE,
    Contribution.ContributionType.STAGE_TASK,
    Contribution.ContributionType.COMPETITION,
    Contribution.ContributionType.IP_WRITING,
    Contribution.ContributionType.IP_EXECUTION,
    Contribution.ContributionType.IP_RETURN_FIX,
    Contribution.ContributionType.IP_ARCHIVE,
    Contribution.ContributionType.IP_MATERIAL,
}
RESOURCE_TYPES = {
    Contribution.ContributionType.RESOURCE,
    Contribution.ContributionType.FILE_UPLOAD,
}
MANAGEMENT_TYPES = {
    Contribution.ContributionType.PROJECT_LEAD,
    Contribution.ContributionType.PROJECT_LEADER,
    Contribution.ContributionType.CORE,
    Contribution.ContributionType.FINANCE_MANAGE,
}
TEAM_HISTORY_TYPES = {
    Contribution.ContributionType.LONG_TERM,
    Contribution.ContributionType.EXITED_CONTRIBUTION,
}

# IP 贡献类型集合
IP_CONTRIBUTION_TYPES = {
    Contribution.ContributionType.IP_WRITING,
    Contribution.ContributionType.IP_EXECUTION,
    Contribution.ContributionType.IP_RETURN_FIX,
    Contribution.ContributionType.IP_ARCHIVE,
    Contribution.ContributionType.IP_MATERIAL,
}


def log_operation(user, action, obj, detail=''):
    """
    写入操作日志辅助方法
    :param user: 操作人
    :param action: 操作动作描述
    :param obj: 操作对象
    :param detail: 操作详情
    """
    object_type = obj.__class__.__name__ if obj else ''
    object_id = str(obj.id) if obj and hasattr(obj, 'id') else ''
    OperationLog.objects.create(
        operator=user,
        operation_type=OperationLog.OperationType.OTHER,
        module='contributions',
        object_type=object_type,
        object_id=object_id,
        description=f'{action}: {detail}',
    )


class RankingService:
    """成员排名服务"""

    @staticmethod
    def _get_member_scores(project, period):
        """
        计算项目所有成员的各项得分
        :param project: 项目实例
        :param period: 统计周期
        :return: {user_id: {user, contribution_score, task_count, ip_count, competition_count, total_score}}
        """
        # 1. 获取项目所有成员（含负责人）
        member_users = []
        # 项目负责人
        if project.leader_id:
            member_users.append(project.leader)
        # 项目成员
        for pm in ProjectMember.objects.filter(project=project).select_related('user'):
            if pm.user not in member_users:
                member_users.append(pm.user)

        # 2. 仅获取指定周期内已审核通过的贡献记录。
        approved_contributions = Contribution.objects.filter(
            project=project,
            status=Contribution.Status.APPROVED,
            period=period,
        ).select_related('user')

        # 按用户聚合贡献
        member_data = {}
        for user in member_users:
            member_data[user.id] = {
                'user': user,
                'contribution_score': Decimal('0'),
                'task_count': 0,
                'ip_count': 0,
                'competition_count': 0,
                'total_score': Decimal('0'),
                'actual_project_score': Decimal('0'),
                'resource_score': Decimal('0'),
                'management_score': Decimal('0'),
                'team_history_score': Decimal('0'),
                'evidence': [],
            }

        # 累加贡献得分
        for contrib in approved_contributions:
            uid = contrib.user_id
            if uid not in member_data:
                # 贡献记录的用户可能不在当前成员列表（如已退出），仍纳入统计
                member_data[uid] = {
                    'user': contrib.user,
                    'contribution_score': Decimal('0'),
                    'task_count': 0,
                    'ip_count': 0,
                    'competition_count': 0,
                    'total_score': Decimal('0'),
                    'actual_project_score': Decimal('0'),
                    'resource_score': Decimal('0'),
                    'management_score': Decimal('0'),
                    'team_history_score': Decimal('0'),
                    'evidence': [],
                }
            # 每条贡献只计一次：审核权重/分值乘以规则中对应类型系数。
            base_point = contrib.weight if contrib.weight else contrib.score
            multiplier = Decimal(
                RANKING_RULE['type_multipliers'].get(
                    contrib.contribution_type,
                    RANKING_RULE['type_multipliers']['other'],
                )
            )
            point = (base_point * multiplier).quantize(POINT_QUANTUM)
            data = member_data[uid]
            data['contribution_score'] += point
            if contrib.contribution_type in ACTUAL_PROJECT_TYPES:
                data['actual_project_score'] += point
            elif contrib.contribution_type in RESOURCE_TYPES:
                data['resource_score'] += point
            elif contrib.contribution_type in MANAGEMENT_TYPES:
                data['management_score'] += point
            elif contrib.contribution_type in TEAM_HISTORY_TYPES:
                data['team_history_score'] += point
            data['evidence'].append({
                'contribution_id': contrib.id,
                'type': contrib.contribution_type,
                'base_score': str(base_point),
                'multiplier': str(multiplier),
                'weighted_score': str(point),
                'reviewer_id': contrib.reviewer_id,
                'reviewed_at': (
                    contrib.reviewed_at.isoformat()
                    if contrib.reviewed_at
                    else None
                ),
            })
            # IP 贡献计数
            if contrib.contribution_type in IP_CONTRIBUTION_TYPES:
                data['ip_count'] += 1
            # 比赛参与计数
            if contrib.contribution_type == Contribution.ContributionType.COMPETITION:
                data['competition_count'] += 1
            if contrib.contribution_type == Contribution.ContributionType.TASK_COMPLETE:
                data['task_count'] += 1

        # 3. 综合得分就是每条证据一次计分后的总和，不再重复叠加固定分。
        for uid, data in member_data.items():
            data['total_score'] = data['contribution_score']

        return member_data

    @staticmethod
    @transaction.atomic
    def generate_ranking_draft(project, period=None, user=None):
        """
        根据贡献记录、任务完成情况、IP贡献生成排序草稿
        :param project: 项目实例
        :param period: 统计周期（默认当前年月，格式 YYYY-MM）
        :param user: 操作人
        :return: (success: bool, data_or_message) data 为生成的排名列表
        """
        if period is None:
            period = timezone.now().strftime('%Y-%m')

        member_data = RankingService._get_member_scores(project, period)

        # 4. 按业务优先级做严格的字典序排序；总分仅用于展示，不得越过类别优先级。
        sorted_members = sorted(
            member_data.values(),
            key=lambda x: (
                x['actual_project_score'],
                x['resource_score'],
                x['management_score'],
                x['team_history_score'],
                -x['user'].date_joined.timestamp(),
                -x['user'].id,
            ),
            reverse=True,
        )

        # 5. 创建/更新 MemberRanking 记录（draft 状态）
        # 删除该项目该周期已有的草案（保留已确认的，确认后不可改）
        MemberRanking.objects.filter(
            project=project, period=period, status=MemberRanking.Status.DRAFT
        ).delete()

        # 已确认的排名不覆盖（确认后不可改）
        confirmed_user_ids = set(
            MemberRanking.objects.filter(
                project=project, period=period, status=MemberRanking.Status.CONFIRMED
            ).values_list('user_id', flat=True)
        )

        created = []
        for index, data in enumerate(sorted_members, start=1):
            # 跳过已确认排名的成员，避免覆盖
            if data['user'].id in confirmed_user_ids:
                continue
            ranking = MemberRanking.objects.update_or_create(
                project=project,
                user=data['user'],
                period=period,
                defaults={
                    'status': MemberRanking.Status.DRAFT,
                    'total_score': data['total_score'],
                    'rank': index,
                    'task_completed_count': data['task_count'],
                    'project_count': 1,
                    'competition_count': data['competition_count'],
                    'ip_contribution_count': data['ip_count'],
                    'is_public': False,
                    'rule_version': RANKING_RULE_VERSION,
                    'rule_snapshot': RANKING_RULE,
                    'score_snapshot': {
                        'period': period,
                        'user_id': data['user'].id,
                        'total_score': str(data['total_score']),
                        'breakdown': {
                            'actual_project': str(data['actual_project_score']),
                            'resource': str(data['resource_score']),
                            'management': str(data['management_score']),
                            'team_history': str(data['team_history_score']),
                        },
                        'evidence_count': len(data['evidence']),
                        'evidence': data['evidence'],
                    },
                    'generated_at': timezone.now(),
                    'confirmed_at': None,
                    'confirmed_by': None,
                },
            )[0]
            created.append(ranking)

        # 写操作日志
        if user is not None:
            log_operation(
                user=user,
                action='生成排名草案',
                obj=project,
                detail=f'{project.name} 周期{period} 共{len(created)}名成员',
            )

        return True, created

    @staticmethod
    @transaction.atomic
    def confirm_ranking(ranking_ids, teacher):
        """
        老师确认排序
        - 更新状态为 confirmed, is_public=True（确认后不可改）
        :param ranking_ids: 排名记录ID列表
        :param teacher: 操作人（老师）
        :return: (success: bool, data_or_message) data 为确认的记录数量
        """
        rankings = MemberRanking.objects.filter(
            id__in=ranking_ids,
            status=MemberRanking.Status.DRAFT,
        )
        confirmed_count = 0
        for ranking in rankings:
            ranking.status = MemberRanking.Status.CONFIRMED
            ranking.is_public = True
            ranking.is_published = True
            ranking.confirmed_at = timezone.now()
            ranking.confirmed_by = teacher
            ranking.save(
                update_fields=[
                    'status', 'is_public', 'is_published',
                    'confirmed_at', 'confirmed_by', 'updated_at',
                ]
            )
            confirmed_count += 1

        # 写操作日志
        log_operation(
            user=teacher,
            action='确认排名',
            obj=None,
            detail=f'老师确认{confirmed_count}条排名记录',
        )

        return True, confirmed_count

    @staticmethod
    @transaction.atomic
    def update_rank(ranking, rank, total_score=None, user=None):
        """
        修改排序（项目负责人）
        - 仅草案状态可修改
        :param ranking: MemberRanking 实例
        :param rank: 新排名
        :param total_score: 新总分（可选）
        :param user: 操作人
        :return: (success: bool, data_or_message)
        """
        if ranking.status != MemberRanking.Status.DRAFT:
            return False, '已确认的排名不可修改'

        ranking.rank = rank
        if total_score is not None:
            ranking.total_score = total_score
        snapshot = dict(ranking.score_snapshot or {})
        overrides = list(snapshot.get('manual_overrides') or [])
        overrides.append({
            'operator_id': getattr(user, 'id', None),
            'at': timezone.now().isoformat(),
            'rank': rank,
            'total_score': str(total_score) if total_score is not None else None,
        })
        snapshot['manual_overrides'] = overrides
        ranking.score_snapshot = snapshot
        ranking.save()

        if user is not None:
            log_operation(
                user=user,
                action='修改排名',
                obj=ranking,
                detail=f'{ranking.user.name} 排名修改为第{rank}名',
            )

        return True, ranking

    @staticmethod
    @transaction.atomic
    def resolve_objection(
        objection,
        teacher,
        final_status,
        teacher_opinion='',
        final_result='',
        corrected_rank=None,
        corrected_total_score=None,
    ):
        """终审排名异议；异议成立时在同项目同周期内真实重排并固化审计证据。"""
        try:
            objection = (
                RankingObjection.objects.select_for_update()
                # project 字段允许为空，PostgreSQL 不允许 FOR UPDATE 锁定
                # LEFT OUTER JOIN 的可空侧；这里只需要 project_id，无需联表。
                .select_related('ranking', 'ranking__user')
                .get(pk=objection.pk)
            )
        except RankingObjection.DoesNotExist:
            return False, '异议不存在'

        if objection.status != RankingObjection.Status.LEADER_REVIEWED:
            return False, '该异议需先经负责人初审'
        if final_status not in {
            RankingObjection.Status.APPROVED,
            RankingObjection.Status.REJECTED,
        }:
            return False, '无效的异议终审结果'

        now = timezone.now()
        ranking = objection.ranking
        objection.teacher_opinion = teacher_opinion
        objection.teacher_confirmer = teacher
        objection.teacher_confirmed_at = now
        objection.handler = teacher

        if final_status == RankingObjection.Status.APPROVED:
            if corrected_rank is None and corrected_total_score is None:
                return False, '异议成立时必须填写更正名次或更正总分'
            if (
                ranking.status != MemberRanking.Status.CONFIRMED
                or not ranking.is_public
            ):
                return False, '仅已确认并公开的排名可执行异议更正'

            period_rankings = list(
                MemberRanking.objects.select_for_update()
                .filter(
                    project_id=ranking.project_id,
                    period=ranking.period,
                    status=MemberRanking.Status.CONFIRMED,
                    is_public=True,
                )
                .select_related('user')
                .order_by('rank', 'id')
            )
            current = next(
                (item for item in period_rankings if item.id == ranking.id),
                None,
            )
            if current is None:
                return False, '待更正排名不在当前公开榜单中'

            original_rank = current.rank
            original_total_score = current.total_score
            requested_rank = (
                int(corrected_rank)
                if corrected_rank is not None
                else period_rankings.index(current) + 1
            )
            if requested_rank < 1 or requested_rank > len(period_rankings):
                return False, f'更正名次必须在 1 至 {len(period_rankings)} 之间'
            current_position = period_rankings.index(current) + 1
            if (
                requested_rank == current_position
                and (
                    corrected_total_score is None
                    or corrected_total_score == original_total_score
                )
            ):
                return False, '异议成立后的名次或总分必须发生实际变化'

            previous_ranks = {item.id: item.rank for item in period_rankings}
            reordered = [item for item in period_rankings if item.id != current.id]
            reordered.insert(requested_rank - 1, current)
            if corrected_total_score is not None:
                current.total_score = corrected_total_score

            rank_changes = []
            for new_rank, item in enumerate(reordered, start=1):
                old_rank = previous_ranks[item.id]
                item.rank = new_rank
                item.updated_at = now
                if old_rank != new_rank:
                    rank_changes.append({
                        'ranking_id': item.id,
                        'user_id': item.user_id,
                        'from_rank': old_rank,
                        'to_rank': new_rank,
                    })

            target_snapshot = dict(current.score_snapshot or {})
            objection_adjustments = list(
                target_snapshot.get('objection_adjustments') or []
            )
            objection_adjustments.append({
                'objection_id': objection.id,
                'operator_id': teacher.id,
                'at': now.isoformat(),
                'from_rank': original_rank,
                'to_rank': current.rank,
                'from_total_score': str(original_total_score),
                'to_total_score': str(current.total_score),
            })
            target_snapshot['objection_adjustments'] = objection_adjustments
            current.score_snapshot = target_snapshot
            MemberRanking.objects.bulk_update(
                reordered,
                ['rank', 'total_score', 'score_snapshot', 'updated_at'],
            )

            objection.original_rank = original_rank
            objection.corrected_rank = current.rank
            objection.original_total_score = original_total_score
            objection.corrected_total_score = current.total_score
            objection.adjustment_snapshot = {
                'rule_version': current.rule_version,
                'project_id': current.project_id,
                'period': current.period,
                'rank_changes': rank_changes,
                'score_change': {
                    'from': str(original_total_score),
                    'to': str(current.total_score),
                },
            }
            objection.adjustment_applied_at = now
            objection.adjustment_applied_by = teacher
            objection.status = RankingObjection.Status.APPROVED
            objection.final_result = final_result or (
                f'异议成立，排名由第 {original_rank} 名更正为第 {current.rank} 名，'
                f'总分由 {original_total_score} 更正为 {current.total_score}。'
            )
            # 避免返回对象中的 select_related 缓存仍保留更正前名次。
            objection.ranking = current
        else:
            objection.status = RankingObjection.Status.REJECTED
            objection.final_result = final_result or '异议不成立，维持原排名。'

        objection.save()
        log_operation(
            user=teacher,
            action='排名异议终审',
            obj=objection,
            detail=(
                f'{objection.ranking.user.name} '
                f'{objection.get_status_display()}：{objection.final_result}'
            ),
        )
        return True, objection
