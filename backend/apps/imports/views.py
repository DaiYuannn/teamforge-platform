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
from django.db.models import Q

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from apps.common.team_models import Team, TeamMember
from .models import ImportTask
from .serializers import (
    ImportTaskSerializer, ImportTaskListSerializer,
    ImportPreviewSerializer, ImportConfirmSerializer,
    MaterialArchivePreviewSerializer,
)
from .services import import_service
from .material_archive import (
    MaterialArchiveError,
    confirm_material_archive,
    preview_material_archive,
    rollback_material_archive,
)


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
        'preview_materials': MaterialArchivePreviewSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'preview': [IsAuthenticated],
        'confirm': [IsAuthenticated],
        'rollback': [IsAuthenticated],
        'preview_materials': [IsAuthenticated],
        'destroy': [IsAuthenticated],
    }

    filterset_fields = ['module', 'status', 'created_by']
    search_fields = ['module', 'file_path']
    ordering_fields = ['created_at', 'updated_at']

    @staticmethod
    def _managed_team_ids(user):
        membership_ids = TeamMember.objects.filter(
            user=user,
            role__in=[
                TeamMember.Role.OWNER,
                TeamMember.Role.CO_LEAD,
                TeamMember.Role.ADMIN,
            ],
            status=TeamMember.Status.ACTIVE,
        ).values_list('team_id', flat=True)
        direct_ids = set(membership_ids) | set(
            Team.objects.filter(owner=user).values_list('id', flat=True)
        )
        child_ids = Team.objects.filter(
            parent_id__in=direct_ids,
        ).values_list('id', flat=True)
        return direct_ids | set(child_ids)

    def get_queryset(self):
        queryset = super().get_queryset().select_related('team', 'created_by')
        user = self.request.user
        if user.global_role in ['sys_admin', 'teacher']:
            return queryset
        managed_ids = self._managed_team_ids(user)
        # 旧任务没有团队字段；仅原创建人可继续查看和处理。
        return queryset.filter(
            Q(team_id__in=managed_ids)
            | Q(team__isnull=True, created_by=user)
        ).distinct()

    def update(self, request, *args, **kwargs):
        return error_response(
            message='导入任务不可直接修改，请重新上传预览',
            code=2407,
            http_status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

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
        team_id = serializer.validated_data.get('team')
        custom_mapping = serializer.validated_data.get('field_mapping', {})

        managed_ids = self._managed_team_ids(request.user)
        team = Team.objects.filter(pk=team_id).first() if team_id else None
        if team_id and team is None:
            return error_response(message='所选团队不存在', http_status=status.HTTP_400_BAD_REQUEST)
        if (
            team
            and request.user.global_role not in ['sys_admin', 'teacher']
            and team.id not in managed_ids
        ):
            return error_response(
                message='只有团队主负责人、共同负责人或管理员可以向该团队导入数据',
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if team is None and len(managed_ids) == 1:
            team = Team.objects.filter(pk=next(iter(managed_ids))).first()
        if team is None and request.user.global_role not in ['sys_admin', 'teacher']:
            return error_response(
                message='只有团队负责人或管理员可以导入数据',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

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
            team=team,
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

    @action(detail=False, methods=['post'], url_path='preview-materials')
    def preview_materials(self, request):
        """Securely validate a ZIP + manifest.json material package."""
        serializer = MaterialArchivePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data['file']
        team = Team.objects.filter(pk=serializer.validated_data['team']).first()
        if team is None:
            return error_response(message='所选团队不存在', http_status=status.HTTP_400_BAD_REQUEST)
        managed_ids = self._managed_team_ids(request.user)
        if (
            request.user.global_role not in ['sys_admin', 'teacher']
            and team.id not in managed_ids
        ):
            return error_response(
                message='只有团队主负责人、共同负责人、管理员或操作老师可以导入资料包',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'imports', 'materials')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = get_valid_filename(os.path.basename(uploaded_file.name))
        file_path = os.path.join(upload_dir, f'{uuid.uuid4().hex}_{safe_name}')
        with open(file_path, 'wb') as target:
            for chunk in uploaded_file.chunks():
                target.write(chunk)
        try:
            preview = preview_material_archive(
                file_path,
                team=team,
                operator=request.user,
            )
        except MaterialArchiveError as exc:
            if os.path.exists(file_path):
                os.remove(file_path)
            return error_response(
                message=f'资料包安全校验失败: {exc}',
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        import_task = ImportTask.objects.create(
            module=ImportTask.Module.MATERIALS,
            file_path=file_path,
            status=ImportTask.Status.PREVIEWED,
            preview_data={
                'archive_sha256': preview['archive_sha256'],
                'rows': preview['rows'][:200],
                'manifest_version': 1,
            },
            total_rows=preview['total_rows'],
            valid_rows=preview['valid_rows'],
            error_rows=preview['error_rows'],
            error_details=preview['errors'],
            created_by=request.user,
            team=team,
        )
        return success_response({
            'task_id': import_task.id,
            'headers': [],
            'field_mapping': {},
            'field_options': [],
            'preview_rows': preview['rows'],
            'total_rows': preview['total_rows'],
            'valid_rows': preview['valid_rows'],
            'error_rows': preview['error_rows'],
            'error_details': preview['errors'],
            'archive_sha256': preview['archive_sha256'],
        }, message='资料包安全校验完成，请确认后导入')

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

        if import_task.module == ImportTask.Module.MATERIALS:
            try:
                result = confirm_material_archive(import_task, operator=request.user)
            except MaterialArchiveError as exc:
                import_task.status = ImportTask.Status.PREVIEWED
                import_task.save(update_fields=['status', 'updated_at'])
                return error_response(
                    message=str(exc),
                    http_status=status.HTTP_400_BAD_REQUEST,
                )
            return success_response(result, message='资料包导入成功')

        # 执行结构化表格导入
        success, result = import_service.confirm_import(
            import_task,
            field_mapping,
            operator=request.user,
        )

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

        if import_task.module == ImportTask.Module.MATERIALS:
            if import_task.status != ImportTask.Status.CONFIRMED:
                return error_response(message='只能回滚已确认的资料包导入任务')
            message = rollback_material_archive(import_task)
            return success_response(message=message)

        success, message = import_service.rollback_import(import_task)

        if not success:
            return error_response(message=message)

        return success_response(message=message)
