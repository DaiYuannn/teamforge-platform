"""
知识产权管理模型
包含 5 个模型：
- IntellectualPropertyApplication: 知识产权申请档案
- IPApplicationContributor: 责任分工记录
- IPReturnRecord: 退回修改责任记录
- IPMaterialVersion: 材料与版本管理
- IPObjection: 知识产权异议
"""
from django.db import models
from django.conf import settings

from apps.projects.models import Project
from apps.files.models import FileAsset


class IntellectualPropertyApplication(models.Model):
    """
    知识产权申请档案模型
    管理软著/专利/论文等知识产权成果的全生命周期
    """

    class IPType(models.TextChoices):
        """成果类型"""
        SOFTWARE_COPYRIGHT = 'software_copyright', '软件著作权'
        INVENTION_PATENT = 'invention_patent', '发明专利'
        UTILITY_MODEL = 'utility_model', '实用新型专利'
        DESIGN_PATENT = 'design_patent', '外观设计专利'
        NOVELTY_SEARCH = 'novelty_search', '科技查新'
        PAPER = 'paper', '论文成果'
        OTHER = 'other', '其他'

    class Status(models.TextChoices):
        """申请状态"""
        DRAFT = 'draft', '准备中'
        WRITING = 'writing', '材料撰写中'
        LEADER_REVIEW = 'leader_review', '项目负责人审核中'
        TEACHER_CONFIRM = 'teacher_confirm', '老师确认中'
        RESEARCH_OFFICE_REVIEW = 'research_office_review', '科研处审核中'
        RETURNED = 'returned', '科研处退回修改'
        MODIFYING = 'modifying', '修改中'
        RESUBMITTED = 'resubmitted', '已重新提交'
        ACCEPTED = 'accepted', '已受理'
        AUTHORIZED = 'authorized', '已授权/已登记'
        ARCHIVED = 'archived', '已归档'
        PAUSED = 'paused', '暂停申请'
        TERMINATED = 'terminated', '终止申请'
        DEFERRED = 'deferred', '转为后续申请'

    # 成果名称
    title = models.CharField('成果名称', max_length=200)
    # 内部编号（唯一）
    application_code = models.CharField('内部编号', max_length=50, unique=True)
    # 成果类型
    ip_type = models.CharField(
        '成果类型',
        max_length=30,
        choices=IPType.choices,
        default=IPType.SOFTWARE_COPYRIGHT,
    )
    # 关联项目（可为空）
    related_project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name='ip_applications',
        verbose_name='关联项目',
        null=True, blank=True,
    )
    related_projects = models.ManyToManyField(
        Project,
        through='IPApplicationProjectLink',
        related_name='linked_ip_applications',
        verbose_name='关联项目',
        blank=True,
    )
    # 当前状态
    status = models.CharField(
        '当前状态',
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    # 主导撰写人
    main_writer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_main_writing',
        verbose_name='主导撰写人',
        null=True,
    )
    # 申请执行人
    applicant_executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_executing',
        verbose_name='申请执行人',
        null=True, blank=True,
    )
    # 材料整理人
    material_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_material_managing',
        verbose_name='材料整理人',
        null=True, blank=True,
    )
    # 项目负责人审核人
    project_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_reviewing',
        verbose_name='项目负责人审核人',
        null=True, blank=True,
    )
    # 老师确认人
    teacher_confirmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_confirming',
        verbose_name='老师确认人',
        null=True, blank=True,
    )
    # 开始日期
    start_date = models.DateField('开始日期', null=True, blank=True)
    # 提交日期
    submit_date = models.DateField('提交日期', null=True, blank=True)
    # 受理日期
    accepted_date = models.DateField('受理日期', null=True, blank=True)
    # 授权/登记日期
    authorized_date = models.DateField('授权/登记日期', null=True, blank=True)
    # 退回次数
    return_count = models.IntegerField('退回次数', default=0)
    # 当前问题
    current_problem = models.TextField('当前问题', blank=True, default='')
    status_note = models.TextField('状态说明', blank=True, default='')
    # 最终证书文件
    final_certificate_file = models.ForeignKey(
        FileAsset,
        on_delete=models.SET_NULL,
        related_name='ip_certificates',
        verbose_name='最终证书文件',
        null=True, blank=True,
    )
    # 成果简介
    intro = models.TextField('成果简介', blank=True, default='')
    # 创建人
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_applications_created',
        verbose_name='创建人',
        null=True,
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ip_applications'
        verbose_name = '知识产权申请'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.application_code} - {self.title}'


class IPApplicationProjectLink(models.Model):
    """一个成果可来源于或复用于多个项目。"""

    class RelationType(models.TextChoices):
        PRIMARY = 'primary', '主项目'
        SOURCE = 'source', '成果来源'
        USED_BY = 'used_by', '成果复用'

    application = models.ForeignKey(
        IntellectualPropertyApplication,
        on_delete=models.CASCADE,
        related_name='project_links',
        verbose_name='知识产权申请',
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='ip_application_links',
        verbose_name='关联项目',
    )
    relation_type = models.CharField(
        '关联类型',
        max_length=20,
        choices=RelationType.choices,
        default=RelationType.USED_BY,
    )
    note = models.TextField('关联说明', blank=True, default='')
    created_at = models.DateTimeField('关联时间', auto_now_add=True)

    class Meta:
        db_table = 'ip_application_project_links'
        verbose_name = '知识产权关联项目'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=('application', 'project'),
                name='uniq_ip_application_project',
            ),
            models.UniqueConstraint(
                fields=('application',),
                condition=models.Q(relation_type='primary'),
                name='uniq_primary_project_per_ip_application',
            ),
        ]


class IPApplicationCandidate(models.Model):
    """拟申报/实际申报名单；不保存身份证等敏感明文。"""

    class LegalRole(models.TextChoices):
        INVENTOR = 'inventor', '发明人'
        AUTHOR = 'author', '著作权人/作者'
        APPLICANT = 'applicant', '申请人'
        OTHER = 'other', '其他申报身份'

    class CandidateStatus(models.TextChoices):
        PROPOSED = 'proposed', '拟申报'
        IDENTITY_PENDING = 'identity_pending', '待身份核验'
        CONFIRMED = 'confirmed', '已确认'
        SUBMITTED = 'submitted', '已正式提交'
        WITHDRAWN = 'withdrawn', '已撤出'

    class IdentityCheckStatus(models.TextChoices):
        PENDING = 'pending', '待核验'
        MATCHED = 'matched', '姓名证件一致'
        MISMATCHED = 'mismatched', '姓名证件不一致'
        NOT_REQUIRED = 'not_required', '无需核验'

    application = models.ForeignKey(
        IntellectualPropertyApplication,
        on_delete=models.CASCADE,
        related_name='candidates',
        verbose_name='知识产权申请',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ip_candidate_records',
        verbose_name='拟申报成员',
    )
    legal_role = models.CharField(
        '申报身份',
        max_length=20,
        choices=LegalRole.choices,
        default=LegalRole.INVENTOR,
    )
    planned_order = models.PositiveIntegerField('拟署名顺序', default=1)
    status = models.CharField(
        '名单状态',
        max_length=30,
        choices=CandidateStatus.choices,
        default=CandidateStatus.PROPOSED,
        db_index=True,
    )
    identity_check_status = models.CharField(
        '身份核验状态',
        max_length=20,
        choices=IdentityCheckStatus.choices,
        default=IdentityCheckStatus.PENDING,
    )
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='checked_ip_candidates',
        verbose_name='核验人',
        null=True,
        blank=True,
    )
    checked_at = models.DateTimeField('核验时间', null=True, blank=True)
    note = models.TextField('说明', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ip_application_candidates'
        verbose_name = '知识产权拟申报名单'
        verbose_name_plural = verbose_name
        ordering = ['planned_order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=('application', 'user', 'legal_role'),
                name='uniq_ip_candidate_legal_role',
            ),
        ]


class IPApplicationContributor(models.Model):
    """
    责任分工记录模型
    记录知识产权申请中各成员的贡献角色与责任分工
    """

    class ContributorRole(models.TextChoices):
        """贡献角色"""
        MAIN_WRITER = 'main_writer', '主导撰写人'
        CO_WRITER = 'co_writer', '协作撰写人'
        CODE_PROVIDER = 'code_provider', '代码提供人'
        DOCUMENT_WRITER = 'document_writer', '文档撰写人'
        DRAWING_PROVIDER = 'drawing_provider', '图纸提供人'
        TESTER = 'tester', '测试人'
        EXECUTOR = 'executor', '申请执行人'
        MATERIAL_MANAGER = 'material_manager', '材料整理人'
        REVIEWER = 'reviewer', '审核人'

    # 所属申请
    application = models.ForeignKey(
        IntellectualPropertyApplication,
        on_delete=models.CASCADE,
        related_name='contributors',
        verbose_name='所属申请',
    )
    # 成员用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ip_contributions',
        verbose_name='成员',
    )
    # 贡献角色
    role = models.CharField(
        '贡献角色',
        max_length=30,
        choices=ContributorRole.choices,
    )
    # 贡献说明
    contribution_description = models.TextField('贡献说明', blank=True, default='')
    # 责任说明
    responsibility_description = models.TextField('责任说明', blank=True, default='')
    # 是否确认
    is_confirmed = models.BooleanField('是否确认', default=False)
    # 确认人
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_confirmations',
        verbose_name='确认人',
        null=True, blank=True,
    )
    # 确认时间
    confirmed_at = models.DateTimeField('确认时间', null=True, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ip_contributors'
        verbose_name = '知识产权责任分工'
        verbose_name_plural = verbose_name
        # 同一申请同一用户同一角色唯一
        unique_together = ('application', 'user', 'role')

    def __str__(self):
        return f'{self.application.title} - {self.user.name}({self.get_role_display()})'


class IPReturnRecord(models.Model):
    """
    退回修改责任记录模型
    记录每次申请被退回的原因、责任归属及修改情况
    """

    class ReturnSource(models.TextChoices):
        """退回来源"""
        RESEARCH_OFFICE = 'research_office', '科研处'
        SCHOOL_SYSTEM = 'school_system', '学校系统'
        AGENCY = 'agency', '代理机构'
        PATENT_PLATFORM = 'patent_platform', '专利平台'
        OTHER = 'other', '其他'

    class ResponsibilityType(models.TextChoices):
        """责任类型"""
        WRITING_PROBLEM = 'writing_problem', '撰写质量问题'
        MATERIAL_PROBLEM = 'material_problem', '材料完整性问题'
        SUBMIT_PROBLEM = 'submit_problem', '提交流程问题'
        REVIEW_PROBLEM = 'review_problem', '审核问题'
        SYSTEM_PROBLEM = 'system_problem', '系统问题'
        UNATTRIBUTABLE = 'unattributable', '无法归属'
        OTHER = 'other', '其他'

    class ReturnResult(models.TextChoices):
        """退回处理结果"""
        PENDING = 'pending', '待修改'
        MODIFIED = 'modified', '已修改'
        RESUBMITTED = 'resubmitted', '已重新提交'
        ACCEPTED = 'accepted', '已通过'
        REJECTED = 'rejected', '未通过'

    # 所属申请
    application = models.ForeignKey(
        IntellectualPropertyApplication,
        on_delete=models.CASCADE,
        related_name='return_records',
        verbose_name='所属申请',
    )
    # 退回时间
    return_time = models.DateTimeField('退回时间')
    # 退回来源
    return_source = models.CharField(
        '退回来源',
        max_length=30,
        choices=ReturnSource.choices,
        default=ReturnSource.RESEARCH_OFFICE,
    )
    # 退回原因
    return_reason = models.TextField('退回原因')
    # 责任类型
    responsibility_type = models.CharField(
        '责任类型',
        max_length=30,
        choices=ResponsibilityType.choices,
        default=ResponsibilityType.OTHER,
    )
    # 责任人
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_responsible_returns',
        verbose_name='责任人',
        null=True, blank=True,
    )
    # 指派人
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_assigned_returns',
        verbose_name='指派人',
        null=True, blank=True,
    )
    # 修改截止时间
    modify_deadline = models.DateTimeField('修改截止时间', null=True, blank=True)
    # 实际修改人
    actual_modifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_actual_modified_returns',
        verbose_name='实际修改人',
        null=True, blank=True,
    )
    # 修改说明
    modify_description = models.TextField('修改说明', blank=True, default='')
    # 处理结果
    result = models.CharField(
        '处理结果',
        max_length=20,
        choices=ReturnResult.choices,
        default=ReturnResult.PENDING,
    )
    # 证明文件
    proof_file = models.ForeignKey(
        FileAsset,
        on_delete=models.SET_NULL,
        related_name='ip_return_proofs',
        verbose_name='证明文件',
        null=True, blank=True,
    )
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ip_return_records'
        verbose_name = '退回修改记录'
        verbose_name_plural = verbose_name
        ordering = ['-return_time']

    def __str__(self):
        return f'{self.application.title} - 退回({self.return_time})'


class IPMaterialVersion(models.Model):
    """
    材料与版本管理模型
    记录申请过程中的各类材料及其版本迭代
    """

    class MaterialType(models.TextChoices):
        """材料类型"""
        APPLICATION_FORM = 'application_form', '申请表'
        MANUAL = 'manual', '软件说明书'
        SOURCE_CODE = 'source_code', '源代码文档'
        SCREENSHOT = 'screenshot', '软件截图'
        DISCLOSURE = 'disclosure', '专利交底书'
        SPECIFICATION = 'specification', '专利说明书'
        CLAIMS = 'claims', '权利要求书'
        ABSTRACT = 'abstract', '摘要'
        DRAWING = 'drawing', '附图'
        FEEDBACK = 'feedback', '科研处反馈截图'
        SYSTEM_SCREENSHOT = 'system_screenshot', '申请系统截图'
        ACCEPTANCE_NOTICE = 'acceptance_notice', '受理通知书'
        CERTIFICATE = 'certificate', '授权证书'
        ARCHIVE = 'archive', '归档材料'
        OTHER = 'other', '其他'

    # 所属申请
    application = models.ForeignKey(
        IntellectualPropertyApplication,
        on_delete=models.CASCADE,
        related_name='material_versions',
        verbose_name='所属申请',
    )
    # 关联文件资源
    file_asset = models.ForeignKey(
        FileAsset,
        on_delete=models.CASCADE,
        related_name='ip_materials',
        verbose_name='关联文件',
    )
    # 材料类型
    material_type = models.CharField(
        '材料类型',
        max_length=30,
        choices=MaterialType.choices,
        default=MaterialType.OTHER,
    )
    # 版本号
    version = models.CharField('版本号', max_length=20, default='v1')
    # 上传人
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_materials_uploaded',
        verbose_name='上传人',
        null=True,
    )
    # 修改说明
    change_note = models.TextField('修改说明', blank=True, default='')
    # 关联退回记录（该版本材料针对某次退回修改）
    related_return_record = models.ForeignKey(
        IPReturnRecord,
        on_delete=models.SET_NULL,
        related_name='materials',
        verbose_name='关联退回记录',
        null=True, blank=True,
    )
    # 是否最终版
    is_final = models.BooleanField('是否最终版', default=False)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ip_material_versions'
        verbose_name = '材料版本'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.application.title} - {self.get_material_type_display()}({self.version})'


class IPObjection(models.Model):
    """
    知识产权异议模型
    成员对申请中的贡献归属、责任认定等提出异议，经负责人初审、老师最终确认
    """

    class ObjectionType(models.TextChoices):
        """异议类型"""
        WRITING_CREDIT = 'writing_credit', '撰写贡献异议'
        EXECUTION_CREDIT = 'execution_credit', '申请执行贡献异议'
        RETURN_RESPONSIBILITY = 'return_responsibility', '退回责任异议'
        RANKING = 'ranking', '成果排序异议'
        MATERIAL_CREDIT = 'material_credit', '材料撰写异议'
        OTHER = 'other', '其他'

    class ObjectionStatus(models.TextChoices):
        """异议状态"""
        PENDING = 'pending', '待处理'
        LEADER_REVIEWED = 'leader_reviewed', '负责人已初审'
        TEACHER_CONFIRMED = 'teacher_confirmed', '老师已确认'
        RESOLVED = 'resolved', '已解决'
        REJECTED = 'rejected', '已驳回'

    # 所属申请
    application = models.ForeignKey(
        IntellectualPropertyApplication,
        on_delete=models.CASCADE,
        related_name='objections',
        verbose_name='所属申请',
    )
    # 提出人
    objector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ip_objections',
        verbose_name='提出人',
    )
    # 异议类型
    objection_type = models.CharField(
        '异议类型',
        max_length=30,
        choices=ObjectionType.choices,
        default=ObjectionType.OTHER,
    )
    # 异议内容
    content = models.TextField('异议内容')
    # 证明文件
    proof_file = models.ForeignKey(
        FileAsset,
        on_delete=models.SET_NULL,
        related_name='ip_objection_proofs',
        verbose_name='证明文件',
        null=True, blank=True,
    )
    # 处理状态
    status = models.CharField(
        '处理状态',
        max_length=30,
        choices=ObjectionStatus.choices,
        default=ObjectionStatus.PENDING,
    )
    # 负责人意见
    leader_opinion = models.TextField('负责人意见', blank=True, default='')
    # 负责人审核人
    leader_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_objection_leader_reviews',
        verbose_name='负责人审核人',
        null=True, blank=True,
    )
    # 负责人审核时间
    leader_reviewed_at = models.DateTimeField('负责人审核时间', null=True, blank=True)
    # 老师意见
    teacher_opinion = models.TextField('老师意见', blank=True, default='')
    # 老师确认人
    teacher_confirmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ip_objection_teacher_confirms',
        verbose_name='老师确认人',
        null=True, blank=True,
    )
    # 老师确认时间
    teacher_confirmed_at = models.DateTimeField('老师确认时间', null=True, blank=True)
    # 最终结果
    final_result = models.TextField('最终结果', blank=True, default='')
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ip_objections'
        verbose_name = '知识产权异议'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.application.title} - {self.objector.name}({self.get_objection_type_display()})'
