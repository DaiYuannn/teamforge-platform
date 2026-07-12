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
    # 回收站（软删除恢复 / 永久删除）
    path('api/v1/recycle-bin/', include('apps.common.recycle_urls')),
    # 动态流（Activity Feed）
    path('api/v1/activities/', include('apps.common.activity_urls')),
    # 统一待办（聚合任务/审批/贡献审核等）
    path('api/v1/todo/', include('apps.common.todo_urls')),

    # ============ N34-N47 平台特性 ============
    # 多团队支持（N40）
    path('api/v1/teams/', include('apps.common.team_urls')),
    path('api/v1/team-members/', include('apps.common.team_member_urls')),
    # 审批流程（N41）
    path('api/v1/approvals/', include('apps.common.approval_urls')),
    # 敏感操作确认（N37）
    path('api/v1/common/confirmations/', include('apps.common.confirmation_urls')),
    # 备份与恢复（N38）
    path('api/v1/common/backup/', include('apps.common.backup_urls')),
    # 安全扫描（N39）
    path('api/v1/common/security-scan/', include('apps.common.security_urls')),
    # 自定义表单（N42）- forms/ 与 form-submissions/ 挂在 common 下
    path('api/v1/common/', include('apps.common.form_urls')),
    # 日历同步（N46）
    path('api/v1/common/calendar/', include('apps.common.calendar_urls')),
    # Open API 文档（N47）
    path('api/v1/common/api-docs/', include('apps.common.api_docs_urls')),

    # ============ N56-N62 工程质量特性 ============
    # 健康检查（N58，无需认证，供负载均衡探针）
    path('api/v1/common/health/', include('apps.common.health_check_urls')),
    # 前端错误监控（N57）
    path('api/v1/common/error-logs/', include('apps.common.error_urls')),
    # 性能监控（N59）
    path('api/v1/common/performance/', include('apps.common.performance_urls')),
    # OpenAPI Schema（N60）
    path('api/v1/common/openapi/', include('apps.common.openapi_urls')),
    # 无障碍 / API 可访问性报告（N61）
    path('api/v1/common/accessibility/', include('apps.common.accessibility_urls')),
    # 国际化与主题（N62）
    path('api/v1/common/i18n/', include('apps.common.i18n_urls')),
]

# 开发环境提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # 注册 django-debug-toolbar 路由（修复 'djdt' is not a registered namespace）
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns += [
            path('__debug__/', include('debug_toolbar.urls')),
        ]
