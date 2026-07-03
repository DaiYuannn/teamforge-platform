"""
项目总路由
所有 API 路径前缀 /api/v1/
包含 SimpleJWT 的 token 路由
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import LoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # SimpleJWT token 路由
    path('api/v1/auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 各业务模块路由
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/projects/', include('apps.projects.urls')),
    path('api/v1/competitions/', include('apps.competitions.urls')),
    path('api/v1/tasks/', include('apps.tasks.urls')),
    path('api/v1/members/', include('apps.members.urls')),
    path('api/v1/finance/', include('apps.finance.urls')),
    path('api/v1/files/', include('apps.files.urls')),
    path('api/v1/imports/', include('apps.imports.urls')),
    path('api/v1/dashboard/', include('apps.dashboard.urls')),
    path('api/v1/contributions/', include('apps.contributions.urls')),
    path('api/v1/sensitive/', include('apps.sensitive.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
    path('api/v1/exports/', include('apps.exports.urls')),
    path('api/v1/intellectual-property/', include('apps.intellectual_property.urls')),
    path('api/v1/integrations/', include('apps.integrations.urls')),
]

# 开发环境提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # 注册 django-debug-toolbar 路由（修复 'djdt' is not a registered namespace）
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns += [
            path('__debug__/', include('debug_toolbar.urls')),
        ]
