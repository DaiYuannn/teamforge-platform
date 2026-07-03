"""
贡献度序列化器
- ContributionSerializer: 完整字段（含关联名称）
- ContributionListSerializer: 列表精简
- ContributionCreateSerializer: 创建用
- ContributionReviewSerializer: 审核用
- MemberRankingSerializer / MemberRankingUpdateSerializer: 成员排名
- RankingObjectionSerializer / RankingObjectionCreateSerializer / RankingObjectionReviewSerializer: 排名异议
"""
from rest_framework import serializers

from .models import Contribution, MemberRanking, RankingObjection
from apps.users.serializers import UserListSerializer


# ============ 贡献记录 ============

class ContributionSerializer(serializers.ModelSerializer):
    """贡献记录完整序列化器（含关联名称）"""
    contribution_type_display = serializers.CharField(
        source='get_contribution_type_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default='')
    filled_by_name = serializers.CharField(source='filled_by.name', read_only=True, default='')
    proof_file_name = serializers.CharField(source='proof_file.name', read_only=True, default='')

    class Meta:
        model = Contribution
        fields = (
            'id', 'project', 'project_name', 'user', 'user_name',
            'contribution_type', 'contribution_type_display',
            'description', 'content', 'score', 'weight',
            'status', 'status_display',
            'related_object_id', 'period',
            'proof_file', 'proof_file_name',
            'filled_by', 'filled_by_name',
            'reviewer', 'reviewer_name', 'reviewed_at', 'review_opinion',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'score', 'status', 'reviewer', 'reviewed_at',
            'review_opinion', 'created_at', 'updated_at',
        )


class ContributionListSerializer(serializers.ModelSerializer):
    """贡献记录列表精简序列化器"""
    contribution_type_display = serializers.CharField(
        source='get_contribution_type_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    user_name = serializers.CharField(source='user.name', read_only=True, default='')
    filled_by_name = serializers.CharField(source='filled_by.name', read_only=True, default='')

    class Meta:
        model = Contribution
        fields = (
            'id', 'project', 'project_name', 'user', 'user_name',
            'contribution_type', 'contribution_type_display',
            'content', 'weight', 'status', 'status_display',
            'period', 'filled_by_name', 'reviewed_at', 'created_at',
        )
        read_only_fields = fields


class ContributionCreateSerializer(serializers.ModelSerializer):
    """贡献记录创建序列化器"""

    class Meta:
        model = Contribution
        fields = (
            'id', 'project', 'user', 'contribution_type',
            'content', 'proof_file', 'period',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        """创建贡献记录时自动设置填写人，默认待审核状态"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # 填写人默认为当前操作用户
            validated_data['filled_by'] = request.user
            # 若未指定贡献本人，则默认为当前操作用户
            validated_data.setdefault('user', request.user)
        validated_data.setdefault('status', Contribution.Status.PENDING)
        return super().create(validated_data)


class ContributionReviewSerializer(serializers.Serializer):
    """
    贡献审核序列化器
    - status: approved/rejected
    - review_opinion: 审核意见
    - weight: 审核后填写的权重/分值
    """
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    review_opinion = serializers.CharField(required=False, allow_blank=True, default='')
    weight = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )


# ============ 成员排名 ============

class MemberRankingSerializer(serializers.ModelSerializer):
    """成员排名完整序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_detail = UserListSerializer(source='user', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default='')

    class Meta:
        model = MemberRanking
        fields = (
            'id', 'project', 'project_name', 'user', 'user_detail',
            'period', 'status', 'status_display',
            'total_score', 'rank',
            'task_completed_count', 'project_count', 'competition_count',
            'ip_contribution_count',
            'is_published', 'is_public',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'total_score', 'rank', 'task_completed_count',
            'project_count', 'competition_count', 'ip_contribution_count',
            'is_published', 'is_public', 'created_at', 'updated_at',
        )


class MemberRankingUpdateSerializer(serializers.ModelSerializer):
    """成员排名修改序列化器（项目负责人修改排序）"""

    class Meta:
        model = MemberRanking
        fields = ('id', 'rank', 'total_score')
        read_only_fields = ('id',)


# ============ 排名异议 ============

class RankingObjectionSerializer(serializers.ModelSerializer):
    """排名异议完整序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    objector_detail = UserListSerializer(source='objector', read_only=True)
    objector_name = serializers.CharField(source='objector.name', read_only=True, default='')
    ranking_user_name = serializers.CharField(
        source='ranking.user.name', read_only=True, default=''
    )
    leader_reviewer_name = serializers.CharField(
        source='leader_reviewer.name', read_only=True, default=''
    )
    teacher_confirmer_name = serializers.CharField(
        source='teacher_confirmer.name', read_only=True, default=''
    )

    class Meta:
        model = RankingObjection
        fields = (
            'id', 'ranking', 'ranking_user_name',
            'objector', 'objector_detail', 'objector_name',
            'content', 'status', 'status_display', 'reply',
            'leader_opinion', 'leader_reviewer', 'leader_reviewer_name', 'leader_reviewed_at',
            'teacher_opinion', 'teacher_confirmer', 'teacher_confirmer_name',
            'teacher_confirmed_at', 'final_result',
            'handler', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'objector', 'status', 'reply',
            'leader_opinion', 'leader_reviewer', 'leader_reviewed_at',
            'teacher_opinion', 'teacher_confirmer', 'teacher_confirmed_at',
            'final_result', 'handler', 'created_at', 'updated_at',
        )


class RankingObjectionCreateSerializer(serializers.ModelSerializer):
    """排名异议创建序列化器"""

    class Meta:
        model = RankingObjection
        fields = ('id', 'ranking', 'content')
        read_only_fields = ('id',)

    def create(self, validated_data):
        """创建异议时自动设置提出人"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['objector'] = request.user
        return super().create(validated_data)


class RankingObjectionReviewSerializer(serializers.Serializer):
    """
    排名异议处理序列化器
    - action: leader_review（负责人初审）/ teacher_confirm（老师最终确认）
    - leader_opinion: 负责人意见
    - teacher_opinion: 老师意见
    - final_result: 最终结果
    - final_status: resolved/approved/rejected（老师确认时必填）
    """
    action = serializers.ChoiceField(choices=['leader_review', 'teacher_confirm'])
    leader_opinion = serializers.CharField(required=False, allow_blank=True, default='')
    teacher_opinion = serializers.CharField(required=False, allow_blank=True, default='')
    final_result = serializers.CharField(required=False, allow_blank=True, default='')
    # 老师确认时的最终状态：approved(异议成立)/rejected(异议不成立)
    final_status = serializers.ChoiceField(
        choices=['approved', 'rejected'], required=False
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
