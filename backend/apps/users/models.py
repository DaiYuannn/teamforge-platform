"""
用户模型
扩展 Django AbstractUser，增加团队管理相关字段
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

# 导入分散在独立文件中的模型，使 Django 迁移系统能检测到它们
from .two_factor_models import TwoFactorSecret  # noqa: F401
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
        TEACHER = 'teacher', '老师'
        MEMBER = 'member', '普通成员'
        SENS_APPROVER = 'sens_approver', '敏感审批人'

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

    # 使用 email 作为登录字段
    USERNAME_FIELD = 'email'
    # 创建超级用户时需要填写的字段
    REQUIRED_FIELDS = ['username', 'name']

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.name}({self.email})'

    @property
    def is_sys_admin(self):
        """是否为系统管理员"""
        return self.global_role == self.GlobalRole.SYS_ADMIN

    @property
    def is_teacher_role(self):
        """是否为老师"""
        return self.global_role == self.GlobalRole.TEACHER

    @property
    def is_sensitive_approver(self):
        """是否为敏感审批人"""
        return self.global_role == self.GlobalRole.SENS_APPROVER


class UserPreference(models.Model):
    """
    用户个人化偏好设置模型
    账户级的界面与行为配置，与用户一对一关联
    """

    # 主题色可选项
    THEME_CHOICES = [
        ('blue', '蓝色'),
        ('green', '绿色'),
        ('purple', '紫色'),
        ('orange', '橙色'),
    ]

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
    theme_color = models.CharField('主题色', max_length=20, default='blue')
    # 默认着陆页
    default_landing = models.CharField('默认着陆页', max_length=50, default='dashboard')
    # 侧边栏默认是否折叠
    sidebar_collapsed = models.BooleanField('侧边栏默认折叠', default=False)
    # 是否开启通知声音
    notification_sound = models.BooleanField('通知声音', default=True)
    # 每页显示条数
    items_per_page = models.IntegerField('每页显示条数', default=20)
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


from .skill_models import MemberSkill  # noqa: E402,F401
from .growth_models import MemberGrowth  # noqa: E402,F401
