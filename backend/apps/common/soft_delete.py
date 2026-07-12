"""
软删除 Mixin 与管理器
为模型提供软删除（回收站）能力：
- is_deleted / deleted_at / deleted_by 三个字段
- soft_delete(user) / restore() 两个方法
- 默认管理器 objects 仅返回未删除对象（is_deleted=False）
- all_objects 管理器返回全部对象（含已删除），供回收站使用

使用方式：
    from apps.common.soft_delete import SoftDeleteMixin, SoftDeleteManager

    class Project(SoftDeleteMixin, models.Model):
        objects = SoftDeleteManager()   # 默认管理器：过滤已删除
        all_objects = models.Manager()  # 全部对象：含已删除（回收站使用）
        ...

Django 行为说明（Django 5.0）：
- 反向关系访问（如 project.tasks）使用相关模型的 _default_manager，
  即 objects（过滤管理器），因此会自动排除已软删除的对象。
- Django 内部操作（如级联收集）使用 _base_manager，默认是未过滤的
  普通 Manager，因此不会因过滤管理器而漏掉对象。
"""
from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """软删除管理器：默认仅返回未删除的对象（is_deleted=False）"""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteMixin(models.Model):
    """软删除 Mixin"""

    is_deleted = models.BooleanField('已删除', default=False, db_index=True)
    deleted_at = models.DateTimeField('删除时间', null=True, blank=True)
    deleted_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_deleted', verbose_name='删除人'
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """软删除：标记为已删除并记录删除时间与操作人"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user and user.is_authenticated:
            self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        """恢复：清除软删除标记"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
