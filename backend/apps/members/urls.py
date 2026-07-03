"""
成员路由
- /: 成员列表/详情（MemberViewSet）
- /skill-tags/: 技能标签管理（SkillTagViewSet）
- /member-skills/: 成员技能管理（MemberSkillViewSet）
- /flexible-schedules/: 灵活工时管理（FlexibleWorkScheduleViewSet）
- /member-detail/: 成员详情（MemberDetailView）

注意：路由注册顺序很重要，具体前缀路径需先于空前缀注册，
空前缀的 MemberViewSet 必须最后注册，避免其 detail 路由拦截其他子路由。
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MemberViewSet,
    SkillTagViewSet,
    MemberSkillViewSet,
    FlexibleWorkScheduleViewSet,
    MemberDetailView,
)

# 创建路由器并注册 ViewSet
router = DefaultRouter()
# 技能标签管理
router.register(r'skill-tags', SkillTagViewSet, basename='skill-tag')
# 成员技能管理
router.register(r'member-skills', MemberSkillViewSet, basename='member-skill')
# 灵活工时管理
router.register(r'flexible-schedules', FlexibleWorkScheduleViewSet, basename='work-schedule')
# 成员列表/详情（空前缀，最后注册，避免 detail 路由拦截子路由）
router.register(r'', MemberViewSet, basename='member')

urlpatterns = [
    # 成员详情（基本信息+技能+灵活工时+项目+任务）
    path('member-detail/', MemberDetailView.as_view(), name='member-detail'),
    path('', include(router.urls)),
]
