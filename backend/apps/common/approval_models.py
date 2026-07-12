"""
审批流程模型
- ApprovalFlow: 审批流程定义
- ApprovalRequest: 审批申请

放在独立文件中，避免迁移冲突。通过 apps/common/models.py 导入。
"""
from django.db import models


class ApprovalFlow(models.Model):
    """审批流程"""

    # 流程名称
    name = models.CharField('流程名称', max_length=200)
    # 流程类型（如 leave / expense / sensitive）
    flow_type = models.CharField('流程类型', max_length=50)
    # 审批步骤（JSON 数组）
    steps = models.JSONField('审批步骤', default=list)
    # 是否启用
    is_active = models.BooleanField('启用', default=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'approval_flows'
        verbose_name = '审批流程'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}({self.flow_type})'


class ApprovalRequest(models.Model):
    """审批申请"""

    class Status(models.TextChoices):
        """审批状态"""
        PENDING = 'pending', '待审批'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'
        CANCELLED = 'cancelled', '已取消'

    # 申请人
    applicant = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='approval_requests',
        verbose_name='申请人',
    )
    # 审批流程
    flow = models.ForeignKey(
        'common.ApprovalFlow',
        on_delete=models.CASCADE,
        related_name='requests',
        verbose_name='审批流程',
    )
    # 状态
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.PENDING,
    )
    # 标题
    title = models.CharField('标题', max_length=200)
    # 申请内容
    content = models.TextField('申请内容', blank=True, default='')
    # 当前步骤
    current_step = models.IntegerField('当前步骤', default=0)
    # 元数据
    metadata = models.JSONField('元数据', default=dict, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'approval_requests'
        verbose_name = '审批申请'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title}({self.get_status_display()})'
