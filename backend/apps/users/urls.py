"""
用户路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, MyProfileView

# 创建路由器并注册 ViewSet
router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    # 当前用户个人信息
    path('me/', MyProfileView.as_view(), name='my-profile'),
    # 用户 CRUD 路由
    path('', include(router.urls)),
]
