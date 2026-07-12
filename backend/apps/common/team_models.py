"""
多团队支持模型
- Team: 团队
- TeamMember: 团队成员（中间表）

放在独立文件中，避免迁移冲突。通过 apps/common/models.py 导入。
"""
from django.db import models


class Team(models.Model):
    """团队"""

    # 团队名称
    name = models.CharField('团队名称', max_length=200)
    # 描述
    description = models.TextField('描述', blank=True, default='')
    # 创建人
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='owned_teams',
        verbose_name='创建人',
    )
    # 成员（多对多，通过 TeamMember）
    members = models.ManyToManyField(
        'users.User',
        through='TeamMember',
        related_name='teams',
        verbose_name='成员',
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'teams'
        verbose_name = '团队'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    """团队成员"""

    # 团队
    team = models.ForeignKey(
        'common.Team',
        on_delete=models.CASCADE,
        verbose_name='团队',
    )
    # 成员
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        verbose_name='成员',
    )
    # 角色（如 owner / admin / member）
    role = models.CharField('角色', max_length=50, default='member')
    # 加入时间
    joined_at = models.DateTimeField('加入时间', auto_now_add=True)

    class Meta:
        db_table = 'team_members'
        verbose_name = '团队成员'
        verbose_name_plural = verbose_name
        unique_together = [('team', 'user')]

    def __str__(self):
        return f'{self.user} @ {self.team}({self.role})'
