"""
备份与恢复路由
- GET  /api/v1/common/backup/
- POST /api/v1/common/backup/create/
- POST /api/v1/common/backup/<backup_id>/restore/
"""
from django.urls import path

from .backup_views import BackupListView, BackupCreateView, BackupRestoreView

urlpatterns = [
    path('', BackupListView.as_view(), name='backup-list'),
    path('create/', BackupCreateView.as_view(), name='backup-create'),
    path('<str:backup_id>/restore/', BackupRestoreView.as_view(), name='backup-restore'),
]
