"""
贡献度模型
包含 Contribution（贡献记录）、MemberRanking（成员排名）、RankingObjection（排名异议）
在原有架构预留字段基础上新增审核流程、证明材料、填写人、排序草案等字段
"""
from django.db import models
from django.conf import settings

from apps.projects.models import Project


class Contribution(models.Model):
    """
    贡献记录模型
    记录成员在项目中的各类贡献（任务完成、经费管理、比赛参与、IP贡献等）
    支持项目负责人审核流程：pending -> approved/rejected
    """

    class ContributionType(models.TextChoices):
        """贡献类型（保留原有类型，并新增项目角色/阶段任务等类型）"""
        # 原有类型（IP 模块同步贡献使用，不可删除）
        TASK_COMPLETE = 'task_complete', '任务完成'
        PROJECT_LEAD = 'project_lead', '项目负责人'
        COMPETITION = 'competition', '比赛参与'
        FINANCE_MANAGE = 'finance_manage', '经费管理'
        FILE_UPLOAD = 'file_upload', '文件上传'
        IP_WRITING = 'ip_writing', '软著/专利撰写贡献'
        IP_EXECUTION = 'ip_execution', '软著/专利申请执行贡献'
        IP_RETURN_FIX = 'ip_return_fix', '软著/专利退回修改贡献'
        IP_ARCHIVE = 'ip_archive', '成果归档贡献'
        IP_MATERIAL = 'ip_material', '材料整理贡献'
        # 新增类型
        PROJECT_LEADER = 'project_leader', '项目负责人统筹'
        CORE = 'core', '核心成员'
        LONG_TERM = 'long_term', '长期贡献'
        STAGE_TASK = 'stage_task', '阶段性任务'
        RESOURCE = 'resource', '资源贡献'
        TEMPORARY_HELP = 'temporary_help', '临时协助'
        NOMINAL = 'nominal', '挂名贡献'
        EXITED_CONTRIBUTION = 'exited_contribution', '已退出成员贡献'
        OTHER = 'other', '其他'

    class Status(models.TextChoices):
        """审核状态"""
        PENDING = 'pending', '待审核'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'

    # 用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contributions',
        verbose_name='用户',
    )
    # 关联项目
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='contributions',
        verbose_name='关联项目',
        null=True, blank=True,
    )
    # 贡献类型
    contribution_type = models.CharField(
        '贡献类型',
        max_length=30,
        choices=ContributionType.choices,
        default=ContributionType.OTHER,
    )
    # 贡献描述（原有字段，IP 同步贡献使用）
    description = models.TextField('贡献描述', blank=True, default='')
    # 贡献内容（新增：手动登记的贡献内容）
    content = models.TextField('贡献内容', blank=True, default='')
    # 贡献分值（原有字段）
    score = models.DecimalField('贡献分值', max_digits=10, decimal_places=2, default=0)
    # 权重（新增：审核时由项目负责人填写的权重/分值，用于排序计算）
    weight = models.DecimalField('权重', max_digits=10, decimal_places=2, default=0)
    # 审核状态（新增）
    status = models.CharField(
        '审核状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # 关联对象ID（如任务ID、比赛ID等）
    related_object_id = models.IntegerField('关联对象ID', null=True, blank=True)
    # 统计周期
    period = models.CharField('统计周期', max_length=20, blank=True, default='')
    # 证明材料（新增）
    proof_file = models.ForeignKey(
        'files.FileAsset',
        on_delete=models.SET_NULL,
        related_name='contribution_proofs',
        verbose_name='证明材料',
        null=True, blank=True,
    )
    # 填写人（新增：可能不是贡献本人，如负责人代填）
    filled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='filled_contributions',
        verbose_name='填写人',
        null=True, blank=True,
    )
    # 审核人（新增）
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewed_contributions',
        verbose_name='审核人',
        null=True, blank=True,
    )
    # 审核时间（新增）
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    # 审核意见（新增）
    review_opinion = models.TextField('审核意见', blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'contributions'
        verbose_name = '贡献记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.name} - {self.get_contribution_type_display()}({self.weight})'


class MemberRanking(models.Model):
    """
    成员排名模型
    按项目、周期统计成员的综合贡献排名
    状态流转：draft(草案) -> confirmed(已确认，公开可见)
    """

    class Status(models.TextChoices):
        """排名状态"""
        DRAFT = 'draft', '草案'
        CONFIRMED = 'confirmed', '已确认'

    # 用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rankings',
        verbose_name='用户',
    )
    # 所属项目（新增）
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='rankings',
        verbose_name='所属项目',
        null=True, blank=True,
    )
    # 统计周期
    period = models.CharField('统计周期', max_length=20)
    # 排名状态（新增）
    status = models.CharField(
        '排名状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    # 总贡献分值
    total_score = models.DecimalField('总贡献分值', max_digits=12, decimal_places=2, default=0)
    # 排名
    rank = models.IntegerField('排名', default=0)
    # 任务完成数
    task_completed_count = models.IntegerField('任务完成数', default=0)
    # 参与项目数
    project_count = models.IntegerField('参与项目数', default=0)
    # 比赛参与数
    competition_count = models.IntegerField('比赛参与数', default=0)
    # IP 贡献数（新增）
    ip_contribution_count = models.IntegerField('IP贡献数', default=0)
    # 是否已公示（原有字段，保留）
    is_published = models.BooleanField('已公示', default=False)
    # 是否公开（新增：老师确认后置为 True，公开可见）
    is_public = models.BooleanField('是否公开', default=False)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'member_rankings'
        verbose_name = '成员排名'
        verbose_name_plural = verbose_name
        # 项目 + 用户 + 周期 唯一
        unique_together = ('project', 'user', 'period')
        ordering = ['period', 'rank']

    def __str__(self):
        return f'{self.user.name} - {self.period} 第{self.rank}名'


class RankingObjection(models.Model):
    """
    排名异议模型
    成员对排名结果提出异议，经项目负责人初审、老师最终确认
    状态流转：pending(待处理) -> leader_reviewed(负责人已初审) -> approved/rejected(老师最终确认)
    """

    class Status(models.TextChoices):
        """异议状态"""
        PENDING = 'pending', '待处理'
        LEADER_REVIEWED = 'leader_reviewed', '负责人已初审'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'

    # 关联排名
    ranking = models.ForeignKey(
        MemberRanking,
        on_delete=models.CASCADE,
        related_name='objections',
        verbose_name='关联排名',
    )
    # 提出人
    objector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ranking_objections',
        verbose_name='提出人',
    )
    # 异议内容
    content = models.TextField('异议内容')
    # 处理状态
    status = models.CharField(
        '处理状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # 处理回复（原有字段，保留）
    reply = models.TextField('处理回复', blank=True, default='')
    # 负责人初审意见（新增）
    leader_opinion = models.TextField('负责人初审意见', blank=True, default='')
    # 负责人审核人（新增）
    leader_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ranking_objection_leader_reviews',
        verbose_name='负责人审核人',
        null=True, blank=True,
    )
    # 负责人审核时间（新增）
    leader_reviewed_at = models.DateTimeField('负责人审核时间', null=True, blank=True)
    # 老师意见（新增）
    teacher_opinion = models.TextField('老师意见', blank=True, default='')
    # 老师确认人（新增）
    teacher_confirmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ranking_objection_teacher_confirms',
        verbose_name='老师确认人',
        null=True, blank=True,
    )
    # 老师确认时间（新增）
    teacher_confirmed_at = models.DateTimeField('老师确认时间', null=True, blank=True)
    # 最终结果（新增）
    final_result = models.TextField('最终结果', blank=True, default='')
    # 处理人（原有字段，保留）
    handler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='handled_objections',
        verbose_name='处理人',
        null=True, blank=True,
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ranking_objections'
        verbose_name = '排名异议'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.objector.name} 对 {self.ranking} 的异议'
