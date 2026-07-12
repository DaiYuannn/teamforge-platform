"""
安全扫描视图
- SecurityScanView: 返回安全检查清单状态

接口：
- GET /api/v1/common/security-scan/
"""
import os

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response


class SecurityScanView(APIView):
    """
    安全扫描
    GET /api/v1/common/security-scan/
    返回安全检查清单及各项通过状态
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        checks = []

        # 1. SECRET_KEY 是否来自环境变量（非默认 insecure 值）
        secret_key = getattr(settings, 'SECRET_KEY', '')
        secret_key_from_env = (
            bool(os.environ.get('DJANGO_SECRET_KEY'))
            and not str(secret_key).startswith('django-insecure-')
        )
        checks.append({
            'item': 'secret_key_from_env',
            'title': 'SECRET_KEY 来自环境变量',
            'passed': secret_key_from_env,
            'severity': 'high',
        })

        # 2. 生产环境 DEBUG=False
        debug_off = not getattr(settings, 'DEBUG', True)
        checks.append({
            'item': 'debug_disabled',
            'title': 'DEBUG 已关闭',
            'passed': debug_off,
            'severity': 'high',
        })

        # 3. HTTPS 建议（SECURE_SSL_REDIRECT / SECURE_HSTS_SECONDS）
        ssl_redirect = getattr(settings, 'SECURE_SSL_REDIRECT', False)
        hsts_seconds = getattr(settings, 'SECURE_HSTS_SECONDS', 0)
        https_recommended = bool(ssl_redirect) or int(hsts_seconds or 0) > 0
        checks.append({
            'item': 'https_recommended',
            'title': '建议启用 HTTPS（SSL 重定向 / HSTS）',
            'passed': https_recommended,
            'severity': 'medium',
        })

        # 4. 密码策略（验证器数量）
        validators = getattr(settings, 'AUTH_PASSWORD_VALIDATORS', [])
        password_policy_ok = len(validators) >= 3
        checks.append({
            'item': 'password_policy',
            'title': '密码强度策略（至少 3 个验证器）',
            'passed': password_policy_ok,
            'detail': f'已配置 {len(validators)} 个验证器',
            'severity': 'medium',
        })

        # 5. X-Frame-Options 防点击劫持
        x_frame = getattr(settings, 'X_FRAME_OPTIONS', '')
        checks.append({
            'item': 'x_frame_options',
            'title': 'X-Frame-Options 防点击劫持',
            'passed': str(x_frame).upper() in ('DENY', 'SAMEORIGIN'),
            'detail': x_frame,
            'severity': 'medium',
        })

        # 6. SECURE_CONTENT_TYPE_NOSNIFF
        nosniff = getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False)
        checks.append({
            'item': 'content_type_nosniff',
            'title': 'X-Content-Type-Options: nosniff',
            'passed': bool(nosniff),
            'severity': 'low',
        })

        # 7. CORS 是否限制来源（非全部放开）
        cors_all = getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False)
        checks.append({
            'item': 'cors_restricted',
            'title': 'CORS 来源受限',
            'passed': not cors_all,
            'severity': 'medium',
        })

        # 8. Cookie 安全（生产环境建议 Secure）
        session_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        csrf_secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)
        checks.append({
            'item': 'cookie_secure',
            'title': 'Cookie Secure 标记',
            'passed': bool(session_secure) and bool(csrf_secure),
            'severity': 'medium',
        })

        total = len(checks)
        passed = sum(1 for c in checks if c['passed'])
        return success_response({
            'checks': checks,
            'total': total,
            'passed': passed,
            'failed': total - passed,
            'score': round(passed / total * 100, 1) if total else 0,
        })
