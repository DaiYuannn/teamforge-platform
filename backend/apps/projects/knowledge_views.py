"""
知识库视图
- KnowledgeArticleViewSet: 文章 CRUD + 搜索（标题/内容/标签）+ 按类别/项目过滤
"""
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from .knowledge_models import KnowledgeArticle
from .knowledge_serializers import (
    KnowledgeArticleSerializer,
    KnowledgeArticleListSerializer,
)


class KnowledgeArticleViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    知识库文章管理 ViewSet
    - list/retrieve: 所有认证用户可查看
    - create/update/destroy: 所有认证用户可操作（作者/老师/管理员）
    - search: 按标题/内容/标签搜索
    """
    queryset = KnowledgeArticle.objects.all().select_related('project', 'author')

    serializer_classes_by_action = {
        'list': KnowledgeArticleListSerializer,
        'retrieve': KnowledgeArticleSerializer,
        'create': KnowledgeArticleSerializer,
        'update': KnowledgeArticleSerializer,
        'partial_update': KnowledgeArticleSerializer,
        'search': KnowledgeArticleListSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'update': [IsAuthenticated],
        'partial_update': [IsAuthenticated],
        'destroy': [IsAuthenticated],
        'search': [IsAuthenticated],
    }

    filterset_fields = ['category', 'project', 'author', 'is_published']
    search_fields = ['title', 'content', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'view_count']

    def get_queryset(self):
        """
        支持按类别、项目过滤，以及关键词搜索
        - search: 搜索标题/内容/标签
        - category: 按类别过滤
        - project: 按项目过滤
        - tag: 按标签过滤
        """
        queryset = super().get_queryset()
        params = self.request.query_params

        # 关键词搜索（标题/内容/标签）
        keyword = params.get('search') or params.get('q')
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(content__icontains=keyword) |
                Q(tags__icontains=keyword)
            )

        # 按标签过滤
        tag = params.get('tag')
        if tag:
            queryset = queryset.filter(tags__icontains=tag)

        return queryset

    def create(self, request, *args, **kwargs):
        """创建知识库文章，自动设置作者"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=request.user)
        return success_response(
            KnowledgeArticleSerializer(article, context={'request': request}).data,
            message='知识库文章创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新知识库文章"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        if not self._can_modify(request.user, instance):
            return error_response(
                message='仅作者、老师或管理员可编辑文章',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        article = serializer.save()
        return success_response(
            KnowledgeArticleSerializer(article, context={'request': request}).data,
            message='知识库文章更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除知识库文章"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        if not self._can_modify(request.user, instance):
            return error_response(
                message='仅作者、老师或管理员可删除文章',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return success_response(message='知识库文章已删除')

    def retrieve(self, request, *args, **kwargs):
        """获取文章详情，并增加浏览数"""
        instance = self.get_object()
        instance.view_count = (instance.view_count or 0) + 1
        instance.save(update_fields=['view_count'])
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        搜索知识库文章
        GET /api/v1/projects/knowledge/search/?q=关键词
        搜索范围: 标题、内容、标签
        """
        keyword = request.query_params.get('q', '').strip()
        if not keyword:
            return success_response([])
        articles = self.get_queryset().filter(
            Q(title__icontains=keyword) |
            Q(content__icontains=keyword) |
            Q(tags__icontains=keyword)
        )
        serializer = self.get_serializer(articles, many=True)
        return success_response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-tag')
    def by_tag(self, request):
        """
        按标签查询文章
        GET /api/v1/projects/knowledge/by-tag/?tag=标签名
        """
        tag = request.query_params.get('tag', '').strip()
        if not tag:
            return error_response(message='请提供 tag 参数', code=1005)
        articles = self.get_queryset().filter(tags__icontains=tag)
        serializer = KnowledgeArticleListSerializer(
            articles, many=True, context={'request': request}
        )
        return success_response(serializer.data)

    @staticmethod
    def _can_modify(user, article):
        """判断用户是否可修改/删除文章"""
        if user.global_role in ['teacher', 'sys_admin']:
            return True
        return article.author_id == user.id
