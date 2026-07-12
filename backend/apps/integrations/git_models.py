"""
Git 集成模型
- GitRepository: Git 仓库关联

放在独立文件中，避免迁移冲突。通过 apps/integrations/models.py 导入。
"""
from django.db import models


class GitRepository(models.Model):
    """Git 仓库"""

    # 仓库地址
    url = models.URLField('仓库地址')
    # 分支
    branch = models.CharField('分支', max_length=100, default='main')
    # 访问令牌
    token = models.CharField('访问令牌', max_length=500, blank=True, default='')
    # 关联项目
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='git_repositories',
        verbose_name='项目',
    )
    # 创建人
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_git_repositories',
        verbose_name='创建人',
    )
    # 是否启用
    is_active = models.BooleanField('是否启用', default=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'git_repositories'
        verbose_name = 'Git仓库'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.url}({self.branch})'
