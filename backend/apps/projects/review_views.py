"""
项目复盘视图
- ProjectReviewViewSet: 项目复盘 CRUD + 提交 + 审阅
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from common.response import success_response, error_response
from .review_models import ProjectReview
from .review_serializers import ProjectReviewSerializer


class ProjectReviewViewSet(viewsets.ModelViewSet):
    """项目复盘 ViewSet"""
    serializer_class = ProjectReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProjectReview.objects.select_related('project', 'reviewer').all()

    def perform_create(self, serializer):
        """创建复盘：仅老师/管理员可创建"""
        user = self.request.user
        if user.global_role not in ('teacher', 'sys_admin'):
            # 理论上权限类已拦截，此处做双保险
            raise PermissionError('仅老师或管理员可创建项目复盘')
        serializer.save()

    def create(self, request, *args, **kwargs):
        """创建项目复盘（仅老师/管理员）"""
        user = request.user
        if user.global_role not in ('teacher', 'sys_admin'):
            return error_response(
                message='权限不足，仅老师或管理员可创建项目复盘',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        # 校验同一项目仅能创建一条复盘（OneToOneField 数据库层已保障，
        # 这里提前给出友好错误）
        project_id = request.data.get('project')
        if project_id and ProjectReview.objects.filter(project_id=project_id).exists():
            return error_response(
                message='该项目已存在复盘记录，每个项目仅可创建一条复盘',
                code=1005,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(
            serializer.data,
            message='项目复盘创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新项目复盘（仅老师/管理员）"""
        user = request.user
        if user.global_role not in ('teacher', 'sys_admin'):
            return error_response(
                message='权限不足，仅老师或管理员可更新项目复盘',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, message='项目复盘更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除项目复盘（仅老师/管理员）"""
        user = request.user
        if user.global_role not in ('teacher', 'sys_admin'):
            return error_response(
                message='权限不足，仅老师或管理员可删除项目复盘',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        instance.delete()
        return success_response(message='项目复盘已删除')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        提交复盘
        POST /api/v1/projects/reviews/{id}/submit/
        将复盘状态由 draft 推进为 submitted，并记录复盘人与复盘日期
        """
        user = request.user
        if user.global_role not in ('teacher', 'sys_admin'):
            return error_response(
                message='权限不足，仅老师或管理员可提交复盘',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        review = self.get_object()
        if review.status == ProjectReview.Status.REVIEWED:
            return error_response(message='复盘已审阅，无法再次提交')
        review.status = ProjectReview.Status.SUBMITTED
        review.review_date = timezone.now()
        review.reviewer = request.user
        review.save(update_fields=['status', 'review_date', 'reviewer', 'updated_at'])
        return success_response(
            ProjectReviewSerializer(review).data,
            message='复盘已提交',
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        审阅完成
        POST /api/v1/projects/reviews/{id}/approve/
        将复盘状态推进为 reviewed
        """
        user = request.user
        if user.global_role not in ('teacher', 'sys_admin'):
            return error_response(
                message='权限不足，仅老师或管理员可审阅复盘',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        review = self.get_object()
        review.status = ProjectReview.Status.REVIEWED
        review.save(update_fields=['status', 'updated_at'])
        return success_response(
            ProjectReviewSerializer(review).data,
            message='复盘审阅完成',
        )
