"""
任务评论视图
- TaskCommentViewSet: 评论 CRUD（支持回复）
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from .comment_models import TaskComment
from .comment_serializers import TaskCommentSerializer


class TaskCommentViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    任务评论管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create: 所有认证用户可评论
    - update/destroy: 评论作者或管理员/老师
    """
    queryset = TaskComment.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': TaskCommentSerializer,
        'retrieve': TaskCommentSerializer,
        'create': TaskCommentSerializer,
        'update': TaskCommentSerializer,
        'partial_update': TaskCommentSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'update': [IsAuthenticated],
        'partial_update': [IsAuthenticated],
        'destroy': [IsAuthenticated],
    }

    filterset_fields = ['task', 'author', 'parent']
    search_fields = ['content', 'task__title']
    ordering_fields = ['created_at', 'updated_at']

    def create(self, request, *args, **kwargs):
        """创建评论，自动设置作者为当前用户"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(author=request.user)
        return success_response(
            TaskCommentSerializer(comment).data,
            message='评论发布成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新评论（仅作者或老师/管理员）"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        return success_response(TaskCommentSerializer(comment).data, message='评论更新成功')

    def destroy(self, request, *args, **kwargs):
        """删除评论（仅作者或老师/管理员）"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return success_response(message='评论已删除')

    def check_object_permissions(self, request, instance):
        """
        对象级权限：
        - create 时由 create 方法处理
        - update/destroy：仅作者本人、老师、管理员可操作
        """
        # list/retrieve/create 不在此校验对象级权限
        if self.action in ('update', 'partial_update', 'destroy'):
            user = request.user
            if not user.is_authenticated:
                self.permission_denied(
                    request,
                    message='请先登录',
                )
            is_owner = instance.author_id == user.id
            is_staff = user.global_role in ('teacher', 'sys_admin')
            if not (is_owner or is_staff):
                self.permission_denied(
                    request,
                    message='无权操作他人评论',
                )
        else:
            super().check_object_permissions(request, instance)
