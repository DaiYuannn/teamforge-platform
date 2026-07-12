"""
用户路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, MyProfileView, ChangePasswordView, UploadAvatarView
from .preference_views import UserPreferenceView
from .statistics_views import MemberStatisticsView
from .workload_views import MemberWorkloadView
from .skill_views import MemberSkillViewSet
from .growth_views import MemberGrowthViewSet
from .two_factor_views import Generate2FAView, Verify2FAView, Disable2FAView
from .role_views import CustomRoleViewSet, UserRoleAssignmentViewSet
from .oauth_views import (
    OAuthProvidersView, OAuthCallbackView, OAuthBindListView,
)

# 创建路由器并注册 ViewSet
# 注意：带前缀的路由（skills/growth）必须先注册，
# 否则空前缀 UserViewSet 的详情路由 (?P<pk>[^/.]+)/ 会先匹配到它们
router = DefaultRouter()
router.register(r'skills', MemberSkillViewSet, basename='member-skill')
router.register(r'growth', MemberGrowthViewSet, basename='member-growth')
router.register(r'', UserViewSet, basename='user')

# 自定义角色管理路由器
role_router = DefaultRouter()
role_router.register(r'', CustomRoleViewSet, basename='custom-role')

# 用户角色分配路由器
role_assignment_router = DefaultRouter()
role_assignment_router.register(r'', UserRoleAssignmentViewSet, basename='role-assignment')

urlpatterns = [
    # 当前用户个人信息
    path('me/', MyProfileView.as_view(), name='my-profile'),
    # 修改密码
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    # 头像上传
    path('upload-avatar/', UploadAvatarView.as_view(), name='upload-avatar'),
    # 当前用户个人化偏好设置
    path('preference/', UserPreferenceView.as_view(), name='user-preference'),
    # 成员统计分析
    path('statistics/', MemberStatisticsView.as_view(), name='member-statistics'),
    # 成员工作量分析
    path('workload/', MemberWorkloadView.as_view(), name='member-workload'),
    # 双因素认证（2FA）
    path('2fa/generate/', Generate2FAView.as_view(), name='2fa-generate'),
    path('2fa/verify/', Verify2FAView.as_view(), name='2fa-verify'),
    path('2fa/disable/', Disable2FAView.as_view(), name='2fa-disable'),
    # 第三方登录（OAuth）
    path('oauth/providers/', OAuthProvidersView.as_view(), name='oauth-providers'),
    path('oauth/callback/', OAuthCallbackView.as_view(), name='oauth-callback'),
    path('oauth/bindings/', OAuthBindListView.as_view(), name='oauth-bindings'),
    # 自定义角色管理
    path('roles/', include(role_router.urls)),
    # 用户角色分配
    path('role-assignments/', include(role_assignment_router.urls)),
    # 用户 CRUD 路由
    path('', include(router.urls)),
]
