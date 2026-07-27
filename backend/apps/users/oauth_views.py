"""
第三方登录（OAuth）视图（桩实现）
- OAuthProvidersView: 列出支持的第三方登录提供商
- OAuthCallbackView: 第三方登录回调（桩，返回未实现提示）
- OAuthBindListView: 查询当前用户已绑定的第三方账号

接口：
- GET  /api/v1/users/oauth/providers/
- POST /api/v1/users/oauth/callback/
- GET  /api/v1/users/oauth/bindings/
"""
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.schema import success_response_schema
from .oauth_models import OAuthAccount


# 支持的第三方登录提供商
SUPPORTED_PROVIDERS = [
    {'provider': 'github', 'name': 'GitHub', 'enabled': True},
    {'provider': 'google', 'name': 'Google', 'enabled': True},
    {'provider': 'wechat', 'name': '微信', 'enabled': False},
]

_OAUTH_ERROR_RESPONSE_SCHEMA = inline_serializer(
    name='OAuthErrorResponse',
    fields={
        'code': serializers.IntegerField(),
        'message': serializers.CharField(),
        'data': serializers.JSONField(allow_null=True),
    },
)


class OAuthAccountSerializer(serializers.ModelSerializer):
    """第三方账号绑定序列化器"""

    class Meta:
        model = OAuthAccount
        fields = ('id', 'provider', 'provider_uid', 'user', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class OAuthProvidersView(APIView):
    """
    列出支持的第三方登录提供商
    GET /api/v1/users/oauth/providers/
    """
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: success_response_schema(
                'OAuthProvidersResponse',
                inline_serializer(
                    name='OAuthProvider',
                    fields={
                        'provider': serializers.CharField(),
                        'name': serializers.CharField(),
                        'enabled': serializers.BooleanField(),
                    },
                    many=True,
                ),
            ),
        },
    )
    def get(self, request):
        return success_response(SUPPORTED_PROVIDERS)


class OAuthCallbackView(GenericAPIView):
    """
    第三方登录回调（桩实现）
    POST /api/v1/users/oauth/callback/
    body: {"provider": "github", "code": "..."}
    """
    serializer_class = serializers.Serializer
    permission_classes = [AllowAny]

    @extend_schema(
        request=inline_serializer(
            name='OAuthCallbackRequest',
            fields={
                'provider': serializers.CharField(),
                'code': serializers.CharField(),
            },
        ),
        responses={
            400: _OAUTH_ERROR_RESPONSE_SCHEMA,
            501: _OAUTH_ERROR_RESPONSE_SCHEMA,
        },
    )
    def post(self, request):
        provider = request.data.get('provider', '')
        code = request.data.get('code', '')
        if not provider or not code:
            return error_response(message='请提供 provider 与 code', code=2201,
                                  http_status=status.HTTP_400_BAD_REQUEST)
        # 桩实现：未真正对接第三方，返回未实现提示
        return error_response(
            message=f'第三方登录({provider})暂未对接，请联系管理员配置',
            code=2202,
            http_status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class OAuthBindListView(GenericAPIView):
    """
    查询当前用户已绑定的第三方账号
    GET /api/v1/users/oauth/bindings/
    """
    serializer_class = OAuthAccountSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: success_response_schema(
                'OAuthBindingListResponse',
                OAuthAccountSerializer(many=True),
            ),
        },
    )
    def get(self, request):
        bindings = OAuthAccount.objects.filter(user=request.user).order_by('-created_at')
        serializer = self.get_serializer(bindings, many=True)
        return success_response(serializer.data)
