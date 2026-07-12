"""
成员技能矩阵模型
单独文件存放，避免与现有 models.py 产生迁移冲突
注意：apps/members 中已有一个架构预留的 MemberSkill（基于 SkillTag 外键），
本模型为独立的技能矩阵实现（含 name/level/certified 字段），
使用独立的 db_table 和 related_name 以避免冲突。
"""
from django.db import models


class MemberSkill(models.Model):
    """成员技能矩阵"""

    # 关联用户
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='skill_matrix',
        verbose_name='用户',
    )
    # 技能名称
    name = models.CharField('技能名称', max_length=100)
    # 熟练度（1-5）
    level = models.IntegerField('熟练度', default=1)
    # 是否已认证
    certified = models.BooleanField('已认证', default=False)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'users_member_skills'
        verbose_name = '成员技能矩阵'
        verbose_name_plural = verbose_name
        unique_together = [('user', 'name')]
        ordering = ['-level', '-created_at']

    def __str__(self):
        return f'{self.user.name} - {self.name}(Lv.{self.level})'
