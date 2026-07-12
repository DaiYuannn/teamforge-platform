"""
自定义角色模型
- CustomRole: 自定义角色（带权限列表）
- UserRoleAssignment: 用户-角色-项目 分配关系

放在独立文件中，避免迁移冲突。通过 apps/users/models.py 导入。
"""
from django.db import models


class CustomRole(models.Model):
    """自定义角色"""

    # 角色名（唯一）
    name = models.CharField('角色名', max_length=100, unique=True)
    # 描述
    description = models.TextField('描述', blank=True, default='')
    # 权限列表（如 ['project.create', 'task.delete']）
    permissions = models.JSONField('权限列表', default=list)
    # 是否系统角色（系统角色不可删除）
    is_system = models.BooleanField('系统角色', default=False)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'custom_roles'
        verbose_name = '自定义角色'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class UserRoleAssignment(models.Model):
    """用户角色分配"""

    # 用户
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='role_assignments',
        verbose_name='用户',
    )
    # 角色
    role = models.ForeignKey(
        'users.CustomRole',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='角色',
    )
    # 项目（可为空，表示全局角色）
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='role_assignments',
        verbose_name='项目',
    )
    # 分配人
    assigned_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_roles',
        verbose_name='分配人',
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'user_role_assignments'
        verbose_name = '用户角色分配'
        verbose_name_plural = verbose_name
        unique_together = [('user', 'role', 'project')]

    def __str__(self):
        return f'{self.user} - {self.role}'
