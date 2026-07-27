"""
国际化（i18n）与主题（暗色模式）视图（N62）
- TranslationView: 返回可用语言及客户端翻译词典
- ThemeView: 返回可用主题（light / dark / auto）

接口：
- GET /api/v1/common/i18n/translations/
- GET /api/v1/common/i18n/themes/

客户端可使用 catalogs 中的完整公共界面词典进行运行时切换。
"""
from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.response import success_response
from common.schema import success_response_schema

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

TRANSLATION_CATALOGS = {
    'zh-CN': {},
    'en': {
        '团队管理平台': 'Team Management',
        '工作台': 'Workspace',
        '首页': 'Home',
        '待办事项': 'To-do',
        '通知中心': 'Notifications',
        '公告管理': 'Announcements',
        '团队动态': 'Activity',
        '定时报表': 'Scheduled Reports',
        '分析工作台': 'Analytics',
        '项目执行': 'Project Delivery',
        '项目管理': 'Projects',
        '项目归档': 'Project Archive',
        '比赛管理': 'Competitions',
        '任务管理': 'Tasks',
        '人员与资源': 'People & Resources',
        '团队组织': 'Teams',
        '成员管理': 'Members',
        '经费管理': 'Finance',
        '文件管理': 'Files',
        '导入中心': 'Imports',
        '成果与审批': 'Outcomes & Approvals',
        '成果与知识产权': 'Outcomes & IP',
        '我的贡献': 'My Contributions',
        '敏感资料': 'Sensitive Data',
        '平台管理': 'Administration',
        '操作日志': 'Audit Log',
        '第三方集成': 'Integrations',
        '平台能力': 'Platform Capabilities',
        '用户管理': 'User Management',
        '个人中心': 'Profile',
        '退出登录': 'Sign Out',
        '搜索项目/任务/成员...': 'Search projects, tasks, members...',
        '登录账户': 'Sign In',
        '邮箱地址': 'Email address',
        '密码': 'Password',
        '记住我': 'Remember me',
        '忘记密码': 'Forgot password',
        '登录': 'Sign In',
        '重置密码': 'Reset Password',
        '新密码': 'New password',
        '确认新密码': 'Confirm new password',
        '确认重置': 'Reset Password',
        '返回登录': 'Back to sign in',
        '语言': 'Language',
    },
}

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

    @extend_schema(
        responses={
            200: success_response_schema(
                'TranslationOptionsResponse',
                inline_serializer(
                    name='TranslationOptionsData',
                    fields={
                        'translations': inline_serializer(
                            name='TranslationOption',
                            many=True,
                            fields={
                                'code': serializers.CharField(),
                                'name': serializers.CharField(),
                                'native_name': serializers.CharField(),
                                'is_default': serializers.BooleanField(),
                            },
                        ),
                        'catalogs': serializers.DictField(),
                        'default': serializers.CharField(),
                        'locale_middleware_enabled': serializers.BooleanField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        # 检查是否启用 LocaleMiddleware
        middleware = list(getattr(settings, 'MIDDLEWARE', []))
        locale_enabled = any('LocaleMiddleware' in m for m in middleware)
        return success_response({
            'translations': AVAILABLE_TRANSLATIONS,
            'default': settings.LANGUAGE_CODE,
            'locale_middleware_enabled': locale_enabled,
            'catalogs': TRANSLATION_CATALOGS,
        })


class ThemeView(APIView):
    """
    可用主题（含暗色模式）
    GET /api/v1/common/i18n/themes/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={
            200: success_response_schema(
                'ThemeOptionsResponse',
                inline_serializer(
                    name='ThemeOptionsData',
                    fields={
                        'themes': inline_serializer(
                            name='ThemeOption',
                            many=True,
                            fields={
                                'code': serializers.CharField(),
                                'name': serializers.CharField(),
                                'is_default': serializers.BooleanField(),
                            },
                        ),
                        'default': serializers.CharField(),
                        'supports_dark_mode': serializers.BooleanField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        return success_response({
            'themes': AVAILABLE_THEMES,
            'default': 'light',
            'supports_dark_mode': True,
        })
