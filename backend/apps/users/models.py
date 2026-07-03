"""
用户模型
扩展 Django AbstractUser，增加团队管理相关字段
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


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
