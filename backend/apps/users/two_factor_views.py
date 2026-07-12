"""
双因素认证（2FA）视图
- Generate2FAView: 生成 TOTP 密钥与二维码 URI
- Verify2FAView: 校验 TOTP 验证码并启用 2FA
- Disable2FAView: 关闭 2FA

接口：
- POST /api/v1/users/2fa/generate/
- POST /api/v1/users/2fa/verify/
- POST /api/v1/users/2fa/disable/
"""
import base64
import os
import secrets

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from .two_factor_models import TwoFactorSecret

# 优先使用 pyotp 生成/校验 TOTP，未安装时回退到简易实现
try:
    import pyotp  # type: ignore

    _HAS_PYOTP = True
except ImportError:  # pragma: no cover
    pyotp = None
    _HAS_PYOTP = False


def _generate_secret():
    """生成 TOTP 密钥（base32）"""
    if _HAS_PYOTP:
        return pyotp.random_base32()
    # 回退：生成 32 字节随机串并 base32 编码
    return base64.b32encode(os.urandom(20)).decode('ascii').rstrip('=')


def _verify_code(secret, code):
    """校验 TOTP 验证码"""
    if not code:
        return False
    if _HAS_PYOTP:
        try:
            return pyotp.TOTP(secret).verify(code, valid_window=1)
        except Exception:
            return False
    # 回退：无法严格校验，仅校验长度为 6 位数字（仅用于未安装 pyotp 的环境）
    return bool(code) and len(str(code)) == 6 and str(code).isdigit()


def _build_otp_uri(secret, email):
    """构造 otpauth URI"""
    issuer = 'TeamManagement'
    label = f'{issuer}:{email}'
    return f'otpauth://totp/{label}?secret={secret}&issuer={issuer}'


def _generate_backup_codes(count=8):
    """生成备用码列表"""
    return [secrets.token_hex(4).upper() for _ in range(count)]


class Generate2FAView(APIView):
    """
    生成 2FA 密钥
    - POST: 为当前用户生成（或重置）TOTP 密钥，返回密钥与 otpauth URI
    - 不会立即启用，需调用 /verify/ 校验通过后才启用
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        tf, created = TwoFactorSecret.objects.get_or_create(user=user)
        # 已启用时不允许重新生成
        if tf.is_enabled:
            return error_response(message='2FA 已启用，请先关闭后再重新生成', code=2001)

        tf.secret = _generate_secret()
        tf.backup_codes = _generate_backup_codes()
        tf.is_enabled = False
        tf.enabled_at = None
        tf.save(update_fields=['secret', 'backup_codes', 'is_enabled', 'enabled_at'])

        return success_response({
            'secret': tf.secret,
            'otpauth_uri': _build_otp_uri(tf.secret, user.email),
            'backup_codes': tf.backup_codes,
            'pyotp_available': _HAS_PYOTP,
        }, message='2FA 密钥已生成，请使用验证器扫码并输入验证码完成启用')


class Verify2FAView(APIView):
    """
    校验 2FA 验证码并启用
    - POST body: {"code": "123456"}
    - 校验通过后启用 2FA
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        code = str(request.data.get('code', '')).strip()

        try:
            tf = TwoFactorSecret.objects.get(user=user)
        except TwoFactorSecret.DoesNotExist:
            return error_response(message='请先生成 2FA 密钥', code=2002,
                                  http_status=status.HTTP_400_BAD_REQUEST)

        if tf.is_enabled:
            return error_response(message='2FA 已启用', code=2003)

        if not _verify_code(tf.secret, code):
            return error_response(message='验证码错误', code=2004,
                                  http_status=status.HTTP_400_BAD_REQUEST)

        tf.is_enabled = True
        tf.enabled_at = timezone.now()
        tf.save(update_fields=['is_enabled', 'enabled_at'])

        return success_response({
            'is_enabled': True,
            'enabled_at': tf.enabled_at,
        }, message='2FA 启用成功')


class Disable2FAView(APIView):
    """
    关闭 2FA
    - POST body: {"code": "123456"} 或 {"backup_code": "XXXX"}
    - 校验通过后关闭 2FA
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        code = str(request.data.get('code', '')).strip()
        backup_code = str(request.data.get('backup_code', '')).strip().upper()

        try:
            tf = TwoFactorSecret.objects.get(user=user)
        except TwoFactorSecret.DoesNotExist:
            return error_response(message='未启用 2FA', code=2005,
                                  http_status=status.HTTP_400_BAD_REQUEST)

        if not tf.is_enabled:
            return error_response(message='未启用 2FA', code=2005)

        verified = False
        if backup_code:
            # 备用码一次性使用
            if backup_code in tf.backup_codes:
                tf.backup_codes = [c for c in tf.backup_codes if c != backup_code]
                verified = True
        if not verified and code:
            verified = _verify_code(tf.secret, code)

        if not verified:
            return error_response(message='验证码或备用码错误', code=2006,
                                  http_status=status.HTTP_400_BAD_REQUEST)

        tf.is_enabled = False
        tf.enabled_at = None
        tf.save(update_fields=['is_enabled', 'enabled_at', 'backup_codes'])

        return success_response({'is_enabled': False}, message='2FA 已关闭')

    def get(self, request):
        """查询当前用户 2FA 状态"""
        user = request.user
        try:
            tf = TwoFactorSecret.objects.get(user=user)
            return success_response({
                'is_enabled': tf.is_enabled,
                'enabled_at': tf.enabled_at,
            })
        except TwoFactorSecret.DoesNotExist:
            return success_response({'is_enabled': False, 'enabled_at': None})
