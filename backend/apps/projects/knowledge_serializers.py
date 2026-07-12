"""
知识库序列化器
- KnowledgeArticleSerializer: 文章完整序列化
- KnowledgeArticleListSerializer: 文章列表精简序列化
"""
from rest_framework import serializers

from .knowledge_models import KnowledgeArticle


class KnowledgeArticleSerializer(serializers.ModelSerializer):
    """知识库文章序列化器"""
    author_name = serializers.CharField(source='author.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    tag_list = serializers.ListField(read_only=True, default=list)

    class Meta:
        model = KnowledgeArticle
        fields = (
            'id', 'title', 'content', 'category', 'category_display',
            'project', 'project_name', 'author', 'author_name',
            'tags', 'tag_list', 'view_count', 'is_published',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'view_count', 'created_at', 'updated_at')

    def to_representation(self, instance):
        """在序列化时填充 tag_list"""
        ret = super().to_representation(instance)
        ret['tag_list'] = instance.tag_list
        return ret


class KnowledgeArticleListSerializer(serializers.ModelSerializer):
    """知识库文章列表精简序列化器"""
    author_name = serializers.CharField(source='author.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = KnowledgeArticle
        fields = (
            'id', 'title', 'category', 'category_display',
            'project', 'project_name', 'author', 'author_name',
            'tags', 'view_count', 'is_published', 'created_at',
        )
        read_only_fields = fields
