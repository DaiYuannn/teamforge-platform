"""
文件管理模型
三级权限: public(公开) / internal(内部) / sensitive(敏感)
- public: 所有认证用户可下载
- internal: 项目成员可下载
- sensitive: 走审批流程（第三期实现）
"""
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
