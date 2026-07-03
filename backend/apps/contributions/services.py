"""
贡献度业务逻辑服务
包含：排名草案生成、排名确认、操作日志记录
排名计算维度：贡献记录（权重求和）+ 任务完成数 + IP贡献数 + 比赛参与数
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import Contribution, MemberRanking, RankingObjection
from apps.projects.models import ProjectMember, Project
from apps.tasks.models import Task
from apps.audit.models import OperationLog


# ============ 排序计算权重配置 ============
# 各维度单分分值（可按需调整）
TASK_POINT = Decimal('10')          # 每个已完成任务得分
IP_POINT = Decimal('20')            # 每条 IP 贡献得分
COMPETITION_POINT = Decimal('15')   # 每次比赛参与得分
# 贡献记录直接使用其 weight 字段求和作为得分

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

        # 2. 获取该项目已审核通过的贡献记录
        approved_contributions = Contribution.objects.filter(
            project=project,
            status=Contribution.Status.APPROVED,
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
                }
            # 贡献得分：优先使用 weight，为 0 时回退 score
            point = contrib.weight if contrib.weight else contrib.score
            member_data[uid]['contribution_score'] += point
            # IP 贡献计数
            if contrib.contribution_type in IP_CONTRIBUTION_TYPES:
                member_data[uid]['ip_count'] += 1
            # 比赛参与计数
            if contrib.contribution_type == Contribution.ContributionType.COMPETITION:
                member_data[uid]['competition_count'] += 1

        # 3. 获取每个成员的任务完成情况（已完成任务数）
        done_tasks = Task.objects.filter(
            project=project,
            status=Task.Status.DONE,
        )
        for task in done_tasks:
            uid = task.assignee_id
            if uid in member_data:
                member_data[uid]['task_count'] += 1
            # 协作者也计入任务完成数
            for collaborator in task.collaborators.all():
                cid = collaborator.id
                if cid in member_data:
                    member_data[cid]['task_count'] += 1

        # 4. 计算综合得分
        for uid, data in member_data.items():
            total = (
                data['contribution_score']
                + data['task_count'] * TASK_POINT
                + data['ip_count'] * IP_POINT
                + data['competition_count'] * COMPETITION_POINT
            )
            data['total_score'] = total

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

        # 5. 按总分降序生成排名
        sorted_members = sorted(
            member_data.values(),
            key=lambda x: x['total_score'],
            reverse=True,
        )

        # 6. 创建/更新 MemberRanking 记录（draft 状态）
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
            ranking.save()
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
        ranking.save()

        if user is not None:
            log_operation(
                user=user,
                action='修改排名',
                obj=ranking,
                detail=f'{ranking.user.name} 排名修改为第{rank}名',
            )

        return True, ranking
