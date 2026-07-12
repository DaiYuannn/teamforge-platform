"""
回收站路由
- GET    /api/v1/recycle-bin/?type=project      获取回收站列表
- POST   /api/v1/recycle-bin/                    恢复对象
- DELETE /api/v1/recycle-bin/?type=project&id=1  永久删除对象
"""
from django.urls import path

from .recycle_views import RecycleBinView

urlpatterns = [
    path('', RecycleBinView.as_view(), name='recycle-bin'),
]
