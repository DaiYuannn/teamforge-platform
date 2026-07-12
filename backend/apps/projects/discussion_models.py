"""
讨论区模型
- DiscussionTopic: 讨论主题
- DiscussionReply: 讨论回复（支持嵌套回复）

单独文件存放，避免与现有 models.py 产生迁移冲突
"""
from django.db import models


class DiscussionTopic(models.Model):
    """讨论主题"""

    # 所属项目
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='discussions',
        verbose_name='项目',
    )
    # 标题
    title = models.CharField('标题', max_length=200)
    # 内容
    content = models.TextField('内容')
    # 发起人
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='discussion_topics',
        verbose_name='发起人',
    )
    # 是否置顶
    is_pinned = models.BooleanField('置顶', default=False)
    # 是否已关闭
    is_closed = models.BooleanField('已关闭', default=False)
    # 浏览数
    view_count = models.IntegerField('浏览数', default=0)
    # 回复数
    reply_count = models.IntegerField('回复数', default=0)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'discussion_topics'
        verbose_name = '讨论主题'
        verbose_name_plural = verbose_name
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f'{self.project.name} - {self.title}'

    def increment_view_count(self):
        """增加浏览数"""
        self.view_count = (self.view_count or 0) + 1
        self.save(update_fields=['view_count'])

    def refresh_reply_count(self):
        """刷新回复数"""
        self.reply_count = self.replies.count()
        self.save(update_fields=['reply_count'])


class DiscussionReply(models.Model):
    """讨论回复"""

    # 关联主题
    topic = models.ForeignKey(
        'projects.DiscussionTopic',
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name='主题',
    )
    # 回复人
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='discussion_replies',
        verbose_name='回复人',
    )
    # 回复内容
    content = models.TextField('回复内容')
    # 父回复（支持嵌套）
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children',
        verbose_name='父回复',
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'discussion_replies'
        verbose_name = '讨论回复'
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return f'{self.topic.title} - {self.author.name}'
