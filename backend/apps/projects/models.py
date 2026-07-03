"""
项目模型
包含 Project（项目）、ProjectMember（项目成员）、ProjectStageLog（项目阶段日志）
"""
from django.db import models
from django.conf import settings


class Project(models.Model):
    """
    项目模型
    包含 16 个阶段的生命周期管理
    """

    class Stage(models.IntegerChoices):
        """项目阶段（16个阶段）"""
        CONCEIVING = 1, '构思中'
        APPROVED = 2, '已立项'
        MATERIAL_PREP = 3, '材料准备中'
        DEV_EXPERIMENT = 4, '开发实验制作中'
        REGISTER_PREP = 5, '报名准备'
        MATERIAL_SUBMIT = 6, '材料提交'
        REVIEW_AUDIT = 7, '网评审核'
        DEFENSE_PREP = 8, '答辩准备'
        SCHOOL_COMP = 9, '校赛'
        CITY_COMP = 10, '市赛'
        PROVINCE_COMP = 11, '省赛'
        NATIONAL_COMP = 12, '国赛'
        AWARDED = 13, '已获奖'
        CLOSED = 14, '已结项'
        PAUSED = 15, '暂停'
        TERMINATED = 16, '终止'

    class Status(models.TextChoices):
        """项目状态"""
        ACTIVE = 'active', '进行中'
        PAUSED = 'paused', '暂停'
        CLOSED = 'closed', '已关闭'

    class Priority(models.TextChoices):
        """优先级"""
        NORMAL = 'normal', '普通'
        HIGH = 'high', '高'
        URGENT = 'urgent', '紧急'

    # 项目名称
    name = models.CharField('项目名称', max_length=200)
    # 项目编号（唯一）
    code = models.CharField('项目编号', max_length=50, unique=True)
    # 项目负责人
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='led_projects',
        verbose_name='项目负责人',
    )
    # 当前阶段
    current_stage = models.IntegerField(
        '当前阶段',
        choices=Stage.choices,
        default=Stage.CONCEIVING,
    )
    # 开始日期
    start_date = models.DateField('开始日期', null=True, blank=True)
    # 计划结束日期
    planned_end_date = models.DateField('计划结束日期', null=True, blank=True)
    # 实际结束日期
    actual_end_date = models.DateField('实际结束日期', null=True, blank=True)
    # 项目状态
    status = models.CharField(
        '项目状态',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    # 优先级
    priority = models.CharField(
        '优先级',
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    # 项目简介
    intro = models.TextField('项目简介', blank=True, default='')
    # 负责人最近更新时间（打卡）
    last_leader_update = models.DateTimeField('负责人最近更新时间', null=True, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'projects'
        verbose_name = '项目'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} - {self.name}'

    @property
    def stage_name(self):
        """获取当前阶段名称"""
        return self.get_current_stage_display()


class ProjectMember(models.Model):
    """
    项目成员模型
    一个用户可以参与多个项目，一个项目可以有多个成员
    """

    class RoleInProject(models.TextChoices):
        """项目中角色"""
        LEADER = 'leader', '负责人'
        CORE = 'core', '核心成员'
        PARTICIPANT = 'participant', '普通参与'

    # 所属项目
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name='所属项目',
    )
    # 成员用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
        verbose_name='成员',
    )
    # 在项目中的角色
    role_in_project = models.CharField(
        '项目角色',
        max_length=20,
        choices=RoleInProject.choices,
        default=RoleInProject.PARTICIPANT,
    )
    # 加入时间
    joined_at = models.DateTimeField('加入时间', auto_now_add=True)

    class Meta:
        db_table = 'project_members'
        verbose_name = '项目成员'
        verbose_name_plural = verbose_name
        # 同一项目同一用户唯一
        unique_together = ('project', 'user')

    def __str__(self):
        return f'{self.project.name} - {self.user.name}'


class ProjectStageLog(models.Model):
    """
    项目阶段变更日志
    记录项目阶段推进的历史
    """

    # 所属项目
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='stage_logs',
        verbose_name='所属项目',
    )
    # 原阶段（首次创建时为 null）
    from_stage = models.IntegerField('原阶段', choices=Project.Stage.choices, null=True, blank=True)
    # 目标阶段
    to_stage = models.IntegerField('目标阶段', choices=Project.Stage.choices)
    # 操作人
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='stage_operations',
        verbose_name='操作人',
        null=True, blank=True,
    )
    # 备注
    note = models.TextField('备注', blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'project_stage_logs'
        verbose_name = '项目阶段日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.project.name}: {self.from_stage} -> {self.to_stage}'
