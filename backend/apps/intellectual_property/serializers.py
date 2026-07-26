"""
知识产权管理序列化器
"""
from pathlib import Path

from django.db import transaction
from rest_framework import serializers

from .models import (
    IntellectualPropertyApplication,
    IPApplicationContributor,
    IPReturnRecord,
    IPMaterialVersion,
    IPObjection,
)
from apps.users.serializers import UserListSerializer


def _request_user(serializer):
    request = serializer.context.get('request')
    if request and request.user.is_authenticated:
        return request.user
    return None


def _create_internal_file_asset(application, uploaded_file, uploader):
    """Store an IP upload as an internal file linked to the same project."""
    from apps.files.models import FileAsset

    return FileAsset.objects.create(
        project=application.related_project,
        name=Path((uploaded_file.name or '').replace('\\', '/')).name[:255],
        file=uploaded_file,
        level=FileAsset.Level.INTERNAL,
        size=uploaded_file.size,
        content_type=getattr(uploaded_file, 'content_type', '') or '',
        uploader=uploader,
    )


def _validate_file_project(file_asset, application, field_name):
    if file_asset and file_asset.project_id != application.related_project_id:
        raise serializers.ValidationError({
            field_name: '文件必须属于知识产权申请关联的同一项目'
        })


def _validate_project_participant(application, user, field_name='user'):
    """Ensure an assigned member belongs to the application's project."""
    project = application.related_project
    if user is None:
        return
    if (
        not user.is_active
        or user.membership_status not in ('active', 'on_leave')
    ):
        raise serializers.ValidationError({
            field_name: '所选用户必须是在队或暂离的有效团队成员'
        })
    if project is None:
        return
    if project.leader_id == user.id:
        return

    from apps.projects.models import ProjectMember
    if not ProjectMember.objects.filter(
        project=project, user=user, status=ProjectMember.Status.ACTIVE
    ).exists():
        raise serializers.ValidationError({field_name: '所选用户不是关联项目成员'})


def _validate_application_roles(attrs, instance=None):
    application = instance
    project = attrs.get(
        'related_project',
        getattr(application, 'related_project', None) if application else None,
    )

    class ApplicationProjectProxy:
        related_project = project

    proxy = ApplicationProjectProxy()
    for field_name in ('main_writer', 'applicant_executor', 'material_manager'):
        if instance is not None and 'related_project' not in attrs and field_name not in attrs:
            continue
        user = attrs.get(field_name, getattr(application, field_name, None) if application else None)
        _validate_project_participant(proxy, user, field_name)

    validate_reviewer = (
        instance is None
        or 'related_project' in attrs
        or 'project_reviewer' in attrs
    )
    reviewer = attrs.get(
        'project_reviewer',
        getattr(application, 'project_reviewer', None) if application else None,
    )
    if validate_reviewer and reviewer:
        _validate_project_participant(proxy, reviewer, 'project_reviewer')
        if project is None:
            raise serializers.ValidationError({
                'project_reviewer': '未关联项目时不能指定项目负责人审核人'
            })
        if reviewer.id != project.leader_id:
            raise serializers.ValidationError({
                'project_reviewer': '项目负责人审核人必须是关联项目负责人'
            })

    validate_confirmer = (
        instance is None
        or 'related_project' in attrs
        or 'teacher_confirmer' in attrs
    )
    confirmer = attrs.get(
        'teacher_confirmer',
        getattr(application, 'teacher_confirmer', None) if application else None,
    )
    if validate_confirmer and confirmer:
        if (
            not confirmer.is_active
            or confirmer.membership_status not in ('active', 'on_leave')
        ):
            raise serializers.ValidationError({
                'teacher_confirmer': '老师确认人必须是有效团队成员'
            })
        if confirmer.global_role not in ('teacher', 'sys_admin'):
            raise serializers.ValidationError({
                'teacher_confirmer': '老师确认人必须是老师或系统管理员'
            })


MAX_CERTIFICATE_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_CERTIFICATE_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
ALLOWED_CERTIFICATE_CONTENT_TYPES = {
    'application/pdf',
    'image/png',
    'image/jpeg',
}


def _validate_certificate_upload(upload):
    """Validate a final certificate before it becomes an internal FileAsset."""
    if upload is None:
        return
    extension = Path(upload.name or '').suffix.lower()
    if extension not in ALLOWED_CERTIFICATE_EXTENSIONS:
        raise serializers.ValidationError({
            'final_certificate_upload': '最终证书仅支持 PDF、PNG、JPG 或 JPEG 文件'
        })
    if upload.size > MAX_CERTIFICATE_UPLOAD_SIZE:
        raise serializers.ValidationError({
            'final_certificate_upload': '最终证书文件不能超过 20MB'
        })
    content_type = (getattr(upload, 'content_type', '') or '').lower()
    if content_type and content_type not in ALLOWED_CERTIFICATE_CONTENT_TYPES:
        raise serializers.ValidationError({
            'final_certificate_upload': '最终证书文件类型与扩展名不匹配'
        })
    try:
        position = upload.tell()
        header = upload.read(12)
        upload.seek(position)
    except (AttributeError, OSError):
        header = b''
    signature_matches = (
        (extension == '.pdf' and header.startswith(b'%PDF-'))
        or (extension == '.png' and header.startswith(b'\x89PNG\r\n\x1a\n'))
        or (
            extension in {'.jpg', '.jpeg'}
            and header.startswith(b'\xff\xd8\xff')
        )
    )
    if not signature_matches:
        raise serializers.ValidationError({
            'final_certificate_upload': '最终证书文件内容与扩展名不匹配'
        })


# ============ 责任分工 ============

class IPApplicationContributorSerializer(serializers.ModelSerializer):
    """责任分工完整序列化器"""
    user_detail = UserListSerializer(source='user', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.name', read_only=True, default='')

    class Meta:
        model = IPApplicationContributor
        fields = (
            'id', 'application', 'user', 'user_detail', 'role', 'role_display',
            'contribution_description', 'responsibility_description',
            'is_confirmed', 'confirmed_by', 'confirmed_by_name', 'confirmed_at',
            'created_at',
        )
        read_only_fields = ('id', 'is_confirmed', 'confirmed_by', 'confirmed_at', 'created_at')

    def validate(self, attrs):
        application = attrs.get('application', getattr(self.instance, 'application', None))
        if self.instance and 'application' in attrs:
            if attrs['application'].pk != self.instance.application_id:
                raise serializers.ValidationError({'application': '责任分工所属申请不可变更'})
        if application:
            contributor = attrs.get('user', getattr(self.instance, 'user', None))
            _validate_project_participant(application, contributor)
        return attrs

    def update(self, instance, validated_data):
        confirmation_fields = (
            'user', 'role', 'contribution_description', 'responsibility_description'
        )
        changed = any(
            field_name in validated_data
            and getattr(instance, f'{field_name}_id', getattr(instance, field_name, None))
            != (
                validated_data[field_name].id
                if field_name == 'user'
                else validated_data[field_name]
            )
            for field_name in confirmation_fields
        )
        contributor = super().update(instance, validated_data)
        if changed and contributor.is_confirmed:
            contributor.is_confirmed = False
            contributor.confirmed_by = None
            contributor.confirmed_at = None
            contributor.save(update_fields=[
                'is_confirmed', 'confirmed_by', 'confirmed_at'
            ])
        return contributor


# ============ 退回修改记录 ============

class IPReturnRecordSerializer(serializers.ModelSerializer):
    """退回修改记录完整序列化器"""
    return_source_display = serializers.CharField(source='get_return_source_display', read_only=True)
    responsibility_type_display = serializers.CharField(
        source='get_responsibility_type_display', read_only=True
    )
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    responsible_user_name = serializers.CharField(
        source='responsible_user.name', read_only=True, default=''
    )
    assigned_by_name = serializers.CharField(source='assigned_by.name', read_only=True, default='')
    actual_modifier_name = serializers.CharField(
        source='actual_modifier.name', read_only=True, default=''
    )

    class Meta:
        model = IPReturnRecord
        fields = (
            'id', 'application', 'return_time', 'return_source', 'return_source_display',
            'return_reason', 'responsibility_type', 'responsibility_type_display',
            'responsible_user', 'responsible_user_name', 'assigned_by', 'assigned_by_name',
            'modify_deadline', 'actual_modifier', 'actual_modifier_name',
            'modify_description', 'result', 'result_display',
            'proof_file', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'application', 'assigned_by', 'actual_modifier', 'result',
            'created_at', 'updated_at',
        )

    def validate(self, attrs):
        application = self.instance.application
        responsible_user = attrs.get('responsible_user', self.instance.responsible_user)
        _validate_project_participant(application, responsible_user, 'responsible_user')
        _validate_file_project(attrs.get('proof_file'), application, 'proof_file')
        return attrs


class IPReturnRecordCreateSerializer(serializers.ModelSerializer):
    """退回修改记录创建序列化器"""

    class Meta:
        model = IPReturnRecord
        fields = (
            'id', 'application', 'return_time', 'return_source', 'return_reason',
            'responsibility_type', 'responsible_user', 'assigned_by',
            'modify_deadline', 'proof_file',
        )
        read_only_fields = ('id', 'assigned_by')

    def validate(self, attrs):
        application = attrs['application']
        _validate_project_participant(
            application, attrs.get('responsible_user'), 'responsible_user'
        )
        _validate_file_project(attrs.get('proof_file'), application, 'proof_file')
        return attrs


class IPReturnResolveSerializer(serializers.Serializer):
    """Validate completion of a pending return modification."""
    modify_description = serializers.CharField(allow_blank=False)
    result = serializers.ChoiceField(
        choices=(
            IPReturnRecord.ReturnResult.MODIFIED,
            IPReturnRecord.ReturnResult.RESUBMITTED,
        ),
        default=IPReturnRecord.ReturnResult.MODIFIED,
    )


# ============ 材料版本 ============

class IPMaterialVersionSerializer(serializers.ModelSerializer):
    """材料版本完整序列化器"""
    material_type_display = serializers.CharField(
        source='get_material_type_display', read_only=True
    )
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True, default='')
    file_asset_name = serializers.CharField(source='file_asset.name', read_only=True, default='')
    material_upload = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = IPMaterialVersion
        fields = (
            'id', 'application', 'file_asset', 'file_asset_name', 'material_upload',
            'material_type', 'material_type_display', 'version',
            'uploaded_by', 'uploaded_by_name', 'change_note',
            'related_return_record', 'is_final', 'created_at',
        )
        read_only_fields = ('id', 'application', 'uploaded_by', 'created_at')
        extra_kwargs = {'file_asset': {'required': False}}

    def validate(self, attrs):
        upload = attrs.get('material_upload')
        file_asset = attrs.get('file_asset')
        if upload and file_asset:
            raise serializers.ValidationError(
                'material_upload 与 file_asset 只能提交其中一个'
            )
        if not upload and not file_asset and not self.instance.file_asset_id:
            raise serializers.ValidationError({'material_upload': '请上传材料文件'})

        application = self.instance.application
        _validate_file_project(file_asset, application, 'file_asset')
        related_return = attrs.get(
            'related_return_record', self.instance.related_return_record
        )
        if related_return and related_return.application_id != application.id:
            raise serializers.ValidationError({
                'related_return_record': '退回记录必须属于同一知识产权申请'
            })
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        upload = validated_data.pop('material_upload', None)
        material = super().update(instance, validated_data)
        if upload:
            material.file_asset = _create_internal_file_asset(
                material.application, upload, _request_user(self)
            )
            material.save(update_fields=['file_asset'])
        return material


class IPMaterialVersionCreateSerializer(serializers.ModelSerializer):
    """材料版本创建序列化器"""
    material_upload = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = IPMaterialVersion
        fields = (
            'id', 'application', 'file_asset', 'material_upload', 'material_type', 'version',
            'change_note', 'related_return_record', 'is_final',
        )
        read_only_fields = ('id',)
        extra_kwargs = {'file_asset': {'required': False}}

    def validate(self, attrs):
        application = attrs['application']
        upload = attrs.get('material_upload')
        file_asset = attrs.get('file_asset')
        if bool(upload) == bool(file_asset):
            raise serializers.ValidationError(
                '必须且只能提交 material_upload 或 file_asset 其中一个'
            )
        _validate_file_project(file_asset, application, 'file_asset')
        related_return = attrs.get('related_return_record')
        if related_return and related_return.application_id != application.id:
            raise serializers.ValidationError({
                'related_return_record': '退回记录必须属于同一知识产权申请'
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        upload = validated_data.pop('material_upload', None)
        if upload:
            validated_data['file_asset'] = _create_internal_file_asset(
                validated_data['application'], upload, _request_user(self)
            )
        return super().create(validated_data)


# ============ 异议 ============

class IPObjectionSerializer(serializers.ModelSerializer):
    """异议完整序列化器"""
    objection_type_display = serializers.CharField(
        source='get_objection_type_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    objector_detail = UserListSerializer(source='objector', read_only=True)
    leader_reviewer_name = serializers.CharField(
        source='leader_reviewer.name', read_only=True, default=''
    )
    teacher_confirmer_name = serializers.CharField(
        source='teacher_confirmer.name', read_only=True, default=''
    )
    proof_upload = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = IPObjection
        fields = (
            'id', 'application', 'objector', 'objector_detail',
            'objection_type', 'objection_type_display', 'content', 'proof_file',
            'proof_upload',
            'status', 'status_display',
            'leader_opinion', 'leader_reviewer', 'leader_reviewer_name', 'leader_reviewed_at',
            'teacher_opinion', 'teacher_confirmer', 'teacher_confirmer_name',
            'teacher_confirmed_at', 'final_result',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'application', 'objector', 'status', 'leader_opinion', 'leader_reviewer',
            'leader_reviewed_at', 'teacher_opinion', 'teacher_confirmer',
            'teacher_confirmed_at', 'final_result', 'created_at', 'updated_at',
        )

    def validate(self, attrs):
        application = self.instance.application
        upload = attrs.get('proof_upload')
        proof_file = attrs.get('proof_file')
        if upload and proof_file:
            raise serializers.ValidationError(
                'proof_upload 与 proof_file 只能提交其中一个'
            )
        _validate_file_project(proof_file, application, 'proof_file')
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        upload = validated_data.pop('proof_upload', None)
        objection = super().update(instance, validated_data)
        if upload:
            objection.proof_file = _create_internal_file_asset(
                objection.application, upload, _request_user(self)
            )
            objection.save(update_fields=['proof_file', 'updated_at'])
        return objection


class IPObjectionCreateSerializer(serializers.ModelSerializer):
    """异议创建序列化器"""
    proof_upload = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = IPObjection
        fields = (
            'id', 'application', 'objection_type', 'content', 'proof_file',
            'proof_upload',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        upload = attrs.get('proof_upload')
        proof_file = attrs.get('proof_file')
        if upload and proof_file:
            raise serializers.ValidationError(
                'proof_upload 与 proof_file 只能提交其中一个'
            )
        _validate_file_project(proof_file, attrs['application'], 'proof_file')
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """创建异议时自动设置提出人"""
        proof_upload = validated_data.pop('proof_upload', None)
        user = _request_user(self)
        if user:
            validated_data['objector'] = user
        if proof_upload:
            validated_data['proof_file'] = _create_internal_file_asset(
                validated_data['application'], proof_upload, user
            )
        return super().create(validated_data)


class IPObjectionReviewSerializer(serializers.Serializer):
    """
    异议处理序列化器
    - 负责人初审：填写 leader_opinion，状态置为 leader_reviewed
    - 老师最终确认：填写 teacher_opinion、final_result，状态置为 resolved/rejected
    """
    # 处理动作：leader_review（负责人初审）/ teacher_confirm（老师确认）
    action = serializers.ChoiceField(choices=['leader_review', 'teacher_confirm'])
    # 负责人意见
    leader_opinion = serializers.CharField(required=False, allow_blank=True, default='')
    # 老师意见
    teacher_opinion = serializers.CharField(required=False, allow_blank=True, default='')
    # 最终结果
    final_result = serializers.CharField(required=False, allow_blank=True, default='')
    # 最终状态：resolved（已解决）/ rejected（已驳回），老师确认时必填
    final_status = serializers.ChoiceField(
        choices=['resolved', 'rejected'], required=False
    )

    def validate(self, attrs):
        """校验处理动作对应的必填字段"""
        action = attrs.get('action')
        if action == 'leader_review':
            if not attrs.get('leader_opinion'):
                raise serializers.ValidationError({'leader_opinion': '负责人初审需填写意见'})
        elif action == 'teacher_confirm':
            if not attrs.get('final_status'):
                raise serializers.ValidationError({'final_status': '老师确认需指定最终状态'})
        return attrs


# ============ 知识产权申请 ============

class IPApplicationListSerializer(serializers.ModelSerializer):
    """
    申请列表精简序列化器（公开字段）
    所有登录成员可见
    """
    ip_type_display = serializers.CharField(source='get_ip_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    related_project_name = serializers.CharField(
        source='related_project.name', read_only=True, default=''
    )
    main_writer_name = serializers.CharField(source='main_writer.name', read_only=True, default='')
    applicant_executor_name = serializers.CharField(
        source='applicant_executor.name', read_only=True, default=''
    )

    class Meta:
        model = IntellectualPropertyApplication
        fields = (
            'id', 'title', 'application_code', 'ip_type', 'ip_type_display',
            'related_project', 'related_project_name', 'status', 'status_display',
            'main_writer', 'main_writer_name',
            'applicant_executor', 'applicant_executor_name',
            'return_count', 'created_at', 'updated_at',
        )
        read_only_fields = fields


class IPApplicationDetailSerializer(serializers.ModelSerializer):
    """
    申请详情完整序列化器
    完整字段 + 责任分工/退回记录/材料版本嵌套
    """
    ip_type_display = serializers.CharField(source='get_ip_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    related_project_name = serializers.CharField(
        source='related_project.name', read_only=True, default=''
    )
    main_writer_detail = UserListSerializer(source='main_writer', read_only=True)
    applicant_executor_detail = UserListSerializer(source='applicant_executor', read_only=True)
    material_manager_detail = UserListSerializer(source='material_manager', read_only=True)
    project_reviewer_detail = UserListSerializer(source='project_reviewer', read_only=True)
    teacher_confirmer_detail = UserListSerializer(source='teacher_confirmer', read_only=True)
    final_certificate_file_name = serializers.CharField(
        source='final_certificate_file.name', read_only=True, default=''
    )
    created_by_name = serializers.CharField(source='created_by.name', read_only=True, default='')
    contributors = IPApplicationContributorSerializer(many=True, read_only=True)
    return_records = IPReturnRecordSerializer(many=True, read_only=True)
    material_versions = IPMaterialVersionSerializer(many=True, read_only=True)
    objections = IPObjectionSerializer(many=True, read_only=True)

    class Meta:
        model = IntellectualPropertyApplication
        fields = (
            'id', 'title', 'application_code', 'ip_type', 'ip_type_display',
            'related_project', 'related_project_name', 'status', 'status_display',
            'main_writer', 'main_writer_detail',
            'applicant_executor', 'applicant_executor_detail',
            'material_manager', 'material_manager_detail',
            'project_reviewer', 'project_reviewer_detail',
            'teacher_confirmer', 'teacher_confirmer_detail',
            'start_date', 'submit_date', 'accepted_date', 'authorized_date',
            'return_count', 'current_problem',
            'final_certificate_file', 'final_certificate_file_name', 'intro',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'contributors', 'return_records', 'material_versions', 'objections',
        )
        read_only_fields = (
            'id', 'return_count', 'created_by', 'created_at', 'updated_at',
        )


class IPApplicationCreateSerializer(serializers.ModelSerializer):
    """申请创建序列化器"""

    class Meta:
        model = IntellectualPropertyApplication
        fields = (
            'id', 'title', 'application_code', 'ip_type',
            'related_project', 'main_writer', 'applicant_executor',
            'material_manager', 'project_reviewer', 'teacher_confirmer',
            'start_date', 'current_problem', 'intro',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        """创建申请时自动设置创建人"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        project = validated_data.get('related_project')
        if project and not validated_data.get('project_reviewer'):
            validated_data['project_reviewer'] = project.leader
        return super().create(validated_data)

    def validate(self, attrs):
        _validate_application_roles(attrs)
        return attrs


class IPApplicationUpdateSerializer(serializers.ModelSerializer):
    """申请更新序列化器"""
    final_certificate_upload = serializers.FileField(
        write_only=True, required=False
    )

    class Meta:
        model = IntellectualPropertyApplication
        fields = (
            'id', 'title', 'application_code', 'ip_type', 'related_project',
            'main_writer', 'applicant_executor', 'material_manager',
            'project_reviewer', 'teacher_confirmer',
            'start_date', 'submit_date', 'accepted_date', 'authorized_date',
            'current_problem', 'final_certificate_file',
            'final_certificate_upload', 'intro',
        )
        read_only_fields = ('id', 'submit_date', 'accepted_date', 'authorized_date')

    def validate(self, attrs):
        user = _request_user(self)
        instance = self.instance
        target_project = attrs.get('related_project', instance.related_project)
        certificate_upload = attrs.get('final_certificate_upload')
        submitted_certificate = attrs.get('final_certificate_file')

        if certificate_upload and submitted_certificate:
            raise serializers.ValidationError(
                'final_certificate_upload 与 final_certificate_file 只能提交其中一个'
            )
        _validate_certificate_upload(certificate_upload)

        if 'related_project' in attrs and attrs['related_project'] != instance.related_project:
            if user and user.global_role not in ('sys_admin', 'teacher'):
                if target_project is None or target_project.leader_id != user.id:
                    raise serializers.ValidationError({
                        'related_project': '只能将申请关联到自己负责的项目'
                    })

        can_manage_roles = (
            user
            and (
                user.global_role in ('sys_admin', 'teacher')
                or (
                    instance.related_project
                    and instance.related_project.leader_id == user.id
                )
            )
        )
        governed_fields = (
            'related_project', 'main_writer', 'applicant_executor',
            'material_manager', 'project_reviewer', 'teacher_confirmer',
        )
        if not can_manage_roles:
            for field_name in governed_fields:
                if field_name not in attrs:
                    continue
                current_id = getattr(instance, f'{field_name}_id')
                new_value = attrs[field_name]
                new_id = new_value.id if new_value else None
                if current_id != new_id:
                    raise serializers.ValidationError({
                        field_name: '仅项目负责人、老师或管理员可调整职责分配'
                    })

        _validate_application_roles(attrs, instance)
        certificate = None if certificate_upload else (
            submitted_certificate
            if 'final_certificate_file' in attrs
            else instance.final_certificate_file
        )
        validate_certificate_reference = (
            'final_certificate_file' in attrs or 'related_project' in attrs
        )
        if certificate and validate_certificate_reference:
            class ApplicationProjectProxy:
                related_project = target_project
            _validate_file_project(
                certificate, ApplicationProjectProxy(), 'final_certificate_file'
            )
            if certificate.level != certificate.Level.INTERNAL:
                raise serializers.ValidationError({
                    'final_certificate_file': '最终证书必须使用内部文件'
                })
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        certificate_upload = validated_data.pop('final_certificate_upload', None)
        application = super().update(instance, validated_data)
        if certificate_upload:
            application.final_certificate_file = _create_internal_file_asset(
                application, certificate_upload, _request_user(self)
            )
            application.save(update_fields=['final_certificate_file', 'updated_at'])
        return application
