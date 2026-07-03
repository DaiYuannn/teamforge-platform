"""
知识产权管理序列化器
"""
from rest_framework import serializers

from .models import (
    IntellectualPropertyApplication,
    IPApplicationContributor,
    IPReturnRecord,
    IPMaterialVersion,
    IPObjection,
)
from apps.users.serializers import UserListSerializer


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
        read_only_fields = ('id', 'created_at', 'updated_at')


class IPReturnRecordCreateSerializer(serializers.ModelSerializer):
    """退回修改记录创建序列化器"""

    class Meta:
        model = IPReturnRecord
        fields = (
            'id', 'application', 'return_time', 'return_source', 'return_reason',
            'responsibility_type', 'responsible_user', 'assigned_by',
            'modify_deadline', 'proof_file',
        )
        read_only_fields = ('id',)


# ============ 材料版本 ============

class IPMaterialVersionSerializer(serializers.ModelSerializer):
    """材料版本完整序列化器"""
    material_type_display = serializers.CharField(
        source='get_material_type_display', read_only=True
    )
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True, default='')
    file_asset_name = serializers.CharField(source='file_asset.name', read_only=True, default='')

    class Meta:
        model = IPMaterialVersion
        fields = (
            'id', 'application', 'file_asset', 'file_asset_name',
            'material_type', 'material_type_display', 'version',
            'uploaded_by', 'uploaded_by_name', 'change_note',
            'related_return_record', 'is_final', 'created_at',
        )
        read_only_fields = ('id', 'uploaded_by', 'created_at')


class IPMaterialVersionCreateSerializer(serializers.ModelSerializer):
    """材料版本创建序列化器"""

    class Meta:
        model = IPMaterialVersion
        fields = (
            'id', 'application', 'file_asset', 'material_type', 'version',
            'change_note', 'related_return_record', 'is_final',
        )
        read_only_fields = ('id',)


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

    class Meta:
        model = IPObjection
        fields = (
            'id', 'application', 'objector', 'objector_detail',
            'objection_type', 'objection_type_display', 'content', 'proof_file',
            'status', 'status_display',
            'leader_opinion', 'leader_reviewer', 'leader_reviewer_name', 'leader_reviewed_at',
            'teacher_opinion', 'teacher_confirmer', 'teacher_confirmer_name',
            'teacher_confirmed_at', 'final_result',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'objector', 'status', 'leader_opinion', 'leader_reviewer',
            'leader_reviewed_at', 'teacher_opinion', 'teacher_confirmer',
            'teacher_confirmed_at', 'final_result', 'created_at', 'updated_at',
        )


class IPObjectionCreateSerializer(serializers.ModelSerializer):
    """异议创建序列化器"""

    class Meta:
        model = IPObjection
        fields = (
            'id', 'application', 'objection_type', 'content', 'proof_file',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        """创建异议时自动设置提出人"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['objector'] = request.user
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
            'final_certificate_file', 'intro',
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
            'related_project', 'main_writer', 'intro',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        """创建申请时自动设置创建人"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class IPApplicationUpdateSerializer(serializers.ModelSerializer):
    """申请更新序列化器"""

    class Meta:
        model = IntellectualPropertyApplication
        fields = (
            'id', 'title', 'ip_type', 'related_project',
            'main_writer', 'applicant_executor', 'material_manager',
            'project_reviewer', 'teacher_confirmer',
            'start_date', 'submit_date', 'accepted_date', 'authorized_date',
            'current_problem', 'final_certificate_file', 'intro',
        )
        read_only_fields = ('id',)
