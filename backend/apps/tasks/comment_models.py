"""
任务评论模型
单独文件存放，避免与现有 models.py 产生迁移冲突
支持多级回复（自关联 parent）
"""
from django.db import models


class TaskComment(models.Model):
    """任务评论"""

    # 关联任务
    task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='任务',
    )
    # 评论人
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='task_comments',
        verbose_name='评论人',
    )
    # 评论内容
    content = models.TextField('评论内容')
    # 父评论（用于回复）
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='replies',
        verbose_name='父评论',
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'task_comments'
        verbose_name = '任务评论'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author_id} 评论任务 {self.task_id}'
