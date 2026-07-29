"""
用户模型
扩展 Django AbstractUser，增加团队管理相关字段
"""
import re

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

# 导入分散在独立文件中的模型，使 Django 迁移系统能检测到它们
from .login_security_models import LoginAttempt, IPBlocklist  # noqa: F401
from .role_models import CustomRole, UserRoleAssignment  # noqa: F401
from .oauth_models import OAuthAccount  # noqa: F401


class User(AbstractUser):
    """
    用户模型
    - 使用 email 作为登录字段（USERNAME_FIELD='email'）
    - 全局角色: sys_admin(系统管理员) / teacher(老师) / member(普通成员) / sens_approver(敏感审批人)
    - 公共访客是未登录态，不需要角色
    """

    class GlobalRole(models.TextChoices):
        """全局角色枚举"""
        SYS_ADMIN = 'sys_admin', '系统管理员'
        # 小团队版只保留一个具有全局业务操作权限的老师账号。
        # 其他老师使用普通全局角色，并在具体团队中配置为“查看老师（只读）”。
        TEACHER = 'teacher', '操作老师'
        MEMBER = 'member', '普通成员'
        SENS_APPROVER = 'sens_approver', '敏感审批人'

    class MembershipStatus(models.TextChoices):
        """成员在团队中的生命周期状态（与账号启停相互独立）。"""
        ACTIVE = 'active', '在队'
        ON_LEAVE = 'on_leave', '暂离'
        EXITED = 'exited', '已离队'
        EXTERNAL = 'external', '外部协作者'

    # 姓名
    name = models.CharField('姓名', max_length=50)
    # 邮箱（唯一，作为登录字段）
    email = models.EmailField('邮箱', unique=True)
    # 手机号
    phone = models.CharField('手机号', max_length=20, blank=True, default='')
    # 头像
    avatar = models.ImageField('头像', upload_to='avatars/', blank=True, null=True)
    # 全局角色
    global_role = models.CharField(
        '全局角色',
        max_length=20,
        choices=GlobalRole.choices,
        default=GlobalRole.MEMBER,
    )
    # 是否为学生
    is_student = models.BooleanField('是否学生', default=True)
    # 年级
    grade = models.CharField('年级', max_length=50, blank=True, default='')
    # 专业
    major = models.CharField('专业', max_length=100, blank=True, default='')
    # 学校
    school = models.CharField('学校', max_length=150, blank=True, default='')
    membership_status = models.CharField(
        '成员状态',
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True,
    )
    team_joined_at = models.DateField('加入团队日期', null=True, blank=True)
    team_left_at = models.DateTimeField('离队时间', null=True, blank=True)
    exit_reason = models.TextField('离队原因', blank=True, default='')
    handover_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handover_from_users',
        verbose_name='交接人',
    )
    handover_notes = models.TextField('交接说明', blank=True, default='')

    # 使用 email 作为登录字段
    USERNAME_FIELD = 'email'
    # 创建超级用户时需要填写的字段
    REQUIRED_FIELDS = ['username', 'name']

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-date_joined']
        constraints = [
            models.UniqueConstraint(
                fields=('global_role',),
                condition=(
                    models.Q(
                        global_role='teacher',
                        is_active=True,
                    )
                    & ~models.Q(
                        membership_status='exited',
                    )
                ),
                name='uniq_active_operating_teacher',
            ),
        ]

    def __str__(self):
        return f'{self.name}({self.email})'

    def save(self, *args, **kwargs):
        if self._state.adding and self.team_joined_at is None:
            self.team_joined_at = timezone.localdate()
        super().save(*args, **kwargs)

    @property
    def is_sys_admin(self):
        """是否为系统管理员"""
        return self.global_role == self.GlobalRole.SYS_ADMIN

    @property
    def is_teacher_role(self):
        """是否为小团队唯一的全局操作老师。"""
        return self.global_role == self.GlobalRole.TEACHER

    @property
    def is_operating_teacher(self):
        """显式别名：全局 ``teacher`` 代表可执行全部业务操作的老师。"""
        return self.is_teacher_role

    @property
    def is_viewing_teacher(self):
        """是否至少在一个团队中担任只读查看老师。"""
        from apps.common.team_models import TeamMember

        return TeamMember.objects.filter(
            user=self,
            role=TeamMember.Role.TEACHER,
            status__in=[
                TeamMember.Status.ACTIVE,
                TeamMember.Status.ON_LEAVE,
            ],
        ).exists()

    @property
    def is_sensitive_approver(self):
        """是否为敏感审批人"""
        return self.global_role == self.GlobalRole.SENS_APPROVER


class UserPreference(models.Model):
    """
    用户个人化偏好设置模型
    账户级的界面与行为配置，与用户一对一关联
    """

    DEFAULT_THEME = 'blue'
    DEFAULT_PRIMARY_COLOR = '#176b73'
    DEFAULT_THEME_MODE = 'system'
    DEFAULT_SCHEDULE_START = '19:00'
    DEFAULT_SCHEDULE_END = '07:00'
    DEFAULT_LANGUAGE = 'zh-CN'

    # 保留主题键以兼容旧客户端；界面实际使用受控的主色值。
    THEME_CHOICES = [
        ('blue', '蓝色'),
        ('green', '绿色'),
        ('purple', '紫色'),
        ('orange', '橙色'),
    ]
    THEME_TO_PRIMARY_COLOR = {
        'blue': DEFAULT_PRIMARY_COLOR,
        'green': '#2f6f4e',
        'purple': '#6f5a86',
        'orange': '#9a6238',
    }
    PRIMARY_COLOR_PATTERN = r'^#[0-9A-Fa-f]{6}$'
    SCHEDULE_TIME_PATTERN = r'^(?:[01]\d|2[0-3]):[0-5]\d$'

    class ThemeMode(models.TextChoices):
        LIGHT = 'light', '浅色'
        DARK = 'dark', '深色'
        SYSTEM = 'system', '跟随系统'
        SCHEDULE = 'schedule', '定时切换'

    # 默认着陆页可选项
    LANDING_CHOICES = [
        ('dashboard', '首页驾驶舱'),
        ('projects', '项目管理'),
        ('tasks', '任务管理'),
        ('notifications', '通知中心'),
    ]

    # 关联用户（一对一）
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preference',
        verbose_name='用户',
    )
    # 仪表盘布局配置（卡片排序、显隐等）
    dashboard_layout = models.JSONField('仪表盘布局', default=dict, blank=True)
    # 主题色
    theme_color = models.CharField(
        '主题色', max_length=20, choices=THEME_CHOICES, default=DEFAULT_THEME
    )
    primary_color = models.CharField(
        '界面主色',
        max_length=7,
        default=DEFAULT_PRIMARY_COLOR,
        validators=[
            RegexValidator(
                regex=PRIMARY_COLOR_PATTERN,
                message='主色必须是完整的六位十六进制颜色，例如 #176b73',
            )
        ],
    )
    theme_mode = models.CharField(
        '明暗模式',
        max_length=20,
        choices=ThemeMode.choices,
        default=DEFAULT_THEME_MODE,
    )
    schedule_start = models.CharField(
        '深色模式开始时间',
        max_length=5,
        default=DEFAULT_SCHEDULE_START,
        validators=[
            RegexValidator(
                regex=SCHEDULE_TIME_PATTERN,
                message='深色模式开始时间必须为 HH:MM 格式的有效时间',
            )
        ],
    )
    schedule_end = models.CharField(
        '深色模式结束时间',
        max_length=5,
        default=DEFAULT_SCHEDULE_END,
        validators=[
            RegexValidator(
                regex=SCHEDULE_TIME_PATTERN,
                message='深色模式结束时间必须为 HH:MM 格式的有效时间',
            )
        ],
    )
    # 默认着陆页
    default_landing = models.CharField('默认着陆页', max_length=50, default='dashboard')
    # 侧边栏默认是否折叠
    sidebar_collapsed = models.BooleanField('侧边栏默认折叠', default=False)
    # 是否开启通知声音
    notification_sound = models.BooleanField('通知声音', default=True)
    language = models.CharField(
        '界面语言',
        max_length=10,
        choices=[('zh-CN', '简体中文'), ('en', 'English')],
        default=DEFAULT_LANGUAGE,
    )
    # 每页显示条数
    items_per_page = models.IntegerField('每页显示条数', default=20)
    # 默认数据范围：优先显示与当前账户有关的数据，或显示团队全部数据
    default_scope = models.CharField(
        '默认数据范围',
        max_length=20,
        choices=[
            ('mine', '与我相关'),
            ('team', '团队全部'),
        ],
        default='mine',
    )
    # 账户级菜单顺序、常用入口及各模块保存的筛选条件
    sidebar_order = models.JSONField('侧边栏顺序', default=list, blank=True)
    favorite_routes = models.JSONField('常用入口', default=list, blank=True)
    saved_filters = models.JSONField('保存的筛选条件', default=dict, blank=True)
    # 类别/渠道、免打扰时段和摘要频率统一保存在结构化偏好中
    notification_preferences = models.JSONField('通知偏好', default=dict, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'user_preferences'
        verbose_name = '用户偏好设置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user.name} 的偏好设置'

    @classmethod
    def primary_color_for_theme(cls, theme):
        """Resolve a legacy theme key to a safe primary color."""
        return cls.THEME_TO_PRIMARY_COLOR.get(theme, cls.DEFAULT_PRIMARY_COLOR)

    @classmethod
    def theme_for_primary_color(cls, primary_color):
        """Resolve a preset primary color to its legacy theme key."""
        normalized = cls.normalize_primary_color(primary_color)
        return next(
            (
                theme
                for theme, color in cls.THEME_TO_PRIMARY_COLOR.items()
                if color == normalized
            ),
            None,
        )

    @classmethod
    def normalize_primary_color(cls, primary_color):
        if not isinstance(primary_color, str):
            return None
        if not re.fullmatch(cls.PRIMARY_COLOR_PATTERN, primary_color):
            return None
        return primary_color.lower()

    @classmethod
    def normalize_schedule_time(cls, value):
        if not isinstance(value, str):
            return None
        return value if re.fullmatch(cls.SCHEDULE_TIME_PATTERN, value) else None

    @property
    def safe_primary_color(self):
        return self.normalize_primary_color(self.primary_color) or self.DEFAULT_PRIMARY_COLOR

    def save(self, *args, **kwargs):
        if (
            self._state.adding
            and self.theme_color != self.DEFAULT_THEME
            and self.primary_color == self.DEFAULT_PRIMARY_COLOR
        ):
            self.primary_color = self.primary_color_for_theme(self.theme_color)

        errors = {}
        normalized = self.normalize_primary_color(self.primary_color)
        if normalized is None:
            errors['primary_color'] = (
                '主色必须是完整的六位十六进制颜色，例如 #176b73'
            )
        else:
            self.primary_color = normalized

        if self.theme_mode not in self.ThemeMode.values:
            errors['theme_mode'] = '明暗模式必须为 light、dark、system 或 schedule'

        for field_name in ('schedule_start', 'schedule_end'):
            value = getattr(self, field_name)
            if self.normalize_schedule_time(value) is None:
                errors[field_name] = '必须为 HH:MM 格式的有效时间'

        if (
            self.theme_mode == self.ThemeMode.SCHEDULE
            and self.schedule_start == self.schedule_end
        ):
            errors['schedule_end'] = '定时模式的开始时间和结束时间不能相同'

        if errors:
            raise ValidationError(errors)
        super().save(*args, **kwargs)


class UserLifecycleEvent(models.Model):
    """成员状态变化审计记录，离队时不删除原账户和业务历史。"""

    class EventType(models.TextChoices):
        CREATED = 'created', '加入团队'
        STATUS_CHANGED = 'status_changed', '状态变更'
        ROLE_CHANGED = 'role_changed', '全局角色变更'
        HANDOVER = 'handover', '工作交接'
        REACTIVATED = 'reactivated', '重新加入'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lifecycle_events',
        verbose_name='成员',
    )
    event_type = models.CharField('事件类型', max_length=30, choices=EventType.choices)
    from_status = models.CharField('原状态', max_length=20, blank=True, default='')
    to_status = models.CharField('新状态', max_length=20, blank=True, default='')
    from_role = models.CharField('原角色', max_length=20, blank=True, default='')
    to_role = models.CharField('新角色', max_length=20, blank=True, default='')
    reason = models.TextField('原因', blank=True, default='')
    handover_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_user_handovers',
        verbose_name='交接人',
    )
    handover_notes = models.TextField('交接说明', blank=True, default='')
    operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operated_user_lifecycle_events',
        verbose_name='操作人',
    )
    created_at = models.DateTimeField('发生时间', auto_now_add=True)

    class Meta:
        db_table = 'user_lifecycle_events'
        verbose_name = '成员生命周期记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.user.name} - {self.get_event_type_display()}'


from .skill_models import MemberSkill  # noqa: E402,F401
from .growth_models import MemberGrowth  # noqa: E402,F401
