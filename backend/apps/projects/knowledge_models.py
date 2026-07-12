"""
知识库模型
- KnowledgeArticle: 知识库文章（指南/模板/FAQ/经验分享等）

单独文件存放，避免与现有 models.py 产生迁移冲突
"""
from django.db import models


class KnowledgeArticle(models.Model):
    """知识库文章"""

    class Category(models.TextChoices):
        """文章类别"""
        GUIDE = 'guide', '指南'
        TEMPLATE = 'template', '模板'
        FAQ = 'faq', '常见问题'
        EXPERIENCE = 'experience', '经验分享'
        OTHER = 'other', '其他'

    # 标题
    title = models.CharField('标题', max_length=200)
    # 内容
    content = models.TextField('内容')
    # 类别
    category = models.CharField(
        '类别',
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    # 关联项目（可为空，表示全局知识）
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='knowledge_articles',
        verbose_name='关联项目',
    )
    # 作者
    author = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='knowledge_articles',
        verbose_name='作者',
    )
    # 标签（逗号分隔）
    tags = models.CharField('标签', max_length=500, blank=True, default='')
    # 浏览数
    view_count = models.IntegerField('浏览数', default=0)
    # 是否已发布
    is_published = models.BooleanField('已发布', default=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'knowledge_articles'
        verbose_name = '知识库文章'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def tag_list(self):
        """将逗号分隔的标签拆分为列表"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]
