"""
敏感资料序列化器
- SensitiveDataSerializer: 脱敏显示（owner_name, data_type, masked_value, display_name, has_file）
- SensitiveDataDetailSerializer: 完整（含明文）- 仅审批通过时使用
- SensitiveDataCreateSerializer: 创建用（加密存储）
- SensitiveAccessRequestSerializer: 完整字段
- SensitiveAccessRequestCreateSerializer: 创建用
- SensitiveAccessRequestReviewSerializer: 审核用
"""
from rest_framework import serializers

from .models import SensitiveData, SensitiveAccessRequest
from .services import SensitiveDataService
from apps.projects.models import Project
from apps.files.models import FileAsset


class SensitiveDataSerializer(serializers.ModelSerializer):
    """敏感数据脱敏序列化器（列表/详情默认使用，不含明文）"""
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    owner_name = serializers.CharField(source='uploader.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    # 脱敏值
    masked_value = serializers.SerializerMethodField()
    # 是否有附件
    has_file = serializers.SerializerMethodField()
    file_attachment_name = serializers.CharField(
        source='file_attachment.name', read_only=True, default=''
    )

    class Meta:
        model = SensitiveData
        fields = (
            'id', 'data_type', 'data_type_display', 'title', 'display_name',
            'owner_name', 'project', 'project_name',
            'masked_value', 'has_file', 'file_attachment_name',
            'key_version', 'is_encrypted', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'masked_value', 'has_file', 'is_encrypted',
            'key_version', 'created_at', 'updated_at',
        )

    def get_masked_value(self, obj):
        """脱敏显示：先解密再脱敏"""
        if not obj.is_encrypted or not obj.encrypted_content:
            return '***'
        try:
            plaintext = SensitiveDataService.decrypt_value(obj.encrypted_content)
            return SensitiveDataService.mask_value(obj.data_type, plaintext)
        except Exception:
            return '***'

    def get_has_file(self, obj):
        """是否有附件"""
        return obj.file_attachment_id is not None


class SensitiveDataDetailSerializer(serializers.ModelSerializer):
    """
    敏感数据完整序列化器（含明文）
    警告：仅在审批通过后限时查看时使用，绝不可用于普通列表
    """
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    owner_name = serializers.CharField(source='uploader.name', read_only=True, default='')
    plaintext = serializers.SerializerMethodField()

    class Meta:
        model = SensitiveData
        fields = (
            'id', 'data_type', 'data_type_display', 'title', 'display_name',
            'owner_name', 'plaintext', 'key_version', 'created_at',
        )
        read_only_fields = fields

    def get_plaintext(self, obj):
        """返回明文（仅在审批通过上下文中使用）"""
        if not obj.is_encrypted:
            return obj.encrypted_content
        return SensitiveDataService.decrypt_value(obj.encrypted_content)


class SensitiveDataCreateSerializer(serializers.Serializer):
    """敏感数据创建序列化器（明文加密存储）"""
    data_type = serializers.ChoiceField(choices=SensitiveData.DataType.choices)
    title = serializers.CharField(max_length=200)
    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    plaintext = serializers.CharField(write_only=True)
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), required=False, allow_null=True
    )
    file_attachment = serializers.PrimaryKeyRelatedField(
        queryset=FileAsset.objects.all(), required=False, allow_null=True
    )

    def create(self, validated_data):
        """创建敏感资料（加密存储）"""
        from common.encryption import get_field_cipher
        cipher = get_field_cipher()
        plaintext = validated_data.pop('plaintext', '')
        encrypted = cipher.encrypt(plaintext) if plaintext else ''

        request = self.context.get('request')
        uploader = request.user if request and request.user.is_authenticated else None

        sensitive = SensitiveData.objects.create(
            data_type=validated_data.get('data_type'),
            title=validated_data.get('title'),
            display_name=validated_data.get('display_name') or validated_data.get('title'),
            encrypted_content=encrypted,
            is_encrypted=bool(plaintext),
            key_version=1,
            file_attachment=validated_data.get('file_attachment'),
            project=validated_data.get('project'),
            uploader=uploader,
        )
        return sensitive


class SensitiveAccessRequestSerializer(serializers.ModelSerializer):
    """访问申请完整序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    applicant_name = serializers.CharField(source='applicant.name', read_only=True, default='')
    approver_name = serializers.CharField(source='approver.name', read_only=True, default='')
    sensitive_data_title = serializers.CharField(
        source='sensitive_data.title', read_only=True, default=''
    )
    sensitive_data_type = serializers.CharField(
        source='sensitive_data.data_type', read_only=True, default=''
    )
    sensitive_data_type_display = serializers.CharField(
        source='sensitive_data.get_data_type_display', read_only=True, default=''
    )
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    is_accessible = serializers.BooleanField(read_only=True)

    class Meta:
        model = SensitiveAccessRequest
        fields = (
            'id', 'sensitive_data', 'sensitive_data_title',
            'sensitive_data_type', 'sensitive_data_type_display',
            'applicant', 'applicant_name', 'reason', 'usage_scenario',
            'project', 'project_name', 'expected_use_time',
            'request_note', 'is_download',
            'status', 'status_display', 'is_accessible',
            'approver', 'approver_name', 'approval_opinion',
            'approved_at', 'access_expires_at', 'viewed_at',
            'created_at',
        )
        read_only_fields = (
            'id', 'applicant', 'status', 'approver', 'approval_opinion',
            'approved_at', 'access_expires_at', 'viewed_at', 'created_at',
        )


class SensitiveAccessRequestCreateSerializer(serializers.ModelSerializer):
    """访问申请创建序列化器"""
    # reason 不再必填，从 usage_scenario 自动填充
    reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = SensitiveAccessRequest
        fields = (
            'id', 'sensitive_data', 'reason', 'usage_scenario',
            'project', 'expected_use_time', 'is_download', 'request_note',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        """如果 reason 为空但 usage_scenario 有值，自动填充"""
        reason = attrs.get('reason', '')
        usage_scenario = attrs.get('usage_scenario', '')
        if not reason and usage_scenario:
            attrs['reason'] = usage_scenario
        elif not reason and not usage_scenario:
            raise serializers.ValidationError({
                'usage_scenario': '请填写使用场景或申请理由。'
            })
        return attrs

    def create(self, validated_data):
        """创建申请时自动设置申请人"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['applicant'] = request.user
        return super().create(validated_data)


class SensitiveAccessRequestReviewSerializer(serializers.Serializer):
    """访问申请审核序列化器"""
    # 审批动作：approve/reject
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    # 审批意见
    approval_opinion = serializers.CharField(required=False, allow_blank=True, default='')
    # 有效期小时数（approve 时有效，默认1小时）
    expire_hours = serializers.IntegerField(required=False, default=1, min_value=0, max_value=24)

    def validate(self, attrs):
        """reject 时 expire_hours 可为 0"""
        action = attrs.get('action')
        expire_hours = attrs.get('expire_hours', 1)
        if action == 'approve' and expire_hours < 1:
            raise serializers.ValidationError({
                'expire_hours': '审批通过时有效期必须大于0小时。'
            })
        return attrs
