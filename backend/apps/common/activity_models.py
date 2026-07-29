"""
动态流（Activity Feed）模型
记录系统中各类操作动态：项目/任务/文件/评论/成员等事件。

放在独立文件中，避免迁移冲突。通过 apps/common/models.py 导入。
"""
from django.db import models
from django.conf import settings


class Activity(models.Model):
    """动态流"""

    class Type(models.TextChoices):
        """动态类型"""
        PROJECT_CREATED = 'project_created', '创建项目'
        PROJECT_UPDATED = 'project_updated', '更新项目'
        PROJECT_CLOSED = 'project_closed', '关闭项目'
        TASK_CREATED = 'task_created', '创建任务'
        TASK_COMPLETED = 'task_completed', '完成任务'
        TASK_UPDATED = 'task_updated', '更新任务'
        FILE_UPLOADED = 'file_uploaded', '上传文件'
        COMMENT_CREATED = 'comment_created', '发表评论'
        MEMBER_JOINED = 'member_joined', '成员加入'
        MEMBER_LEFT = 'member_left', '成员离开'
        COMPETITION_CREATED = 'competition_created', '创建比赛参赛条目'
        COMPETITION_UPDATED = 'competition_updated', '更新比赛参赛条目'
        COMPETITION_AWARDED = 'competition_awarded', '登记比赛获奖'
        FINANCE_EXPENSE = 'finance_expense', '登记或更新支出'
        FINANCE_PAYMENT = 'finance_payment', '完成经费付款'
        FINANCE_TRANSFER = 'finance_transfer', '登记内部资金转移'
        FINANCE_INCOME = 'finance_income', '登记或更新收入'
        IP_CREATED = 'ip_created', '创建知识产权成果'
        IP_UPDATED = 'ip_updated', '更新知识产权成果'
        IP_AUTHORIZED = 'ip_authorized', '知识产权成果授权'
        ANNOUNCEMENT_PUBLISHED = 'announcement_published', '发布公告'

    # 动态类型
    activity_type = models.CharField(
        '动态类型', max_length=50, choices=Type.choices,
    )
    # 操作人
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activities',
        verbose_name='操作人',
    )
    # 关联项目（可为空，表示全局动态）
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='activities',
        verbose_name='项目',
    )
    organization = models.ForeignKey(
        'common.Team',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name='所属实践团队',
    )
    # 目标类型（如 project / task / file 等）
    target_type = models.CharField('目标类型', max_length=50, default='')
    # 目标ID
    target_id = models.IntegerField('目标ID', null=True, blank=True)
    # 描述
    description = models.CharField('描述', max_length=500, default='')
    # 元数据（JSON）
    metadata = models.JSONField('元数据', default=dict, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'activities'
        verbose_name = '动态'
        verbose_name_plural = verbose_name
        # 按创建时间倒序，相同时间按 id 倒序保证确定性
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.get_activity_type_display()} - {self.description}'
