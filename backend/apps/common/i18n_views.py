"""
国际化（i18n）与主题（暗色模式）视图（N62）
- TranslationView: 返回可用翻译语言（桩：zh-CN / en）
- ThemeView: 返回可用主题（light / dark / auto）

接口：
- GET /api/v1/common/i18n/translations/
- GET /api/v1/common/i18n/themes/

说明：当前 Django 中间件链未启用 LocaleMiddleware，此处提供桩数据，
前端可据此渲染语言切换与主题切换 UI。
"""
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.response import success_response

# 可用翻译（桩）
AVAILABLE_TRANSLATIONS = [
    {
        'code': 'zh-CN',
        'name': '简体中文',
        'native_name': '简体中文',
        'is_default': True,
    },
    {
        'code': 'en',
        'name': 'English',
        'native_name': 'English',
        'is_default': False,
    },
]

# 可用主题
AVAILABLE_THEMES = [
    {'code': 'light', 'name': '浅色', 'is_default': True},
    {'code': 'dark', 'name': '深色', 'is_default': False},
    {'code': 'auto', 'name': '跟随系统', 'is_default': False},
]


class TranslationView(APIView):
    """
    可用翻译语言
    GET /api/v1/common/i18n/translations/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        # 检查是否启用 LocaleMiddleware
        middleware = list(getattr(settings, 'MIDDLEWARE', []))
        locale_enabled = any('LocaleMiddleware' in m for m in middleware)
        return success_response({
            'translations': AVAILABLE_TRANSLATIONS,
            'default': settings.LANGUAGE_CODE,
            'locale_middleware_enabled': locale_enabled,
            'note': '翻译内容为桩数据，生产应接入 Django i18n catalog',
        })


class ThemeView(APIView):
    """
    可用主题（含暗色模式）
    GET /api/v1/common/i18n/themes/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return success_response({
            'themes': AVAILABLE_THEMES,
            'default': 'light',
            'supports_dark_mode': True,
        })
