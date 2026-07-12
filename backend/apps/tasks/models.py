"""
任务模型
包含 Task（任务）和 TaskLog（任务状态变更日志）
关键：任务完成情况对所有认证用户可见
"""
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.projects.models import Project
from apps.common.soft_delete import SoftDeleteMixin, SoftDeleteManager


class Task(SoftDeleteMixin, models.Model):
    """
    任务模型
    支持任务分配、协作者、审核、状态流转等
    支持软删除（回收站）：删除后进入回收站，可恢复或永久删除
    """

    # 默认管理器：仅返回未软删除的任务；回收站请使用 all_objects
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Status(models.TextChoices):
        """任务状态"""
        TODO = 'todo', '待办'
        DOING = 'doing', '进行中'
        PENDING_REVIEW = 'pending_review', '待审核'
        DONE = 'done', '已完成'
        OVERDUE = 'overdue', '已逾期'
        PAUSED = 'paused', '暂停'
        CANCELLED = 'cancelled', '已取消'
        NEED_HELP = 'need_help', '需要帮助'

    class Priority(models.TextChoices):
        """任务优先级"""
        LOW = 'low', '低'
        MEDIUM = 'medium', '中'
        HIGH = 'high', '高'
        URGENT = 'urgent', '紧急'

    # 所属项目
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='所属项目',
    )
    # 任务标题
    title = models.CharField('任务标题', max_length=200)
    # 指派给（负责人）
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assigned_tasks',
        verbose_name='指派给',
    )
    # 创建者
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_tasks',
        verbose_name='创建者',
        null=True, blank=True,
    )
    # 协作者（多人）
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='collaborating_tasks',
        verbose_name='协作者',
        blank=True,
    )
    # 任务描述
    description = models.TextField('任务描述', blank=True, default='')
    # 截止时间
    deadline = models.DateTimeField('截止时间', null=True, blank=True)
    # 开始时间
    start_date = models.DateTimeField('开始时间', null=True, blank=True)
    # 任务优先级
    priority = models.CharField(
        '优先级',
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    # 任务状态
    status = models.CharField(
        '任务状态',
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    # 完成时间
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    # 是否已逾期提醒
    overdue_reminded = models.BooleanField('已逾期提醒', default=False)
    # 延期原因
    delay_reason = models.TextField('延期原因', blank=True, default='')
    # 审核人
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewing_tasks',
        verbose_name='审核人',
        null=True, blank=True,
    )
    # 附件（JSON格式存储文件信息）
    attachments = models.TextField('附件', blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'tasks'
        verbose_name = '任务'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title}({self.get_status_display()})'

    @property
    def is_overdue(self):
        """是否已逾期：截止时间已过且未完成"""
        if self.deadline and self.status not in (
            self.Status.DONE, self.Status.CANCELLED
        ):
            return timezone.now() > self.deadline
        return False


class TaskLog(models.Model):
    """
    任务状态变更日志
    记录任务状态流转的历史
    """

    # 关联任务
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='status_logs',
        verbose_name='关联任务',
    )
    # 原状态
    from_status = models.CharField(
        '原状态', max_length=20,
        choices=Task.Status.choices,
        blank=True, default='',
    )
    # 目标状态
    to_status = models.CharField(
        '目标状态', max_length=20,
        choices=Task.Status.choices,
    )
    # 操作人
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='task_operations',
        verbose_name='操作人',
        null=True, blank=True,
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'task_logs'
        verbose_name = '任务日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.task.title}: {self.from_status} -> {self.to_status}'


from .subtask_models import SubTask  # noqa: E402,F401
from .dependency_models import TaskDependency  # noqa: E402,F401
from .comment_models import TaskComment  # noqa: E402,F401
