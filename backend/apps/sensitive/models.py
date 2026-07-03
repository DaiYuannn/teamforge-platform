"""
敏感资料模型
包含 SensitiveData（敏感数据）、SensitiveAccessRequest（访问申请）
关键：敏感资料明文绝不裸露，必须审批通过后限时查看，每次查看必须写 OperationLog
加密使用 common/encryption.py 的 FieldCipher（Fernet 加密）
"""
from django.db import models
from django.conf import settings


class SensitiveData(models.Model):
    """
    敏感数据模型
    存储加密后的敏感资料，明文不开放直接查看，需审批通过后限时查看
    """

    class DataType(models.TextChoices):
        """敏感数据类型"""
        ID_CARD = 'id_card', '身份证号'
        BANK_ACCOUNT = 'bank_account', '银行账号'
        PHONE = 'phone', '手机号'
        ADDRESS = 'address', '住址'
        SIGNATURE = 'signature', '签名'
        OTHER = 'other', '其他'

    # 数据类型
    data_type = models.CharField(
        '数据类型',
        max_length=20,
        choices=DataType.choices,
        default=DataType.OTHER,
    )
    # 数据标题（原有字段）
    title = models.CharField('数据标题', max_length=200)
    # 显示名称（新增：脱敏列表中展示的名称）
    display_name = models.CharField('显示名称', max_length=100, blank=True, default='')
    # 加密内容（使用 FieldCipher 加密存储，原有字段）
    encrypted_content = models.TextField('加密内容', blank=True, default='')
    # 加密文件路径（原有字段）
    encrypted_file_path = models.CharField('加密文件路径', max_length=500, blank=True, default='')
    # 密钥版本（新增：用于密钥轮换）
    key_version = models.IntegerField('密钥版本', default=1)
    # 附件（新增：如身份证图片等）
    file_attachment = models.ForeignKey(
        'files.FileAsset',
        on_delete=models.SET_NULL,
        related_name='sensitive_data_attachments',
        verbose_name='附件',
        null=True, blank=True,
    )
    # 关联项目（可选，原有字段）
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='sensitive_data',
        verbose_name='关联项目',
        null=True, blank=True,
    )
    # 上传人（原有字段，作为敏感资料拥有者）
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='uploaded_sensitive_data',
        verbose_name='上传人',
        null=True, blank=True,
    )
    # 是否已加密（原有字段）
    is_encrypted = models.BooleanField('已加密', default=False)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'sensitive_data'
        verbose_name = '敏感数据'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'[敏感]{self.title}'

    def encrypt_content(self, plaintext):
        """加密内容并保存"""
        from common.encryption import get_field_cipher
        cipher = get_field_cipher()
        self.encrypted_content = cipher.encrypt(plaintext)
        self.is_encrypted = True
        self.save()

    def decrypt_content(self):
        """
        解密内容
        关键：不开放明文查看，此方法仅限审批通过后内部调用
        """
        if not self.is_encrypted:
            return self.encrypted_content
        from common.encryption import get_field_cipher
        cipher = get_field_cipher()
        return cipher.decrypt(self.encrypted_content)


class SensitiveAccessRequest(models.Model):
    """
    敏感数据访问申请模型
    成员需提交访问申请，审批通过后才能在有效期内查看敏感资料明文
    状态流转：pending(待审批) -> approved(已通过)/rejected(已驳回) -> expired(已过期)
    """

    class Status(models.TextChoices):
        """审批状态"""
        PENDING = 'pending', '待审批'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'
        EXPIRED = 'expired', '已过期'

    # 关联敏感数据（原有字段）
    sensitive_data = models.ForeignKey(
        SensitiveData,
        on_delete=models.CASCADE,
        related_name='access_requests',
        verbose_name='敏感数据',
    )
    # 申请人（原有字段）
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sensitive_access_requests',
        verbose_name='申请人',
    )
    # 申请理由（原有字段）
    reason = models.TextField('申请理由')
    # 使用场景（新增）
    usage_scenario = models.TextField('使用场景', blank=True, default='')
    # 所属项目（新增）
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        related_name='sensitive_access_requests',
        verbose_name='所属项目',
        null=True, blank=True,
    )
    # 预计使用时间（新增）
    expected_use_time = models.DateTimeField('预计使用时间', null=True, blank=True)
    # 申请说明（新增）
    request_note = models.TextField('申请说明', blank=True, default='')
    # 是否需要下载（新增）
    is_download = models.BooleanField('是否需要下载', default=False)
    # 审批状态（原有字段）
    status = models.CharField(
        '审批状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # 审批人（原有字段）
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='approved_sensitive_requests',
        verbose_name='审批人',
        null=True, blank=True,
    )
    # 审批意见（原有字段，保留）
    approval_comment = models.TextField('审批意见', blank=True, default='')
    # 审批意见（新增，与 approval_comment 含义一致，新代码使用此字段）
    approval_opinion = models.TextField('审批意见', blank=True, default='')
    # 审批时间（原有字段）
    approved_at = models.DateTimeField('审批时间', null=True, blank=True)
    # 访问有效期截止（原有字段）
    access_expires_at = models.DateTimeField('访问有效期截止', null=True, blank=True)
    # 首次查看时间（新增：记录明文查看时间，用于审计）
    viewed_at = models.DateTimeField('首次查看时间', null=True, blank=True)
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'sensitive_access_requests'
        verbose_name = '敏感数据访问申请'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.applicant.name} 申请访问 {self.sensitive_data.title}'

    @property
    def is_accessible(self):
        """是否可访问（已通过且未过期）"""
        from django.utils import timezone
        if self.status != self.Status.APPROVED:
            return False
        if self.access_expires_at and timezone.now() > self.access_expires_at:
            return False
        return True
