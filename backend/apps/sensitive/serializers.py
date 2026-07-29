"""
敏感资料序列化器
- SensitiveDataSerializer: 脱敏显示（owner_name, data_type, masked_value, display_name, has_file）
- SensitiveDataDetailSerializer: 完整（含明文）- 仅审批通过时使用
- SensitiveDataCreateSerializer: 创建用（加密存储）
- SensitiveAccessRequestSerializer: 完整字段
- SensitiveAccessRequestCreateSerializer: 创建用
- SensitiveAccessRequestReviewSerializer: 审核用
"""
from django.db import transaction
from rest_framework import serializers

from .models import (
    SensitiveAccessRequest,
    SensitiveData,
    SensitiveDataGrant,
    SensitiveGrantAccessLog,
)
from .services import SensitiveDataService
from apps.projects.models import Project
from apps.files.models import FileAsset
from apps.users.models import User
from apps.common.team_models import Team, TeamMember
from common.project_access import project_can_manage
from .permissions import (
    can_manage_sensitive_grants,
    can_review_sensitive_data,
    get_active_sensitive_grant,
    user_can_view_sensitive_metadata,
)


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
    can_manage_grants = serializers.SerializerMethodField()
    active_direct_grant = serializers.SerializerMethodField()

    class Meta:
        model = SensitiveData
        fields = (
            'id', 'data_type', 'data_type_display', 'title', 'display_name',
            'owner_name', 'subject_user', 'subject_name', 'team', 'team_name',
            'project', 'project_name',
            'masked_value', 'has_file', 'file_attachment_name',
            'can_manage_grants', 'active_direct_grant',
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

    def get_can_manage_grants(self, obj) -> bool:
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and can_manage_sensitive_grants(request.user, obj)
        )

    def get_active_direct_grant(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        grant = get_active_sensitive_grant(request.user, obj)
        if not grant:
            return None
        return {
            'id': grant.id,
            'can_view': grant.can_view,
            'can_download': grant.can_download,
            'purpose': grant.purpose,
            'expires_at': grant.expires_at,
        }


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
    plaintext = serializers.CharField(
        write_only=True, required=False, allow_blank=True, default=''
    )
    attachment_upload = serializers.FileField(write_only=True, required=False)
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
        attachment_upload = attrs.get('attachment_upload')
        if file_attachment and attachment_upload:
            raise serializers.ValidationError({
                'attachment_upload': '直接上传附件与选择现有文件只能使用一种方式'
            })
        if not attrs.get('plaintext') and not file_attachment and not attachment_upload:
            raise serializers.ValidationError('资料明文或附件至少填写一项')
        if attachment_upload:
            from apps.files.upload_security import validate_uploaded_material

            validate_uploaded_material(attachment_upload)
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
            reviewer = can_review_sensitive_data(
                user,
                SensitiveData(team=team),
            )
            if membership is None and team.owner_id != user.id and not reviewer:
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
            if subject_user and subject_user.id != user.id and not reviewer:
                raise serializers.ValidationError({
                    'subject_user': '只有本团队负责人或明确审批人可以代成员录入资料'
                })
        if project and team:
            from common.project_access import project_root_team_ids

            project_roots = project_root_team_ids(project)
            team_root_id = team.parent_id or team.id
            if project_roots and team_root_id not in project_roots:
                raise serializers.ValidationError({
                    'project': '所选项目与敏感资料所属团队不在同一组织'
                })
        if file_attachment:
            # 绑定敏感资料会立刻把 FileAsset 提升为 sensitive 并撤销其分享链接，
            # 因此不能只验证“当前可读”。只有文件上传人或所属项目管理者可以执行
            # 这一不可逆的权限提升，避免通过猜测文件 ID 劫持其他项目文件。
            can_reclassify = (
                file_attachment.uploader_id == getattr(user, 'id', None)
                or getattr(user, 'global_role', '') in {'sys_admin', 'teacher'}
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
            if team and file_attachment.team_id and file_attachment.team_id != team.id:
                raise serializers.ValidationError({
                    'file_attachment': '附件的指定团队与敏感资料所属团队不一致'
                })
            if SensitiveData.objects.filter(
                file_attachment=file_attachment,
            ).exists():
                raise serializers.ValidationError({
                    'file_attachment': '该文件已绑定其他敏感资料'
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """创建敏感资料（加密存储）"""
        from common.encryption import get_field_cipher
        cipher = get_field_cipher()
        plaintext = validated_data.pop('plaintext', '')
        attachment_upload = validated_data.pop('attachment_upload', None)
        encrypted = cipher.encrypt(plaintext) if plaintext else ''

        request = self.context.get('request')
        uploader = request.user if request and request.user.is_authenticated else None
        if attachment_upload is not None:
            file_attachment = FileAsset.objects.create(
                project=validated_data.get('project'),
                team=validated_data.get('team'),
                name=attachment_upload.name,
                file=attachment_upload,
                level=FileAsset.Level.SENSITIVE,
                size=attachment_upload.size,
                content_type=getattr(attachment_upload, 'content_type', '') or '',
                uploader=uploader,
            )
            validated_data['file_attachment'] = file_attachment

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


class SensitiveDataGrantSerializer(serializers.ModelSerializer):
    sensitive_data_title = serializers.CharField(
        source='sensitive_data.title', read_only=True, default=''
    )
    granted_to_name = serializers.CharField(
        source='granted_to.name', read_only=True, default=''
    )
    granted_to_email = serializers.CharField(
        source='granted_to.email', read_only=True, default=''
    )
    granted_by_name = serializers.CharField(
        source='granted_by.name', read_only=True, default=''
    )
    revoked_by_name = serializers.CharField(
        source='revoked_by.name', read_only=True, default=''
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = SensitiveDataGrant
        fields = (
            'id', 'sensitive_data', 'sensitive_data_title',
            'granted_to', 'granted_to_name', 'granted_to_email',
            'can_view', 'can_download', 'purpose', 'expires_at',
            'granted_by', 'granted_by_name', 'revoked_at',
            'revoked_by', 'revoked_by_name', 'is_active',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'sensitive_data', 'granted_by', 'revoked_at', 'revoked_by',
            'created_at', 'updated_at',
        )
        validators = []

    def validate(self, attrs):
        from django.utils import timezone

        sensitive_data = self.context.get('sensitive_data')
        request = self.context.get('request')
        granted_to = attrs.get('granted_to')
        can_view = attrs.get('can_view', True)
        can_download = attrs.get('can_download', False)
        expires_at = attrs.get('expires_at')
        if not sensitive_data or not request:
            raise serializers.ValidationError('缺少授权上下文')
        if not can_manage_sensitive_grants(request.user, sensitive_data):
            raise serializers.ValidationError('无权授权该敏感资料')
        if not can_view and not can_download:
            raise serializers.ValidationError('查看和下载权限至少选择一项')
        if can_download and not sensitive_data.file_attachment_id:
            raise serializers.ValidationError({'can_download': '该资料没有可下载附件'})
        if expires_at is None or expires_at <= timezone.now():
            raise serializers.ValidationError({'expires_at': '授权到期时间必须晚于当前时间'})
        if granted_to == request.user:
            raise serializers.ValidationError({'granted_to': '不能给自己创建直接授权'})
        if (
            not granted_to
            or not granted_to.is_active
            or granted_to.membership_status not in {'active', 'on_leave'}
        ):
            raise serializers.ValidationError({'granted_to': '被授权人必须是活动内部成员'})
        if sensitive_data.team_id and not TeamMember.objects.filter(
            team_id=sensitive_data.team_id,
            user=granted_to,
            status=TeamMember.Status.ACTIVE,
        ).exists():
            raise serializers.ValidationError({'granted_to': '只能授权给该资料所属团队的活动成员'})
        return attrs


class SensitiveGrantAccessLogSerializer(serializers.ModelSerializer):
    accessor_name = serializers.CharField(source='accessor.name', read_only=True, default='')
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = SensitiveGrantAccessLog
        fields = (
            'id', 'grant', 'sensitive_data', 'accessor', 'accessor_name',
            'action', 'action_display', 'purpose_snapshot', 'is_success',
            'detail', 'request_method', 'request_path', 'request_ip', 'accessed_at',
        )
        read_only_fields = fields


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
