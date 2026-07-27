"""
文件路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FileAssetViewSet, FileFolderViewSet, FileTagViewSet
from .share_views import FileShareLinkViewSet

# 创建路由器并注册 ViewSet
# 注意：带前缀的路由（tags/shares）必须在 '' 之前注册，否则 '' 的详情路由 ^(?P<pk>[^/.]+)/$
# 会把 /files/tags/ 或 /files/shares/ 当作 FileAsset 的 pk 来匹配（导致 404/405）
router = DefaultRouter()
router.register(r'folders', FileFolderViewSet, basename='file-folder')
router.register(r'tags', FileTagViewSet, basename='file-tag')
router.register(r'shares', FileShareLinkViewSet, basename='file-share')
router.register(r'', FileAssetViewSet, basename='file')

urlpatterns = [
    path('', include(router.urls)),
]
