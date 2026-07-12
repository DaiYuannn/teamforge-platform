"""
备份与恢复视图（桩实现）
- BackupListView: 列出可用备份（桩，返回空列表）
- BackupCreateView: 触发备份（桩，返回成功）
- BackupRestoreView: 从备份恢复（桩，返回成功）

接口：
- GET  /api/v1/common/backup/
- POST /api/v1/common/backup/create/
- POST /api/v1/common/backup/<backup_id>/restore/
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response


class BackupListView(APIView):
    """列出可用备份（桩实现）"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 桩实现：返回空备份列表
        return success_response({
            'backups': [],
            'total': 0,
            'message': '当前无可用备份（桩实现，未接入真实备份引擎）',
        })


class BackupCreateView(APIView):
    """触发备份（桩实现）"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 桩实现：仅返回成功，未真正执行备份
        return success_response({
            'backup_id': None,
            'status': 'stub',
            'message': '备份任务已接收（桩实现，未接入真实备份引擎）',
        }, message='备份已触发')


class BackupRestoreView(APIView):
    """从备份恢复（桩实现）"""

    permission_classes = [IsAuthenticated]

    def post(self, request, backup_id):
        # 桩实现：仅返回成功，未真正执行恢复
        return success_response({
            'backup_id': backup_id,
            'status': 'stub',
            'message': '恢复任务已接收（桩实现，未接入真实备份引擎）',
        }, message='恢复已触发')
