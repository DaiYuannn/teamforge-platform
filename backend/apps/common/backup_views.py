"""仅系统管理员可用的演示数据备份与恢复 API。"""
from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework import serializers
from rest_framework.views import APIView

from common.permissions import IsSysAdmin
from common.response import error_response, success_response
from common.schema import success_response_schema
from .backup_service import (
    DemoBackupError,
    create_demo_backup,
    get_backup_file,
    import_demo_backup,
    list_demo_backups,
    restore_demo_backup,
)


class DemoBackupSerializer(serializers.Serializer):
    backup_id = serializers.CharField()
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    created_by = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField()
    size = serializers.IntegerField()
    entry_count = serializers.IntegerField(required=False)
    sha256 = serializers.CharField(required=False)
    download_url = serializers.CharField(required=False)
    requires_relogin = serializers.BooleanField(required=False)


class DemoBackupListDataSerializer(serializers.Serializer):
    backups = DemoBackupSerializer(many=True)
    total = serializers.IntegerField()
    mode = serializers.CharField()
    message = serializers.CharField()


class DemoBackupImportRequestSerializer(serializers.Serializer):
    file = serializers.FileField()


class DemoBackupRestoreRequestSerializer(serializers.Serializer):
    confirmation = serializers.CharField()


class DemoBackupRestoreDataSerializer(serializers.Serializer):
    backup_id = serializers.CharField()
    status = serializers.CharField()
    restored_at = serializers.DateTimeField()
    strategy = serializers.CharField()
    restored_records = serializers.DictField(
        child=serializers.IntegerField(),
    )
    restored_media_files = serializers.IntegerField()
    rollback_backup_id = serializers.CharField()
    requires_relogin = serializers.BooleanField()


class BackupListView(APIView):
    permission_classes = [IsSysAdmin]

    @extend_schema(
        responses={
            200: success_response_schema(
                'DemoBackupListResponse', DemoBackupListDataSerializer(),
            ),
        },
    )
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

    @extend_schema(
        request=None,
        responses={
            201: success_response_schema(
                'DemoBackupCreateResponse', DemoBackupSerializer(),
            ),
        },
    )
    def post(self, request):
        backup = create_demo_backup(created_by=request.user)
        return success_response(
            backup,
            message='演示数据备份包已生成',
            http_status=status.HTTP_201_CREATED,
        )


class BackupImportView(APIView):
    permission_classes = [IsSysAdmin]

    @extend_schema(
        request={
            'multipart/form-data': DemoBackupImportRequestSerializer,
        },
        responses={
            201: success_response_schema(
                'DemoBackupImportResponse', DemoBackupSerializer(),
            ),
        },
    )
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

    @extend_schema(
        request=DemoBackupRestoreRequestSerializer,
        responses={
            200: success_response_schema(
                'DemoBackupRestoreResponse', DemoBackupRestoreDataSerializer(),
            ),
        },
    )
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

    @extend_schema(
        responses={
            (200, 'application/zip'): OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description='Demo backup ZIP archive.',
            ),
        },
    )
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
