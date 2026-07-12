"""
文件标签模型
- FileTag: 标签定义（可关联项目，形成项目级标签）
- FileTagRelation: 文件-标签多对多关联

放在独立文件中，避免与主文件模型迁移冲突。
"""
from django.db import models
from django.conf import settings


class FileTag(models.Model):
    """文件标签"""

    # 标签名
    name = models.CharField('标签名', max_length=50)
    # 颜色（十六进制色值）
    color = models.CharField('颜色', max_length=20, default='#409EFF')
    # 关联项目（可为空，表示全局标签）
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='file_tags',
        verbose_name='项目',
    )
    # 创建人
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='file_tags',
        verbose_name='创建人',
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'file_tags'
        verbose_name = '文件标签'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        # 同一项目下标签名唯一（项目为空时全局唯一）
        unique_together = [('name', 'project')]

    def __str__(self):
        return f'{self.name}({self.color})'


class FileTagRelation(models.Model):
    """文件-标签关联"""

    # 关联文件
    file = models.ForeignKey(
        'files.FileAsset',
        on_delete=models.CASCADE,
        related_name='tag_relations',
        verbose_name='文件',
    )
    # 关联标签
    tag = models.ForeignKey(
        'files.FileTag',
        on_delete=models.CASCADE,
        related_name='file_relations',
        verbose_name='标签',
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'file_tag_relations'
        verbose_name = '文件标签关联'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        # 同一文件同一标签唯一
        unique_together = [('file', 'tag')]

    def __str__(self):
        return f'{self.file.name} - {self.tag.name}'
