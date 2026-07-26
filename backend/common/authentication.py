"""JWT authentication with hard membership-status boundaries."""
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


class ScopedJWTAuthentication(JWTAuthentication):
    """
    External collaborators only enter project-scoped collaboration surfaces.

    Object/list querysets still apply the exact project membership filter.  This
    authentication-level boundary prevents a newly added endpoint from
    accidentally exposing team-wide contacts, finance, approvals or audit data.
    """

    EXTERNAL_ALLOWED_PREFIXES = (
        '/api/v1/users/me/',
        '/api/v1/users/preference/',
        '/api/v1/users/change-password/',
        '/api/v1/users/upload-avatar/',
        '/api/v1/projects/',
        '/api/v1/tasks/',
        '/api/v1/files/',
        '/api/v1/competitions/',
        '/api/v1/notifications/',
        '/api/v1/contributions/',
        '/api/v1/common/calendar/',
        '/api/v1/common/media/',
        '/api/v1/dashboard/public-portal/',
    )

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        if getattr(user, 'membership_status', '') == 'exited':
            raise AuthenticationFailed('已退出团队的账号不能继续访问系统')
        if (
            getattr(user, 'membership_status', '') == 'external'
            and not request.path.startswith(self.EXTERNAL_ALLOWED_PREFIXES)
        ):
            raise PermissionDenied('外部协作者只能访问获授权的项目协作内容')
        return user, token


class ActiveMemberTokenRefreshSerializer(TokenRefreshSerializer):
    """Do not mint new access tokens for disabled or exited accounts."""

    def validate(self, attrs):
        refresh = RefreshToken(attrs['refresh'])
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        if user_id is None:
            raise AuthenticationFailed('刷新令牌缺少用户信息')

        from apps.users.models import User

        lookup = {api_settings.USER_ID_FIELD: user_id}
        try:
            user = User.objects.get(**lookup)
        except User.DoesNotExist as exc:
            raise AuthenticationFailed('用户不存在') from exc
        if not user.is_active or user.membership_status == User.MembershipStatus.EXITED:
            raise AuthenticationFailed('已退出或停用账号不能刷新令牌')
        return super().validate(attrs)
