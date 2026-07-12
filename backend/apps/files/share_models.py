"""
N33: 文件分享链接模型
- FileShareLink: 文件分享链接（支持过期时间、最大访问次数、令牌访问）

单独文件存放，避免与现有 models.py 产生迁移冲突
"""
import uuid

from django.db import models


class FileShareLink(models.Model):
    """文件分享链接"""

    # 关联文件
    file = models.ForeignKey(
        'files.FileAsset',
        on_delete=models.CASCADE,
        related_name='share_links',
        verbose_name='文件',
    )
    # 创建人
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='file_shares',
        verbose_name='创建人',
    )
    # 分享令牌（唯一）
    token = models.CharField('分享令牌', max_length=64, unique=True)
    # 过期时间（可为空，表示永不过期）
    expire_at = models.DateTimeField('过期时间', null=True, blank=True)
    # 最大访问次数（可为空，表示不限）
    max_views = models.IntegerField('最大访问次数', null=True, blank=True)
    # 访问次数
    view_count = models.IntegerField('访问次数', default=0)
    # 是否有效
    is_active = models.BooleanField('有效', default=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'file_share_links'
        verbose_name = '文件分享链接'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.file.name} - {self.token[:8]}...'

    @classmethod
    def generate_token(cls):
        """生成唯一的分享令牌"""
        token = uuid.uuid4().hex
        while cls.objects.filter(token=token).exists():
            token = uuid.uuid4().hex
        return token

    @property
    def is_expired(self):
        """是否已过期"""
        if self.expire_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expire_at

    @property
    def is_view_limit_reached(self):
        """是否已达最大访问次数"""
        if self.max_views is None:
            return False
        return self.view_count >= self.max_views

    @property
    def is_valid(self):
        """链接是否仍有效（未撤销、未过期、未超访问次数）"""
        return (
            self.is_active
            and not self.is_expired
            and not self.is_view_limit_reached
        )
