"""
讨论区视图
- DiscussionTopicViewSet: 主题 CRUD + 回复 + 置顶/关闭
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.project_access import scope_project_queryset, user_can_access_project
from .discussion_models import DiscussionTopic, DiscussionReply
from .discussion_serializers import (
    DiscussionTopicSerializer,
    DiscussionTopicListSerializer,
    DiscussionReplySerializer,
)


class DiscussionTopicViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    讨论主题管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create: 所有认证用户可发起讨论
    - update/destroy: 作者/老师/管理员
    - reply: 回复主题
    - replies: 获取主题回复列表
    - toggle_pin: 置顶/取消置顶（老师/管理员）
    - toggle_close: 关闭/开启主题（老师/管理员）
    """
    queryset = DiscussionTopic.objects.all().select_related('project', 'author')

    serializer_classes_by_action = {
        'list': DiscussionTopicListSerializer,
        'retrieve': DiscussionTopicSerializer,
        'create': DiscussionTopicSerializer,
        'update': DiscussionTopicSerializer,
        'partial_update': DiscussionTopicSerializer,
        'reply': DiscussionReplySerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'update': [IsAuthenticated],
        'partial_update': [IsAuthenticated],
        'destroy': [IsAuthenticated],
        'reply': [IsAuthenticated],
        'replies': [IsAuthenticated],
        'toggle_pin': [IsAuthenticated],
        'toggle_close': [IsAuthenticated],
    }

    filterset_fields = ['project', 'author', 'is_pinned', 'is_closed']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'updated_at', 'view_count', 'reply_count']

    def get_queryset(self):
        """内部成员透明读取；外部协作者仅可见获授权项目。"""
        return scope_project_queryset(
            super().get_queryset(),
            self.request.user,
            project_lookup='project',
        )

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        write = request.method not in ('GET', 'HEAD', 'OPTIONS')
        if not user_can_access_project(request.user, obj.project, write=write):
            self.permission_denied(request, message='无权访问该项目讨论')

    def create(self, request, *args, **kwargs):
        """创建讨论主题，自动设置作者为当前用户"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data.get('project')
        if not user_can_access_project(request.user, project, write=True):
            return error_response(
                message='仅项目活动成员可发起讨论',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        topic = serializer.save(author=request.user)
        return success_response(
            DiscussionTopicSerializer(topic, context={'request': request}).data,
            message='讨论主题创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新讨论主题（仅作者/老师/管理员）"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        if not self._can_modify(request.user, instance):
            return error_response(
                message='仅作者、老师或管理员可编辑讨论主题',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        target_project = serializer.validated_data.get('project', instance.project)
        if not user_can_access_project(request.user, target_project, write=True):
            return error_response(
                message='无权将讨论移动到该项目',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        topic = serializer.save()
        return success_response(
            DiscussionTopicSerializer(topic, context={'request': request}).data,
            message='讨论主题更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除讨论主题（仅作者/老师/管理员）"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        if not self._can_modify(request.user, instance):
            return error_response(
                message='仅作者、老师或管理员可删除讨论主题',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return success_response(message='讨论主题已删除')

    def retrieve(self, request, *args, **kwargs):
        """获取主题详情，并增加浏览数"""
        instance = self.get_object()
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """
        回复讨论主题
        POST /api/v1/projects/discussions/{id}/reply/
        body: {"content": "回复内容", "parent": <parent_reply_id, 可选>}
        """
        topic = self.get_object()
        if topic.is_closed:
            return error_response(
                message='该讨论主题已关闭，无法回复',
                code=1006,
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        content = request.data.get('content', '').strip()
        if not content:
            return error_response(message='回复内容不能为空', code=1005)
        parent_id = request.data.get('parent')
        parent = None
        if parent_id:
            try:
                parent = DiscussionReply.objects.get(id=parent_id, topic=topic)
            except DiscussionReply.DoesNotExist:
                return error_response(message='父回复不存在', code=1004,
                                      http_status=status.HTTP_404_NOT_FOUND)
        reply = DiscussionReply.objects.create(
            topic=topic,
            author=request.user,
            content=content,
            parent=parent,
        )
        topic.refresh_reply_count()
        return success_response(
            DiscussionReplySerializer(reply, context={'request': request}).data,
            message='回复成功',
            http_status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """
        获取主题的回复列表
        GET /api/v1/projects/discussions/{id}/replies/
        """
        topic = self.get_object()
        replies = topic.replies.select_related('author').all()
        serializer = DiscussionReplySerializer(replies, many=True, context={'request': request})
        return success_response(serializer.data)

    @action(detail=True, methods=['post'], url_path='toggle-pin')
    def toggle_pin(self, request, pk=None):
        """
        切换置顶状态（仅老师/管理员）
        POST /api/v1/projects/discussions/{id}/toggle-pin/
        """
        topic = self.get_object()
        if request.user.global_role not in ['teacher', 'sys_admin']:
            return error_response(
                message='仅老师或管理员可置顶讨论主题',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        topic.is_pinned = not topic.is_pinned
        topic.save(update_fields=['is_pinned', 'updated_at'])
        msg = '已置顶' if topic.is_pinned else '已取消置顶'
        return success_response(
            DiscussionTopicListSerializer(topic, context={'request': request}).data,
            message=msg,
        )

    @action(detail=True, methods=['post'], url_path='toggle-close')
    def toggle_close(self, request, pk=None):
        """
        切换关闭状态（仅老师/管理员）
        POST /api/v1/projects/discussions/{id}/toggle-close/
        """
        topic = self.get_object()
        if request.user.global_role not in ['teacher', 'sys_admin']:
            return error_response(
                message='仅老师或管理员可关闭讨论主题',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        topic.is_closed = not topic.is_closed
        topic.save(update_fields=['is_closed', 'updated_at'])
        msg = '已关闭' if topic.is_closed else '已重新开启'
        return success_response(
            DiscussionTopicListSerializer(topic, context={'request': request}).data,
            message=msg,
        )

    @staticmethod
    def _can_modify(user, topic):
        """判断用户是否可修改/删除主题"""
        if user.global_role in ['teacher', 'sys_admin']:
            return True
        return topic.author_id == user.id
