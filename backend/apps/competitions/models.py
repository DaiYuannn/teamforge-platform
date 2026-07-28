"""
比赛模型
记录项目参加的各类比赛信息及进度
"""
from django.db import models
from django.conf import settings

from apps.projects.models import Project


class Competition(models.Model):
    """
    比赛模型
    一个项目可以参加多个比赛，记录每个比赛的报名、评审、答辩、结果等信息
    """

    class Level(models.TextChoices):
        """比赛级别"""
        SCHOOL = 'school', '校赛'
        CITY = 'city', '市赛'
        PROVINCE = 'province', '省赛'
        NATIONAL = 'national', '国赛'

    class Status(models.TextChoices):
        """比赛状态"""
        PREPARING = 'preparing', '准备中'
        ONGOING = 'ongoing', '进行中'
        COMPLETED = 'completed', '已结束'

    # 关联项目
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='competitions',
        verbose_name='所属项目',
    )
    participant_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='CompetitionParticipant',
        related_name='competition_participations',
        verbose_name='参赛成员',
        blank=True,
    )
    # 比赛名称
    name = models.CharField('比赛名称', max_length=200)
    # 比赛类型
    comp_type = models.CharField('比赛类型', max_length=100, blank=True, default='')
    # 比赛级别
    level = models.CharField(
        '比赛级别',
        max_length=20,
        choices=Level.choices,
        default=Level.SCHOOL,
    )
    # 主办单位
    organizer = models.CharField('主办单位', max_length=200, blank=True, default='')
    # 报名日期
    register_date = models.DateField('报名日期', null=True, blank=True)
    # 材料截止日期
    material_deadline = models.DateField('材料截止日期', null=True, blank=True)
    # 网评日期
    review_date = models.DateField('网评日期', null=True, blank=True)
    # 答辩日期
    defense_date = models.DateField('答辩日期', null=True, blank=True)
    # 校赛日期
    school_date = models.DateField('校赛日期', null=True, blank=True)
    # 市赛日期
    city_date = models.DateField('市赛日期', null=True, blank=True)
    # 省赛日期
    province_date = models.DateField('省赛日期', null=True, blank=True)
    # 国赛日期
    national_date = models.DateField('国赛日期', null=True, blank=True)
    # 结果公布日期
    result_date = models.DateField('结果公布日期', null=True, blank=True)
    # 比赛状态
    status = models.CharField(
        '比赛状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PREPARING,
    )
    # 是否晋级
    is_promoted = models.BooleanField('是否晋级', default=False)
    # 是否获奖
    is_awarded = models.BooleanField('是否获奖', default=False)
    # 获奖等级
    award_level = models.CharField('获奖等级', max_length=50, blank=True, default='')
    # 未晋级原因
    not_promoted_reason = models.TextField('未晋级原因', blank=True, default='')
    # 改进建议
    improvement_suggestion = models.TextField('改进建议', blank=True, default='')
    # 评审总结
    review_summary = models.TextField('评审总结', blank=True, default='')
    # 当前阶段
    current_stage = models.CharField('当前阶段', max_length=100, blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'competitions'
        verbose_name = '比赛'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.project.name} - {self.name}({self.get_level_display()})'


class CompetitionParticipant(models.Model):
    """比赛实际组织名单，独立于项目成员和获奖人名单。"""

    class Role(models.TextChoices):
        LEADER = 'leader', '比赛负责人'
        MEMBER = 'member', '参赛成员'
        ADVISOR = 'advisor', '指导成员'

    class ParticipationStatus(models.TextChoices):
        PLANNED = 'planned', '拟参赛'
        CONFIRMED = 'confirmed', '已确认'
        WITHDRAWN = 'withdrawn', '已退出'

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name='比赛',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='competition_participant_records',
        verbose_name='成员',
    )
    role = models.CharField(
        '比赛角色',
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    participation_status = models.CharField(
        '参与状态',
        max_length=20,
        choices=ParticipationStatus.choices,
        default=ParticipationStatus.PLANNED,
        db_index=True,
    )
    responsibility = models.TextField('比赛分工', blank=True, default='')
    joined_at = models.DateTimeField('加入时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'competition_participants'
        verbose_name = '比赛参赛成员'
        verbose_name_plural = verbose_name
        ordering = ['role', 'joined_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=('competition', 'user'),
                name='uniq_competition_participant_user',
            ),
        ]

    def __str__(self):
        return f'{self.competition.name} - {self.user.name}'


from .award_models import CompetitionAward  # noqa: E402,F401
