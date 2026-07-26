"""
文件管理模型
三级权限: public(公开) / internal(内部) / sensitive(敏感)
- public: 所有认证用户可下载
- internal: 项目成员可下载
- sensitive: 走审批流程（第三期实现）
"""
import hashlib

from django.db import models
from django.conf import settings

from apps.projects.models import Project


class FileAsset(models.Model):
    """
    文件资源模型
    支持三级权限控制
    """

    class Level(models.TextChoices):
        """文件权限级别"""
        PUBLIC = 'public', '公开'
        INTERNAL = 'internal', '内部'
        SENSITIVE = 'sensitive', '敏感'

    # 关联项目（可为空，表示公共文件）
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='所属项目',
        null=True, blank=True,
    )
    # 文件名称
    name = models.CharField('文件名称', max_length=255)
    # 文件
    file = models.FileField('文件', upload_to='files/%Y%m/')
    # 权限级别
    level = models.CharField(
        '权限级别',
        max_length=20,
        choices=Level.choices,
        default=Level.PUBLIC,
    )
    # 文件大小（字节）
    size = models.BigIntegerField('文件大小', default=0)
    # 内容类型
    content_type = models.CharField('内容类型', max_length=100, blank=True, default='')
    # 上传人
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='uploaded_files',
        verbose_name='上传人',
        null=True, blank=True,
    )
    # 版本号
    version = models.IntegerField('版本号', default=1)
    # 文件哈希（SHA-256，上传时自动计算）
    file_hash = models.CharField('文件哈希', max_length=64, blank=True, default='')
    # 水印文字（可选，下载水印版本时使用）
    watermark_text = models.CharField('水印文字', max_length=200, blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'file_assets'
        verbose_name = '文件资源'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        重写保存逻辑：
        - 已关联敏感资料的附件不允许降级为公开/内部文件
        - 调用父类保存（文件会通过 pre_save 写入存储）
        - 保存后计算 SHA-256 哈希，若哈希有变化则单独更新
        - 敏感文件自动撤销历史分享链接
        """
        if self.pk:
            from apps.sensitive.models import SensitiveData

            if SensitiveData.objects.filter(file_attachment_id=self.pk).exists():
                self.level = self.Level.SENSITIVE
                update_fields = kwargs.get('update_fields')
                if update_fields is not None:
                    kwargs['update_fields'] = set(update_fields) | {'level'}

        super().save(*args, **kwargs)
        self._update_file_hash_if_needed()
        if self.level == self.Level.SENSITIVE:
            from .share_models import FileShareLink

            FileShareLink.objects.filter(
                file_id=self.pk,
                is_active=True,
            ).update(is_active=False)

    def _compute_sha256(self):
        """计算文件 SHA-256 哈希，文件不可读时返回 None"""
        if not self.file:
            return None
        try:
            self.file.open('rb')
            try:
                sha256 = hashlib.sha256()
                for chunk in iter(lambda: self.file.read(8192), b''):
                    sha256.update(chunk)
                return sha256.hexdigest()
            finally:
                self.file.close()
        except Exception:
            # 文件不存在或不可读（如测试中的虚拟路径），跳过
            return None

    def _update_file_hash_if_needed(self):
        """计算并更新文件哈希（仅在哈希变化时写入数据库）"""
        new_hash = self._compute_sha256()
        if new_hash and new_hash != self.file_hash:
            self.file_hash = new_hash
            # 使用查询集更新，避免再次触发 save 逻辑
            type(self).objects.filter(pk=self.pk).update(file_hash=new_hash)


class FileVersion(models.Model):
    """
    文件版本模型（架构预留）
    记录文件的历史版本
    """

    # 关联文件资源
    file_asset = models.ForeignKey(
        FileAsset,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='文件资源',
    )
    # 版本文件
    file = models.FileField('版本文件', upload_to='files/versions/%Y%m/')
    # 版本号
    version = models.IntegerField('版本号', default=1)
    # 上传人
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='uploaded_file_versions',
        verbose_name='上传人',
        null=True, blank=True,
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'file_versions'
        verbose_name = '文件版本'
        verbose_name_plural = verbose_name
        ordering = ['-version']

    def __str__(self):
        return f'{self.file_asset.name} v{self.version}'


# 导入文件标签模型（独立文件，避免迁移冲突）
from .tag_models import FileTag, FileTagRelation  # noqa: E402,F401
from .share_models import FileShareLink  # noqa: E402,F401
