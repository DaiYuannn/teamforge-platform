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
from apps.users.models import User
from apps.common.team_models import Team, TeamMember
from common.project_access import project_can_manage
from .permissions import can_review_sensitive_data, user_can_view_sensitive_metadata


class SensitiveDataSerializer(serializers.ModelSerializer):
    """敏感数据脱敏序列化器（列表/详情默认使用，不含明文）"""
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    owner_name = serializers.CharField(source='uploader.name', read_only=True, default='')
    subject_name = serializers.CharField(source='subject_user.name', read_only=True, default='')
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
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
            'owner_name', 'subject_user', 'subject_name', 'team', 'team_name',
            'project', 'project_name',
            'masked_value', 'has_file', 'file_attachment_name',
            'key_version', 'is_encrypted', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'data_type', 'subject_user', 'team', 'project',
            'masked_value', 'has_file', 'is_encrypted',
            'key_version', 'created_at', 'updated_at',
        )

    def get_masked_value(self, obj) -> str:
        """脱敏显示：先解密再脱敏"""
        if not obj.is_encrypted or not obj.encrypted_content:
            return '***'
        try:
            plaintext = SensitiveDataService.decrypt_value(obj.encrypted_content)
            return SensitiveDataService.mask_value(obj.data_type, plaintext)
        except Exception:
            return '***'

    def get_has_file(self, obj) -> bool:
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

    def get_plaintext(self, obj) -> str:
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
    team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), required=False, allow_null=True
    )
    subject_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    file_attachment = serializers.PrimaryKeyRelatedField(
        queryset=FileAsset.objects.all(), required=False, allow_null=True
    )

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        team = attrs.get('team')
        data_type = attrs.get('data_type')
        subject_user = attrs.get('subject_user')
        project = attrs.get('project')
        file_attachment = attrs.get('file_attachment')
        personal_types = {
            SensitiveData.DataType.ID_CARD,
            SensitiveData.DataType.BANK_ACCOUNT,
            SensitiveData.DataType.PHONE,
            SensitiveData.DataType.ADDRESS,
            SensitiveData.DataType.SIGNATURE,
        }
        if data_type in personal_types and subject_user is None:
            subject_user = user
            attrs['subject_user'] = user
        if team is None:
            if Team.objects.exists():
                raise serializers.ValidationError({
                    'team': '已有团队组织时，敏感资料必须选择所属小团队'
                })
            reviewer = can_review_sensitive_data(
                user,
                SensitiveData(team=None),
            )
            if subject_user and subject_user.id != user.id and not reviewer:
                raise serializers.ValidationError({
                    'subject_user': '只有明确的敏感资料审批人可以代成员录入历史资料'
                })
        else:
            membership = TeamMember.objects.filter(
                team=team,
                user=user,
                status=TeamMember.Status.ACTIVE,
            ).first()
            if membership is None and team.owner_id != user.id:
                raise serializers.ValidationError({
                    'team': '只能向自己所在的活动团队提交敏感资料'
                })
            if subject_user and not TeamMember.objects.filter(
                team=team,
                user=subject_user,
                status=TeamMember.Status.ACTIVE,
            ).exists():
                raise serializers.ValidationError({
                    'subject_user': '资料所属成员必须是该团队的活动成员'
                })
            reviewer = can_review_sensitive_data(
                user,
                SensitiveData(team=team),
            )
            if subject_user and subject_user.id != user.id and not reviewer:
                raise serializers.ValidationError({
                    'subject_user': '只有本团队负责人或明确审批人可以代成员录入资料'
                })
        if file_attachment:
            # 绑定敏感资料会立刻把 FileAsset 提升为 sensitive 并撤销其分享链接，
            # 因此不能只验证“当前可读”。只有文件上传人或所属项目管理者可以执行
            # 这一不可逆的权限提升，避免通过猜测文件 ID 劫持其他项目文件。
            can_reclassify = (
                file_attachment.uploader_id == getattr(user, 'id', None)
                or (
                    file_attachment.project_id
                    and project_can_manage(user, file_attachment.project)
                )
            )
            if not can_reclassify:
                raise serializers.ValidationError({
                    'file_attachment': '只能绑定自己上传或自己负责项目中的文件'
                })
            if project and file_attachment.project_id != project.id:
                raise serializers.ValidationError({
                    'file_attachment': '附件必须属于所选项目'
                })
            if SensitiveData.objects.filter(
                file_attachment=file_attachment,
            ).exists():
                raise serializers.ValidationError({
                    'file_attachment': '该文件已绑定其他敏感资料'
                })
        return attrs

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
            team=validated_data.get('team'),
            subject_user=validated_data.get('subject_user'),
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
    has_attachment = serializers.SerializerMethodField()
    attachment_name = serializers.CharField(
        source='sensitive_data.file_attachment.name',
        read_only=True,
        default='',
    )
    can_download_attachment = serializers.BooleanField(read_only=True)

    class Meta:
        model = SensitiveAccessRequest
        fields = (
            'id', 'sensitive_data', 'sensitive_data_title',
            'sensitive_data_type', 'sensitive_data_type_display',
            'applicant', 'applicant_name', 'reason', 'usage_scenario',
            'project', 'project_name', 'expected_use_time',
            'request_note', 'is_download',
            'status', 'status_display', 'is_accessible',
            'has_attachment', 'attachment_name', 'can_download_attachment',
            'approver', 'approver_name', 'approval_opinion',
            'approved_at', 'access_expires_at', 'viewed_at',
            'created_at',
        )
        read_only_fields = (
            'id', 'applicant', 'status', 'approver', 'approval_opinion',
            'approved_at', 'access_expires_at', 'viewed_at', 'created_at',
        )

    def get_has_attachment(self, obj) -> bool:
        return obj.sensitive_data.file_attachment_id is not None


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
        request = self.context.get('request')
        sensitive_data = attrs.get('sensitive_data')
        if (
            request
            and request.user.is_authenticated
            and sensitive_data
            and not user_can_view_sensitive_metadata(request.user, sensitive_data)
        ):
            raise serializers.ValidationError({
                'sensitive_data': '无权申请其他团队或未授权的身份证资料。'
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
