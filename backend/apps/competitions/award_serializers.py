"""
比赛获奖记录序列化器
"""
from rest_framework import serializers

from apps.users.models import User
from .award_models import CompetitionAward


class CompetitionAwardSerializer(serializers.ModelSerializer):
    """比赛获奖记录序列化器"""
    competition_name = serializers.CharField(
        source='competition.name', read_only=True, default=''
    )
    recipient_details = serializers.SerializerMethodField()

    class Meta:
        model = CompetitionAward
        fields = (
            'id', 'competition', 'competition_name',
            'award_name', 'award_level', 'award_date',
            'recipients', 'recipient_details',
            'notes', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_recipient_details(self, obj):
        """获奖人详情列表"""
        return [
            {'id': r.id, 'name': r.name, 'email': r.email}
            for r in obj.recipients.all()
        ]


class CompetitionAwardCreateSerializer(serializers.Serializer):
    """比赛获奖记录创建序列化器"""
    award_name = serializers.CharField(max_length=200)
    award_level = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    award_date = serializers.DateField(required=False, allow_null=True)
    recipients = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def create(self, validated_data):
        """创建获奖记录"""
        recipients = validated_data.pop('recipients', [])
        competition = validated_data.get('competition')
        award = CompetitionAward.objects.create(
            competition=competition,
            award_name=validated_data.get('award_name', ''),
            award_level=validated_data.get('award_level', ''),
            award_date=validated_data.get('award_date'),
            notes=validated_data.get('notes', ''),
        )
        if recipients:
            award.recipients.set(recipients)
        return award
