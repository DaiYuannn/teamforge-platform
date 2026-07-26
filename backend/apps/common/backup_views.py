"""仅系统管理员可用的演示数据备份与恢复 API。"""
from django.http import FileResponse
from rest_framework import status
from rest_framework.views import APIView

from common.permissions import IsSysAdmin
from common.response import error_response, success_response
from .backup_service import (
    DemoBackupError,
    create_demo_backup,
    get_backup_file,
    import_demo_backup,
    list_demo_backups,
    restore_demo_backup,
)


class BackupListView(APIView):
    permission_classes = [IsSysAdmin]

    def get(self, request):
        backups = list_demo_backups()
        return success_response({
            'backups': backups,
            'total': len(backups),
            'mode': 'demo',
            'message': '演示数据包包含业务快照与实际附件；不替代生产数据库备份。',
        })


class BackupCreateView(APIView):
    permission_classes = [IsSysAdmin]

    def post(self, request):
        backup = create_demo_backup(created_by=request.user)
        return success_response(
            backup,
            message='演示数据备份包已生成',
            http_status=status.HTTP_201_CREATED,
        )


class BackupImportView(APIView):
    permission_classes = [IsSysAdmin]

    def post(self, request):
        try:
            backup = import_demo_backup(request.FILES.get('file'))
        except DemoBackupError as exc:
            return error_response(message=str(exc), code=4004)
        return success_response(
            backup,
            message='演示数据备份包已导入',
            http_status=status.HTTP_201_CREATED,
        )


class BackupRestoreView(APIView):
    permission_classes = [IsSysAdmin]

    def post(self, request, backup_id):
        if request.data.get('confirmation') != 'RESTORE_DEMO':
            return error_response(
                message='请输入确认口令 RESTORE_DEMO',
                code=4001,
            )
        try:
            result = restore_demo_backup(backup_id, requested_by=request.user)
        except DemoBackupError as exc:
            return error_response(message=str(exc), code=4004)
        return success_response(
            result,
            message='演示数据已恢复，请重新登录',
        )


class BackupDownloadView(APIView):
    permission_classes = [IsSysAdmin]

    def get(self, request, backup_id):
        try:
            path = get_backup_file(backup_id)
        except DemoBackupError as exc:
            return error_response(message=str(exc), code=4004)
        return FileResponse(
            path.open('rb'),
            as_attachment=True,
            filename=path.name,
            content_type='application/zip',
        )
