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
from apps.projects.models import Project

from .models import Contribution, MemberRanking, RankingObjection
from .serializers import (
    ContributionSerializer,
    ContributionListSerializer,
    ContributionCreateSerializer,
    ContributionReviewSerializer,
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
        return queryset

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

        contribution = serializer.save()
        return success_response(
            ContributionSerializer(contribution).data,
            message='贡献记录创建成功，等待项目负责人审核',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新贡献记录"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
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

        # 权限校验：项目负责人/老师/管理员
        if not _is_project_leader_or_admin(user, contribution.project):
            return error_response(
                message='仅项目负责人/老师/管理员可审核贡献', code=1003,
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
        # 老师/管理员：所有待审核贡献
        if user.global_role in ['sys_admin', 'teacher']:
            queryset = self.get_queryset().filter(status=Contribution.Status.PENDING)
        else:
            # 项目负责人：我负责的项目中的待审核贡献
            my_project_ids = Project.objects.filter(leader=user).values_list('id', flat=True)
            queryset = self.get_queryset().filter(
                status=Contribution.Status.PENDING,
                project_id__in=list(my_project_ids),
            )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ContributionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ContributionListSerializer(queryset, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """
        指定项目的贡献记录
        GET /api/v1/contributions/contributions/by_project/?project=1
        """
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
        params = self.request.query_params
        project_id = params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        period = params.get('period')
        if period:
            queryset = queryset.filter(period=period)

        user = self.request.user
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
            from apps.projects.models import ProjectMember
            my_project_ids += list(
                ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
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
        objection.teacher_opinion = validated_data.get('teacher_opinion', '')
        objection.teacher_confirmer = request.user
        objection.teacher_confirmed_at = timezone.now()
        objection.final_result = validated_data.get('final_result', '')
        # 根据最终状态设置异议状态
        if final_status == 'approved':
            objection.status = RankingObjection.Status.APPROVED
        else:
            objection.status = RankingObjection.Status.REJECTED
        objection.handler = request.user
        objection.save()

        return success_response(
            RankingObjectionSerializer(objection).data,
            message='异议最终确认完成',
        )
