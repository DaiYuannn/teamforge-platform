"""
多团队支持模型
- Team: 团队
- TeamMember: 团队成员（中间表）

放在独立文件中，避免迁移冲突。通过 apps/common/models.py 导入。
"""
from django.db import models
from django.core.exceptions import ValidationError


class Team(models.Model):
    """团队"""

    class TeamType(models.TextChoices):
        ORGANIZATION = 'organization', '总团队'
        SQUAD = 'squad', '小团队'

    # 团队名称
    name = models.CharField('团队名称', max_length=200)
    # 描述
    description = models.TextField('描述', blank=True, default='')
    code = models.CharField('团队编号', max_length=50, unique=True, null=True, blank=True)
    logo = models.ImageField('团队标志', upload_to='public/team/', null=True, blank=True)
    contact_email = models.EmailField('联系邮箱', blank=True, default='')
    join_message = models.TextField('加入我们说明', blank=True, default='')
    is_active = models.BooleanField('是否启用', default=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='child_teams',
        verbose_name='上级团队',
        null=True,
        blank=True,
    )
    team_type = models.CharField(
        '团队类型',
        max_length=20,
        choices=TeamType.choices,
        default=TeamType.ORGANIZATION,
    )
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

    def clean(self):
        super().clean()
        errors = {}
        if self.parent_id:
            if self.pk and self.parent_id == self.pk:
                errors['parent'] = '团队不能将自己设为上级团队'
            elif self.parent and self.parent.parent_id:
                errors['parent'] = '团队组织最多支持“总团队—小团队”两级'
            elif self.pk and self.child_teams.exists():
                errors['parent'] = '已有直属小团队的总团队不能再设为其他团队的下级'
            if self.team_type != self.TeamType.SQUAD:
                errors['team_type'] = '设置上级团队后，团队类型必须为小团队'
        elif self.team_type != self.TeamType.ORGANIZATION:
            errors['team_type'] = '没有上级团队时，团队类型必须为总团队'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class TeamMember(models.Model):
    """团队成员"""

    class Role(models.TextChoices):
        OWNER = 'owner', '负责人'
        CO_LEAD = 'co_lead', '共同负责人'
        ADMIN = 'admin', '团队管理员'
        TEACHER = 'teacher', '查看老师（只读）'
        MEMBER = 'member', '团队成员'
        ADVISOR = 'advisor', '顾问'
        EXTERNAL = 'external', '外部协作者'

    class Status(models.TextChoices):
        ACTIVE = 'active', '在队'
        ON_LEAVE = 'on_leave', '暂离'
        EXITED = 'exited', '已离队'

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
    role = models.CharField('角色', max_length=50, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(
        '成员状态',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    # 加入时间
    joined_at = models.DateTimeField('加入时间', auto_now_add=True)
    left_at = models.DateTimeField('离队时间', null=True, blank=True)
    exit_reason = models.TextField('离队原因', blank=True, default='')
    handover_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handover_from_members',
        verbose_name='交接成员',
    )
    handover_notes = models.TextField('交接说明', blank=True, default='')

    class Meta:
        db_table = 'team_members'
        verbose_name = '团队成员'
        verbose_name_plural = verbose_name
        unique_together = [('team', 'user')]

    def __str__(self):
        return f'{self.user} @ {self.team}({self.role})'


class TeamMembershipEvent(models.Model):
    """团队成员关系的变更历史。"""

    membership = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='团队成员关系',
    )
    event_type = models.CharField('事件类型', max_length=30)
    from_role = models.CharField('原角色', max_length=50, blank=True, default='')
    to_role = models.CharField('新角色', max_length=50, blank=True, default='')
    from_status = models.CharField('原状态', max_length=20, blank=True, default='')
    to_status = models.CharField('新状态', max_length=20, blank=True, default='')
    reason = models.TextField('原因', blank=True, default='')
    handover_to = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_handover_events',
        verbose_name='交接成员',
    )
    handover_notes = models.TextField('交接说明', blank=True, default='')
    operator = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operated_team_membership_events',
        verbose_name='操作人',
    )
    created_at = models.DateTimeField('发生时间', auto_now_add=True)

    class Meta:
        db_table = 'team_membership_events'
        verbose_name = '团队成员变动记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at', '-id']
