"""
贡献度视图
- ContributionViewSet: 贡献记录 CRUD + 审核 + 我的贡献 + 待审核 + 按项目查询
- MemberRankingViewSet: 成员排名 列表 + 生成草案 + 修改排序 + 老师确认 + 按项目查询
- RankingObjectionViewSet: 排名异议 列表 + 创建 + 负责人初审 + 老师最终确认
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsTeacherOrAdmin
from common.project_access import (
    active_user_root_team_ids,
    has_active_project_leadership,
    project_can_manage,
    project_root_team_ids,
    scope_project_queryset,
)
from apps.projects.models import Project, ProjectMember
from apps.users.models import User

from .models import (
    Contribution,
    ProjectContributionReviewer,
    MemberRanking,
    RankingObjection,
)
from .serializers import (
    ContributionSerializer,
    ContributionListSerializer,
    ContributionCreateSerializer,
    ContributionReviewSerializer,
    ProjectContributionReviewerSerializer,
    MemberRankingSerializer,
    MemberRankingUpdateSerializer,
    RankingObjectionSerializer,
    RankingObjectionCreateSerializer,
    RankingObjectionReviewSerializer,
)
from .permissions import (
    IsProjectMemberForContribution,
    IsProjectLeaderOrTeacherOrAdminForContribution,
    _is_project_member,
    _is_project_leader_or_admin,
)
from .services import RankingService


def _select_contribution_reviewer(project, contribution_user, filled_by):
    """Route one reviewer and require an independent reviewer for manager self-report."""
    excluded_ids = {
        user_id for user_id in (
            getattr(contribution_user, 'id', None),
            getattr(filled_by, 'id', None),
        ) if user_id
    }
    requires_independent = project_can_manage(contribution_user, project)
    configured = ProjectContributionReviewer.objects.filter(
        project=project,
        is_active=True,
    ).exclude(user_id__in=excluded_ids)
    if requires_independent:
        configured = configured.filter(is_independent=True)
    reviewer_config = configured.select_related('user').order_by(
        'priority', 'id',
    ).first()
    if reviewer_config:
        return reviewer_config.user
    if requires_independent:
        return None

    co_leader = ProjectMember.objects.filter(
        project=project,
        role_in_project=ProjectMember.RoleInProject.LEADER,
        status=ProjectMember.Status.ACTIVE,
    ).exclude(user_id__in=excluded_ids).select_related('user').first()
    if co_leader:
        return co_leader.user
    if project.leader_id not in excluded_ids:
        return project.leader
    return None


def _is_actual_project_participant(user, project):
    """贡献本人必须确实属于项目，不能借全局角色绕过成员关系。"""
    if not user or not project:
        return False
    if project.leader_id == user.id:
        return True
    return ProjectMember.objects.filter(
        project=project,
        user=user,
        status=ProjectMember.Status.ACTIVE,
    ).exists()


def _organization_teachers_for_project(project):
    """只向项目所在根团队内的老师发送异议通知。"""
    teachers = User.objects.filter(
        global_role=User.GlobalRole.TEACHER,
        is_active=True,
        membership_status__in=[
            User.MembershipStatus.ACTIVE,
            User.MembershipStatus.ON_LEAVE,
        ],
    )
    from apps.common.team_models import Team, TeamMember

    active_root_ids = set(
        Team.objects.filter(
            parent__isnull=True,
            is_active=True,
        ).values_list('id', flat=True)
    )
    if not active_root_ids:
        # 完全没有 Team 的旧部署保持原有全局老师通知行为。
        return teachers

    root_ids = project_root_team_ids(project)
    if not root_ids and project and project.leader_id:
        root_ids = active_user_root_team_ids(project.leader)
    if not root_ids:
        return teachers.none()

    visible_statuses = [
        TeamMember.Status.ACTIVE,
        TeamMember.Status.ON_LEAVE,
    ]
    return teachers.filter(
        Q(
            teammember__team_id__in=root_ids,
            teammember__status__in=visible_statuses,
        )
        | Q(
            teammember__team__parent_id__in=root_ids,
            teammember__status__in=visible_statuses,
        )
        | Q(owned_teams__id__in=root_ids)
        | Q(owned_teams__parent_id__in=root_ids)
    ).distinct()


def _notify_ranking_objection(objection, stage, sender):
    """发送排名异议提交、初审和终审通知。"""
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService
    project = objection.ranking.project
    recipients = []
    if stage == 'created':
        if project and project.leader:
            recipients.append(project.leader)
        recipients.extend(_organization_teachers_for_project(project))
        title = f'排名异议待初审：{project.name if project else "团队排名"}'
        content = (
            f'{objection.objector.name} 对 {objection.ranking.period} '
            f'第 {objection.ranking.rank} 名提出异议：{objection.content}'
        )
    elif stage == 'leader_reviewed':
        recipients.append(objection.objector)
        recipients.extend(_organization_teachers_for_project(project))
        title = f'排名异议已初审：{project.name if project else "团队排名"}'
        content = f'负责人初审意见：{objection.leader_opinion}，请老师进行最终确认。'
    else:
        recipients.append(objection.objector)
        if project and project.leader:
            recipients.append(project.leader)
        title = f'排名异议已终审：{project.name if project else "团队排名"}'
        content = (
            f'最终结果：{objection.get_status_display()}。'
            f'{objection.final_result or objection.teacher_opinion}'
        )

    unique_recipients = {
        user.id: user
        for user in recipients
        if user and user.is_active and user.id != getattr(sender, 'id', None)
    }
    NotificationService.bulk_create_and_send_email(
        recipients=list(unique_recipients.values()),
        title=title,
        content=content,
        category=Notification.NotificationType.CONTRIBUTION,
        ref_type='ranking_objection',
        ref_id=objection.id,
        sender=sender,
        priority=Notification.Priority.HIGH,
    )


# ============ 贡献记录 ============

class ContributionViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    贡献记录管理 ViewSet
    - list: 支持按 project/status/user/contribution_type 筛选
    - create: 项目成员可创建（校验是否为该项目成员）
    - update/partial_update: 填写人或项目负责人
    - destroy: 填写人或项目负责人
    - review: PATCH 项目负责人审核
    - my_contributions: GET 我的贡献记录
    - pending_review: GET 待我审核的贡献
    - by_project: GET 指定项目的贡献记录
    """
    queryset = Contribution.objects.all().order_by('-created_at')
    # 默认序列化器（兜底，避免未配置 action 调用 get_serializer 时报错）
    serializer_class = ContributionSerializer

    serializer_classes_by_action = {
        'list': ContributionListSerializer,
        'retrieve': ContributionSerializer,
        'create': ContributionCreateSerializer,
        'update': ContributionSerializer,
        'partial_update': ContributionSerializer,
        'review': ContributionReviewSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'update': [IsProjectMemberForContribution],
        'partial_update': [IsProjectMemberForContribution],
        'destroy': [IsProjectMemberForContribution],
        'review': [IsAuthenticated],
        'my_contributions': [IsAuthenticated],
        'pending_review': [IsAuthenticated],
        'by_project': [IsAuthenticated],
    }

    def get_queryset(self):
        """支持按 project/status/user/contribution_type 筛选"""
        queryset = super().get_queryset().select_related(
            'project', 'user', 'filled_by', 'reviewer',
        )
        params = self.request.query_params
        project_id = params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        user_id = params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        contrib_status = params.get('status')
        if contrib_status:
            queryset = queryset.filter(status=contrib_status)
        contribution_type = params.get('contribution_type')
        if contribution_type:
            queryset = queryset.filter(contribution_type=contribution_type)
        period = params.get('period')
        if period:
            queryset = queryset.filter(period=period)
        if getattr(self.request.user, 'membership_status', '') == User.MembershipStatus.EXTERNAL:
            project_ids = ProjectMember.objects.filter(
                user=self.request.user,
                status=ProjectMember.Status.ACTIVE,
            ).values_list('project_id', flat=True)
            queryset = queryset.filter(project_id__in=project_ids)
        scoped_queryset = scope_project_queryset(
            queryset,
            self.request.user,
            project_lookup='project',
        )
        # 审核分派本身构成对单条贡献的显式授权，允许跨小组审核人
        # 在不获得项目其他数据可见性的前提下读取并处理该记录。
        scoped_ids = scoped_queryset.order_by().values('pk')
        can_use_assignment = (
            self.request.user.is_active
            and self.request.user.membership_status in (
                User.MembershipStatus.ACTIVE,
                User.MembershipStatus.ON_LEAVE,
            )
        )
        if not can_use_assignment:
            return scoped_queryset
        return queryset.filter(
            Q(pk__in=scoped_ids) | Q(reviewer=self.request.user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        """创建贡献记录（校验是否为项目成员）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 校验是否为该项目成员
        project = serializer.validated_data.get('project')
        if project is not None and not _is_project_member(request.user, project):
            return error_response(
                message='仅项目成员可创建该项目贡献记录', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        contribution_user = serializer.validated_data.get('user') or request.user
        if contribution_user.id != request.user.id and not (
            project and project_can_manage(request.user, project)
        ):
            return error_response(
                message='只有项目负责人可以代其他成员登记贡献',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if project is not None and not _is_actual_project_participant(
            contribution_user,
            project,
        ):
            return error_response(
                message='贡献本人必须是该项目的活动成员',
                code=1005,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        reviewer = _select_contribution_reviewer(
            project,
            contribution_user,
            request.user,
        ) if project else None
        if project and reviewer is None:
            return error_response(
                message=(
                    '未找到可分派的贡献审核人。负责人本人申报时，'
                    '请先配置一名独立审核人。'
                ),
                code=2501,
            )

        contribution = serializer.save()
        if reviewer:
            contribution.reviewer = reviewer
            contribution.save(update_fields=['reviewer', 'updated_at'])
        return success_response(
            ContributionSerializer(contribution).data,
            message=f'贡献记录创建成功，已分派给{reviewer.name if reviewer else "审核人"}',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新贡献记录"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        if instance.status != Contribution.Status.PENDING:
            return error_response(message='已审核的贡献记录不能再修改')
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        contribution = serializer.save()
        return success_response(
            ContributionSerializer(contribution).data,
            message='贡献记录更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除贡献记录"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        if instance.status != Contribution.Status.PENDING:
            return error_response(message='已审核的贡献记录不能删除')
        instance.delete()
        return success_response(message='贡献记录删除成功')

    @action(detail=True, methods=['patch'])
    def review(self, request, pk=None):
        """
        项目负责人审核贡献
        PATCH /api/v1/contributions/contributions/{id}/review/
        body: {"status": "approved/rejected", "review_opinion": "审核意见", "weight": 10}
        """
        contribution = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        user = request.user

        if contribution.user_id == user.id or contribution.filled_by_id == user.id:
            return error_response(
                message='贡献本人或填写人不能审核自己的记录',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        can_review = (
            user.global_role == 'sys_admin'
            or contribution.reviewer_id == user.id
            or (
                contribution.reviewer_id is None
                and contribution.project is not None
                and (
                    contribution.project.leader_id == user.id
                    or has_active_project_leadership(user, contribution.project)
                )
            )
        )
        if not can_review:
            return error_response(
                message='该贡献已分派给其他审核人', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        # 校验当前状态必须为待审核
        if contribution.status != Contribution.Status.PENDING:
            return error_response(message='该贡献记录已审核，不可重复审核')

        new_status = validated_data.get('status')
        contribution.status = new_status
        contribution.review_opinion = validated_data.get('review_opinion', '')
        contribution.weight = validated_data.get('weight', contribution.weight)
        contribution.reviewer = user
        contribution.reviewed_at = timezone.now()
        contribution.save()

        return success_response(
            ContributionSerializer(contribution).data,
            message='贡献记录审核完成',
        )

    @action(detail=False, methods=['get'])
    def my_contributions(self, request):
        """
        我的贡献记录
        GET /api/v1/contributions/contributions/my_contributions/
        """
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ContributionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ContributionListSerializer(queryset, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """
        待我审核的贡献（我负责的项目中的待审核贡献）
        GET /api/v1/contributions/contributions/pending_review/
        """
        user = request.user
        if user.global_role == 'sys_admin':
            queryset = self.get_queryset().filter(status=Contribution.Status.PENDING)
        else:
            queryset = self.get_queryset().filter(
                status=Contribution.Status.PENDING,
            ).filter(
                Q(reviewer=user)
                | Q(
                    reviewer__isnull=True,
                    project__leader=user,
                )
                | Q(
                    reviewer__isnull=True,
                    project__members__user=user,
                    project__members__role_in_project=ProjectMember.RoleInProject.LEADER,
                    project__members__status=ProjectMember.Status.ACTIVE,
                )
            ).exclude(
                user=user,
            ).exclude(
                filled_by=user,
            ).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ContributionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ContributionListSerializer(queryset, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """获取指定项目的贡献记录。"""
        project_id = request.query_params.get('project')
        if not project_id:
            return error_response(message='请提供 project 参数')
        queryset = self.get_queryset().filter(project_id=project_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ContributionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ContributionListSerializer(queryset, many=True)
        return success_response(serializer.data)


class ProjectContributionReviewerViewSet(ModelViewSet):
    """配置项目审核池；老师只有被明确配置后才收到贡献待办。"""

    queryset = ProjectContributionReviewer.objects.all()
    serializer_class = ProjectContributionReviewerSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['project', 'user', 'is_independent', 'is_active']
    ordering_fields = ['priority', 'created_at']

    def get_queryset(self):
        return scope_project_queryset(
            super().get_queryset().select_related('project', 'user'),
            self.request.user,
            project_lookup='project',
        )

    def _can_manage(self, project):
        return project_can_manage(self.request.user, project)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data['project']
        if not self._can_manage(project):
            return error_response(
                message='仅项目负责人可配置贡献审核人',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        reviewer = serializer.save()
        return success_response(
            self.get_serializer(reviewer).data,
            message='贡献审核人已配置',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage(instance.project):
            return error_response(
                message='仅项目负责人可调整贡献审核人',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        target_project = request.data.get('project')
        if (
            target_project not in (None, '')
            and str(target_project) != str(instance.project_id)
        ):
            return error_response(
                message='审核人配置不能迁移到其他项目',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage(instance.project):
            return error_response(
                message='仅项目负责人可移除贡献审核人',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

# ============ 成员排名 ============

class MemberRankingViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    成员排名管理 ViewSet
    - list: 按项目查询排序（已确认的公开可见，草案仅负责人/老师/管理员可见）
    - generate: POST 项目负责人生成排序草案
    - update_rank: PATCH 修改排序（项目负责人）
    - confirm: POST 老师确认排序（确认后不可改，is_public=True）
    - by_project: GET 指定项目的排序
    """
    queryset = MemberRanking.objects.all().order_by('period', 'rank')
    # 默认序列化器（兜底）
    serializer_class = MemberRankingSerializer

    serializer_classes_by_action = {
        'list': MemberRankingSerializer,
        'retrieve': MemberRankingSerializer,
        'update_rank': MemberRankingUpdateSerializer,
        'generate': MemberRankingSerializer,
        'confirm': MemberRankingSerializer,
        'by_project': MemberRankingSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'generate': [IsAuthenticated],
        'update_rank': [IsAuthenticated],
        'confirm': [IsTeacherOrAdmin],
        'by_project': [IsAuthenticated],
    }

    def get_queryset(self):
        """按项目筛选；普通成员仅可见已公开的排名"""
        queryset = super().get_queryset().select_related('project', 'user')
        queryset = scope_project_queryset(
            queryset,
            self.request.user,
            project_lookup='project',
            include_unscoped=True,
        )
        params = self.request.query_params
        project_id = params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        period = params.get('period')
        if period:
            queryset = queryset.filter(period=period)

        user = self.request.user
        if getattr(user, 'membership_status', '') == User.MembershipStatus.EXTERNAL:
            project_ids = ProjectMember.objects.filter(
                user=user,
                status=ProjectMember.Status.ACTIVE,
            ).values_list('project_id', flat=True)
            queryset = queryset.filter(project_id__in=project_ids)
        # 普通成员仅可见已公开（已确认）的排名
        if user.global_role not in ['sys_admin', 'teacher']:
            # 项目负责人可见自己项目的草案，其他成员仅可见 is_public=True
            my_project_ids = Project.objects.filter(leader=user).values_list('id', flat=True)
            queryset = queryset.filter(
                Q(is_public=True) | Q(project_id__in=list(my_project_ids))
            )
        return queryset

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        生成排序草案
        POST /api/v1/contributions/rankings/generate/
        body: {"project": 1, "period": "2026-06"}
        """
        project_id = request.data.get('project')
        period = request.data.get('period')
        if not project_id:
            return error_response(message='请提供 project 参数')

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return error_response(message='项目不存在', code=1004, http_status=status.HTTP_404_NOT_FOUND)

        # 权限校验：项目负责人/老师/管理员
        if not _is_project_leader_or_admin(request.user, project):
            return error_response(
                message='仅项目负责人/老师/管理员可生成排序', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        success, result = RankingService.generate_ranking_draft(
            project=project, period=period, user=request.user,
        )
        if not success:
            return error_response(message=result)

        serializer = MemberRankingSerializer(result, many=True)
        return success_response(serializer.data, message='排序草案生成成功')

    @action(detail=True, methods=['patch'])
    def update_rank(self, request, pk=None):
        """
        修改排序（项目负责人）
        PATCH /api/v1/contributions/rankings/{id}/update_rank/
        body: {"rank": 1, "total_score": 100}
        """
        ranking = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 权限校验：项目负责人/老师/管理员
        if not _is_project_leader_or_admin(request.user, ranking.project):
            return error_response(
                message='仅项目负责人/老师/管理员可修改排序', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        success, result = RankingService.update_rank(
            ranking=ranking,
            rank=serializer.validated_data.get('rank', ranking.rank),
            total_score=serializer.validated_data.get('total_score'),
            user=request.user,
        )
        if not success:
            return error_response(message=result)

        return success_response(
            MemberRankingSerializer(result).data,
            message='排序修改成功',
        )

    @action(detail=False, methods=['post'])
    def confirm(self, request):
        """
        老师确认排序（确认后不可改，is_public=True）
        POST /api/v1/contributions/rankings/confirm/
        body: {"ids": [1, 2, 3]} 或 {"project": 1, "period": "2026-06"}
        """
        ids = request.data.get('ids')
        project_id = request.data.get('project')
        period = request.data.get('period')

        if not ids:
            if not project_id:
                return error_response(message='请提供 ids 或 project 参数')
            # 按 project + period 确认所有草案
            ranking_qs = MemberRanking.objects.filter(
                project_id=project_id,
                status=MemberRanking.Status.DRAFT,
            )
            if period:
                ranking_qs = ranking_qs.filter(period=period)
            ids = list(ranking_qs.values_list('id', flat=True))

        success, result = RankingService.confirm_ranking(ids, request.user)
        if not success:
            return error_response(message=result)

        return success_response(
            {'confirmed_count': result},
            message=f'成功确认{result}条排名',
        )

    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """
        指定项目的排序（已确认的公开可见）
        GET /api/v1/contributions/rankings/by_project/?project=1&period=2026-06
        """
        project_id = request.query_params.get('project')
        if not project_id:
            return error_response(message='请提供 project 参数')
        queryset = self.get_queryset().filter(project_id=project_id)
        # 普通成员仅可见已公开的
        if request.user.global_role not in ['sys_admin', 'teacher']:
            my_project_ids = Project.objects.filter(leader=request.user).values_list('id', flat=True)
            if int(project_id) not in list(my_project_ids):
                queryset = queryset.filter(is_public=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MemberRankingSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MemberRankingSerializer(queryset, many=True)
        return success_response(serializer.data)


# ============ 排名异议 ============

class RankingObjectionViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    排名异议管理 ViewSet
    - list: 按项目查询异议（项目成员可见）
    - create: 项目成员提交异议
    - leader_review: PATCH 项目负责人初审
    - teacher_confirm: PATCH 老师最终确认
    """
    queryset = RankingObjection.objects.all().order_by('-created_at')
    # 默认序列化器（兜底）
    serializer_class = RankingObjectionSerializer

    serializer_classes_by_action = {
        'list': RankingObjectionSerializer,
        'retrieve': RankingObjectionSerializer,
        'create': RankingObjectionCreateSerializer,
        'leader_review': RankingObjectionReviewSerializer,
        'teacher_confirm': RankingObjectionReviewSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'leader_review': [IsAuthenticated],
        'teacher_confirm': [IsTeacherOrAdmin],
    }

    def get_queryset(self):
        """按项目筛选异议；普通成员仅可见自己所在项目的异议"""
        queryset = super().get_queryset().select_related(
            'ranking', 'ranking__project', 'objector',
            'leader_reviewer', 'teacher_confirmer',
        )
        params = self.request.query_params
        project_id = params.get('project')
        if project_id:
            queryset = queryset.filter(ranking__project_id=project_id)
        status = params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        user = self.request.user
        # 老师/管理员可见所有
        if user.global_role not in ['sys_admin', 'teacher']:
            # 普通成员可见自己所在项目的异议
            my_project_ids = list(
                Project.objects.filter(leader=user).values_list('id', flat=True)
            )
            my_project_ids += list(
                ProjectMember.objects.filter(
                    user=user, status=ProjectMember.Status.ACTIVE
                ).values_list('project_id', flat=True)
            )
            queryset = queryset.filter(ranking__project_id__in=my_project_ids)
        return queryset

    def create(self, request, *args, **kwargs):
        """创建异议（校验是否为项目成员）"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ranking = serializer.validated_data.get('ranking')
        project = getattr(ranking, 'project', None)
        # 校验是否为项目成员
        if project is not None and not _is_project_member(request.user, project):
            return error_response(
                message='仅项目成员可对该项目排名提出异议', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        # 校验排名已公开（已确认）才能提异议
        if not ranking.is_public:
            return error_response(message='该排名尚未公开确认，无法提出异议')

        objection = serializer.save()
        _notify_ranking_objection(objection, 'created', request.user)
        return success_response(
            RankingObjectionSerializer(objection).data,
            message='异议提交成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['patch'])
    def leader_review(self, request, pk=None):
        """
        项目负责人初审
        PATCH /api/v1/contributions/objections/{id}/leader_review/
        body: {"leader_opinion": "负责人意见"}
        """
        objection = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # 校验 action 必须为 leader_review
        if validated_data.get('action') != 'leader_review':
            return error_response(message='该接口仅支持负责人初审操作')

        project = getattr(objection.ranking, 'project', None)
        if not _is_project_leader_or_admin(request.user, project):
            return error_response(
                message='仅项目负责人/老师/管理员可进行初审', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        # 校验当前状态必须为待处理
        if objection.status != RankingObjection.Status.PENDING:
            return error_response(message='该异议已初审，无法重复初审')

        objection.leader_opinion = validated_data.get('leader_opinion', '')
        objection.leader_reviewer = request.user
        objection.leader_reviewed_at = timezone.now()
        objection.status = RankingObjection.Status.LEADER_REVIEWED
        objection.handler = request.user
        objection.save()
        _notify_ranking_objection(objection, 'leader_reviewed', request.user)

        return success_response(
            RankingObjectionSerializer(objection).data,
            message='异议初审完成',
        )

    @action(detail=True, methods=['patch'])
    def teacher_confirm(self, request, pk=None):
        """
        老师最终确认
        PATCH /api/v1/contributions/objections/{id}/teacher_confirm/
        body: {
            "teacher_opinion": "老师意见",
            "final_result": "最终结果",
            "final_status": "approved/rejected"
        }
        """
        objection = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # 校验 action 必须为 teacher_confirm
        if validated_data.get('action') != 'teacher_confirm':
            return error_response(message='该接口仅支持老师最终确认操作')

        # 校验当前状态必须为负责人已初审
        if objection.status != RankingObjection.Status.LEADER_REVIEWED:
            return error_response(message='该异议需先经负责人初审')

        final_status = validated_data.get('final_status')
        success, result = RankingService.resolve_objection(
            objection=objection,
            teacher=request.user,
            final_status=final_status,
            teacher_opinion=validated_data.get('teacher_opinion', ''),
            final_result=validated_data.get('final_result', ''),
            corrected_rank=validated_data.get('corrected_rank'),
            corrected_total_score=validated_data.get('corrected_total_score'),
        )
        if not success:
            return error_response(message=result)
        objection = result
        _notify_ranking_objection(objection, 'teacher_confirmed', request.user)

        return success_response(
            RankingObjectionSerializer(objection).data,
            message='异议最终确认完成',
        )
