"""
Git 集成模型
- GitRepository: Git 仓库关联

放在独立文件中，避免迁移冲突。通过 apps/integrations/models.py 导入。
"""
from django.db import models
from django.utils import timezone

from common.encryption import get_field_cipher


ENCRYPTED_PREFIX = 'enc:v1:'


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
    connection_status = models.CharField(max_length=20, default='unchecked')
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')
    remote_commit = models.CharField(max_length=64, blank=True, default='')
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

    def save(self, *args, **kwargs):
        if self.token and not self.token.startswith(ENCRYPTED_PREFIX):
            self.token = ENCRYPTED_PREFIX + get_field_cipher().encrypt(self.token)
        super().save(*args, **kwargs)

    def get_token(self):
        if not self.token:
            return ''
        if not self.token.startswith(ENCRYPTED_PREFIX):
            return self.token
        return get_field_cipher().decrypt(self.token[len(ENCRYPTED_PREFIX):])

    def record_connection(self, *, connected, commit='', error='', synced=False):
        now = timezone.now()
        self.connection_status = 'connected' if connected else 'error'
        self.last_checked_at = now
        self.last_error = error
        fields = ['connection_status', 'last_checked_at', 'last_error', 'updated_at']
        if commit:
            self.remote_commit = commit
            fields.append('remote_commit')
        if synced and connected:
            self.last_synced_at = now
            fields.append('last_synced_at')
        self.save(update_fields=fields)
