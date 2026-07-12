"""
敏感操作确认视图
- SensitiveConfirmationGenerateView: 生成确认令牌
- SensitiveConfirmationVerifyView: 校验令牌并标记已确认

接口：
- POST /api/v1/common/confirmations/generate/
- POST /api/v1/common/confirmations/verify/
"""
import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from common.response import success_response, error_response
from .confirmation_models import SensitiveConfirmation

# 确认令牌有效期（分钟）
CONFIRM_TOKEN_EXPIRE_MINUTES = 30


def _generate_token():
    """生成唯一确认令牌"""
    return secrets.token_hex(16)


class SensitiveConfirmationGenerateSerializer(serializers.Serializer):
    """生成确认令牌请求"""
    confirm_type = serializers.ChoiceField(choices=SensitiveConfirmation.Type.choices)
    target_type = serializers.CharField(max_length=50, required=False, default='')
    target_id = serializers.CharField(max_length=100, required=False, default='')

    def validate_confirm_type(self, value):
        # 二次校验枚举合法
        if value not in SensitiveConfirmation.Type.values:
            raise serializers.ValidationError('非法的确认类型')
        return value


class SensitiveConfirmationVerifySerializer(serializers.Serializer):
    """校验确认令牌请求"""
    token = serializers.CharField(max_length=64)


class SensitiveConfirmationSerializer(serializers.ModelSerializer):
    """确认记录序列化器"""
    type_display = serializers.CharField(source='get_confirm_type_display', read_only=True)

    class Meta:
        model = SensitiveConfirmation
        fields = (
            'id', 'user', 'confirm_type', 'type_display',
            'target_type', 'target_id', 'token',
            'is_confirmed', 'expires_at', 'created_at',
        )
        read_only_fields = fields


class SensitiveConfirmationGenerateView(GenericAPIView):
    """
    生成敏感操作确认令牌
    POST /api/v1/common/confirmations/generate/
    body: {"confirm_type": "delete_project", "target_type": "project", "target_id": "1"}
    """
    serializer_class = SensitiveConfirmationGenerateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        confirmation = SensitiveConfirmation.objects.create(
            user=request.user,
            confirm_type=data['confirm_type'],
            target_type=data.get('target_type', ''),
            target_id=data.get('target_id', ''),
            token=_generate_token(),
            expires_at=timezone.now() + timedelta(minutes=CONFIRM_TOKEN_EXPIRE_MINUTES),
        )
        return success_response(
            SensitiveConfirmationSerializer(confirmation).data,
            message='确认令牌已生成',
            http_status=status.HTTP_201_CREATED,
        )


class SensitiveConfirmationVerifyView(GenericAPIView):
    """
    校验敏感操作确认令牌
    POST /api/v1/common/confirmations/verify/
    body: {"token": "xxxx"}
    """
    serializer_class = SensitiveConfirmationVerifySerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        try:
            confirmation = SensitiveConfirmation.objects.get(token=token)
        except SensitiveConfirmation.DoesNotExist:
            return error_response(message='确认令牌不存在', code=2301,
                                  http_status=status.HTTP_404_NOT_FOUND)

        # 仅令牌所属用户可校验
        if confirmation.user_id != request.user.id:
            return error_response(message='无权校验该令牌', code=2302,
                                  http_status=status.HTTP_403_FORBIDDEN)

        if confirmation.is_confirmed:
            return error_response(message='该令牌已被使用', code=2303,
                                  http_status=status.HTTP_400_BAD_REQUEST)

        if confirmation.expires_at <= timezone.now():
            return error_response(message='该令牌已过期', code=2304,
                                  http_status=status.HTTP_400_BAD_REQUEST)

        confirmation.is_confirmed = True
        confirmation.save(update_fields=['is_confirmed'])
        return success_response(
            SensitiveConfirmationSerializer(confirmation).data,
            message='确认成功',
        )
