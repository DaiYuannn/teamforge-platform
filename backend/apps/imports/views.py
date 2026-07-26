"""
数据导入视图
- ImportTaskViewSet: 导入任务管理
- preview: POST 上传文件并预览
- confirm: POST 确认导入
- rollback: POST 回滚导入
"""
import os
import uuid
from django.conf import settings
from django.utils.text import get_valid_filename
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.permissions import IsTeacherOrAdmin
from .models import ImportTask
from .serializers import (
    ImportTaskSerializer, ImportTaskListSerializer,
    ImportPreviewSerializer, ImportConfirmSerializer,
)
from .services import import_service


class ImportTaskViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    数据导入 ViewSet
    - list/retrieve: 老师/管理员可查看导入历史
    - preview: POST 上传文件并预览
    - confirm: POST 确认导入（事务写入）
    - rollback: POST 回滚导入（根据快照删除）
    """
    queryset = ImportTask.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': ImportTaskListSerializer,
        'retrieve': ImportTaskSerializer,
        'preview': ImportPreviewSerializer,
        'confirm': ImportConfirmSerializer,
    }

    permission_classes_by_action = {
        'list': [IsTeacherOrAdmin],
        'retrieve': [IsTeacherOrAdmin],
        'preview': [IsTeacherOrAdmin],
        'confirm': [IsTeacherOrAdmin],
        'rollback': [IsTeacherOrAdmin],
        'destroy': [IsTeacherOrAdmin],
    }

    filterset_fields = ['module', 'status', 'created_by']
    search_fields = ['module', 'file_path']
    ordering_fields = ['created_at', 'updated_at']

    @action(detail=False, methods=['post'])
    def preview(self, request):
        """
        上传文件并预览
        POST /api/v1/imports/preview/
        body: file(文件), module(模块), field_mapping(可选)
        :return: 预览数据 + 自动字段映射 + 校验结果
        """
        serializer = ImportPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data['file']
        module = serializer.validated_data['module']
        custom_mapping = serializer.validated_data.get('field_mapping', {})

        # 保存文件到临时目录
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'imports')
        os.makedirs(upload_dir, exist_ok=True)
        suffix = os.path.splitext(file.name)[1].lower()
        if suffix not in {'.xlsx', '.xlsm', '.csv'}:
            return error_response(
                message='仅支持 .xlsx、.xlsm 或 .csv 文件',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        safe_name = get_valid_filename(os.path.basename(file.name))
        file_path = os.path.join(upload_dir, f'{uuid.uuid4().hex}_{safe_name}')
        with open(file_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)

        try:
            # 解析 Excel 文件
            headers, rows = import_service.parse_excel(file_path)
        except Exception as e:
            os.remove(file_path)
            return error_response(message=f'文件解析失败: {str(e)}')

        # 自动字段映射（或使用自定义映射）
        if custom_mapping:
            field_mapping = custom_mapping
        else:
            field_mapping = import_service.auto_map_fields(headers, module)

        # 校验数据
        valid_rows, error_details = import_service.validate_rows(rows, field_mapping, module)

        # 创建导入任务记录
        import_task = ImportTask.objects.create(
            module=module,
            file_path=file_path,
            status=ImportTask.Status.PREVIEWED,
            field_mapping=field_mapping,
            preview_data={
                'headers': headers,
                'rows': rows[:20],  # 预览前20行
                'total_preview': len(rows),
            },
            total_rows=len(rows),
            valid_rows=len(valid_rows),
            error_rows=len(error_details),
            error_details=error_details,
            created_by=request.user,
        )

        return success_response({
            'task_id': import_task.id,
            'headers': headers,
            'field_mapping': field_mapping,
            'preview_rows': rows[:20],
            'total_rows': len(rows),
            'valid_rows': len(valid_rows),
            'error_rows': len(error_details),
            'error_details': error_details,
            'field_options': import_service.get_field_options(module),
        }, message='文件解析成功，请确认字段映射后导入')

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        确认导入
        POST /api/v1/imports/{id}/confirm/
        body: field_mapping(可选，最终字段映射)
        """
        import_task = self.get_object()

        if import_task.status != ImportTask.Status.PREVIEWED:
            return error_response(message='只能确认已预览的导入任务')

        serializer = ImportConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        field_mapping = serializer.validated_data.get('field_mapping')

        # 更新状态为确认中
        import_task.status = ImportTask.Status.CONFIRMING
        import_task.save()

        # 执行导入
        success, result = import_service.confirm_import(import_task, field_mapping)

        if not success:
            return error_response(message=result)

        return success_response(result, message='数据导入成功')

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """
        回滚导入
        POST /api/v1/imports/{id}/rollback/
        根据快照删除已写入的数据
        """
        import_task = self.get_object()

        success, message = import_service.rollback_import(import_task)

        if not success:
            return error_response(message=message)

        return success_response(message=message)
