"""
任务评论视图
- TaskCommentViewSet: 评论 CRUD（支持回复）
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.project_access import scope_project_queryset, user_can_access_project
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

    def get_queryset(self):
        return scope_project_queryset(
            super().get_queryset().select_related('task__project', 'author'),
            self.request.user,
            project_lookup='task__project',
        )

    def create(self, request, *args, **kwargs):
        """创建评论，自动设置作者为当前用户"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.validated_data.get('task')
        if not user_can_access_project(request.user, task.project, write=True):
            return error_response(
                message='无权在该项目任务下发表评论',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        parent = serializer.validated_data.get('parent')
        if parent is not None and parent.task_id != task.id:
            return error_response(
                message='父评论必须属于同一任务',
                code=1005,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
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
        target_task = serializer.validated_data.get('task', instance.task)
        if not user_can_access_project(request.user, target_task.project, write=True):
            return error_response(
                message='无权将评论移动到该项目任务',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        parent = serializer.validated_data.get('parent', instance.parent)
        if parent is not None and parent.task_id != target_task.id:
            return error_response(
                message='父评论必须属于同一任务',
                code=1005,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
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
        write = request.method not in ('GET', 'HEAD', 'OPTIONS')
        if not user_can_access_project(
            request.user,
            instance.task.project,
            write=write,
        ):
            self.permission_denied(request, message='无权访问该任务评论')

        # list/retrieve/create 不在此校验作者权限
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
