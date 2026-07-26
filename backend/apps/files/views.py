"""
文件视图
- FileAssetViewSet: 文件上传/列表/详情/下载
三级权限: public / internal / sensitive
"""
import os

from django.core.files import File
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from common.storage import protected_media_response
from common.project_access import (
    is_external_collaborator,
    scope_project_queryset,
    user_can_access_project,
)
from .models import FileAsset, FileVersion
from .tag_models import FileTag, FileTagRelation
from .serializers import (
    FileAssetSerializer, FileAssetListSerializer, FileVersionSerializer,
    FileTagSerializer, FileTagRelationSerializer, AssignTagsSerializer,
)
from .permissions import (
    FileUploadPermission,
    FileDownloadPermission,
    user_can_access_file,
)
from .audit import record_download_audit


class FileAssetViewSet(MultiSerializerMixin, MultiPermissionMixin, ModelViewSet):
    """
    文件管理 ViewSet
    - list/retrieve: 所有认证用户可查看列表（根据文件级别过滤）
    - create: 上传文件（老师/管理员）
    - download: 下载文件（根据文件级别校验权限）
    - destroy: 删除文件（老师/管理员/上传者）
    """
    queryset = FileAsset.objects.all().order_by('-created_at')

    serializer_classes_by_action = {
        'list': FileAssetListSerializer,
        'retrieve': FileAssetSerializer,
        'create': FileAssetSerializer,
        'update': FileAssetSerializer,
        'partial_update': FileAssetSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [FileUploadPermission],
        'update': [FileUploadPermission],
        'partial_update': [FileUploadPermission],
        'destroy': [FileUploadPermission],
        'download': [IsAuthenticated],
        'check_duplicate': [IsAuthenticated],
        'download_watermarked': [IsAuthenticated],
        'versions': [IsAuthenticated],
        'upload_version': [FileUploadPermission],
        'download_version': [IsAuthenticated],
        'restore_version': [FileUploadPermission],
    }

    filterset_fields = ['project', 'level', 'uploader']
    search_fields = ['name']
    ordering_fields = ['created_at', 'size', 'name']

    def get_queryset(self):
        """
        根据用户角色过滤文件列表
        - 管理员/老师：可查看所有文件
        - 普通成员：只能查看公开文件 + 自己参与项目的内部文件
        """
        from django.db.models import Q
        from apps.projects.models import ProjectMember, Project

        queryset = super().get_queryset()
        user = self.request.user

        # 管理员和老师可查看所有文件
        if user.global_role in ['sys_admin', 'teacher']:
            return queryset
        if is_external_collaborator(user):
            return scope_project_queryset(
                queryset.exclude(level=FileAsset.Level.SENSITIVE),
                user,
                project_lookup='project',
            )

        # 普通成员：获取用户参与的项目ID列表 + 负责的项目ID列表
        member_project_ids = list(
            ProjectMember.objects.filter(
                user=user, status=ProjectMember.Status.ACTIVE
            ).values_list('project_id', flat=True)
        )
        led_project_ids = list(
            Project.objects.filter(leader=user).values_list('id', flat=True)
        )
        all_project_ids = member_project_ids + led_project_ids

        # 公开文件 + 自己项目的内部文件（不含敏感文件）
        return queryset.filter(
            Q(level='public') |
            (Q(level='internal') & Q(project_id__in=all_project_ids))
        )

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if is_external_collaborator(request.user) and not user_can_access_file(
            request.user,
            obj,
        ):
            self.permission_denied(request, message='无权访问该文件')

    def create(self, request, *args, **kwargs):
        """上传文件"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取上传的文件
        file = serializer.validated_data.get('file')
        if file:
            # 自动填充文件信息
            serializer.validated_data['size'] = file.size
            serializer.validated_data['content_type'] = file.content_type or ''
            if not serializer.validated_data.get('name'):
                serializer.validated_data['name'] = file.name

        # 设置上传人
        file_asset = serializer.save(uploader=request.user)

        return success_response(
            FileAssetSerializer(file_asset, context={'request': request}).data,
            message='文件上传成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新文件信息"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        file_asset = serializer.save()
        return success_response(
            FileAssetSerializer(file_asset, context={'request': request}).data,
            message='文件更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除文件"""
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        # 删除物理文件
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()
        return success_response(message='文件删除成功')

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        下载文件
        GET /api/v1/files/{id}/download/
        根据文件级别校验下载权限:
        - public: IsAuthenticated
        - internal: IsProjectMember
        - sensitive: 走审批流程（第三期实现）
        """
        file_asset = self.get_object()

        # 校验下载权限
        permission = FileDownloadPermission()
        if not permission.has_object_permission(request, self, file_asset):
            record_download_audit(
                request,
                module='files',
                object_type='FileAsset',
                object_id=file_asset.id,
                channel='direct',
                is_success=False,
                response_status=status.HTTP_403_FORBIDDEN,
            )
            if file_asset.level == 'sensitive':
                return error_response(
                    message='敏感文件只能通过已批准申请或审计下载入口获取',
                    code=1003,
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            return error_response(
                message='权限不足，无法下载此文件',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        # 返回文件
        if not file_asset.file:
            record_download_audit(
                request,
                module='files',
                object_type='FileAsset',
                object_id=file_asset.id,
                channel='direct',
                is_success=False,
                response_status=status.HTTP_404_NOT_FOUND,
            )
            raise Http404('文件不存在')

        try:
            response = protected_media_response(
                file_asset.file.name,
                as_attachment=True,
                download_name=file_asset.name,
            )
        except Http404:
            record_download_audit(
                request,
                module='files',
                object_type='FileAsset',
                object_id=file_asset.id,
                channel='direct',
                is_success=False,
                response_status=status.HTTP_404_NOT_FOUND,
            )
            raise
        record_download_audit(
            request,
            module='files',
            object_type='FileAsset',
            object_id=file_asset.id,
            channel='direct',
        )
        return response

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        获取文件版本列表
        GET /api/v1/files/{id}/versions/
        """
        file_asset = self.get_object()
        versions = FileVersion.objects.filter(file_asset=file_asset)
        serializer = FileVersionSerializer(versions, many=True, context={'request': request})
        return success_response(serializer.data)

    @action(detail=True, methods=['post'], url_path='upload-version')
    def upload_version(self, request, pk=None):
        """
        上传文件新版本
        POST /api/v1/files/{id}/upload-version/
        """
        file_asset = self.get_object()
        self.check_object_permissions(request, file_asset)

        upload_file = request.FILES.get('file')
        if not upload_file:
            return error_response(message='请上传文件', code=1005)

        # 保存旧版本
        current_version = file_asset.version or 1
        if file_asset.file:
            FileVersion.objects.create(
                file_asset=file_asset,
                file=file_asset.file,
                version=current_version,
                uploader=file_asset.uploader,
            )

        # 更新为新版本
        file_asset.file = upload_file
        file_asset.version = current_version + 1
        file_asset.size = upload_file.size
        file_asset.content_type = upload_file.content_type or ''
        file_asset.uploader = request.user
        file_asset.save(update_fields=['file', 'version', 'size', 'content_type', 'uploader', 'updated_at'])

        return success_response(
            FileAssetSerializer(file_asset, context={'request': request}).data,
            message=f'文件已更新至 v{file_asset.version}',
        )

    @action(detail=True, methods=['get'], url_path=r'versions/(?P<version_id>\d+)/download')
    def download_version(self, request, pk=None, version_id=None):
        """
        下载历史版本
        GET /api/v1/files/{id}/versions/{version_id}/download/
        """
        file_asset = self.get_object()
        try:
            version = FileVersion.objects.get(id=version_id, file_asset=file_asset)
        except FileVersion.DoesNotExist:
            raise Http404('版本不存在')

        # 校验下载权限
        permission = FileDownloadPermission()
        if not permission.has_object_permission(request, self, file_asset):
            record_download_audit(
                request,
                module='files',
                object_type='FileVersion',
                object_id=version.id,
                channel='version',
                is_success=False,
                response_status=status.HTTP_403_FORBIDDEN,
            )
            return error_response(
                message='权限不足，无法下载此文件版本',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if not version.file:
            record_download_audit(
                request,
                module='files',
                object_type='FileVersion',
                object_id=version.id,
                channel='version',
                is_success=False,
                response_status=status.HTTP_404_NOT_FOUND,
            )
            raise Http404('版本文件不存在')

        try:
            response = protected_media_response(
                version.file.name,
                as_attachment=True,
                download_name=f'{file_asset.name}_v{version.version}',
            )
        except Http404:
            record_download_audit(
                request,
                module='files',
                object_type='FileVersion',
                object_id=version.id,
                channel='version',
                is_success=False,
                response_status=status.HTTP_404_NOT_FOUND,
            )
            raise
        record_download_audit(
            request,
            module='files',
            object_type='FileVersion',
            object_id=version.id,
            channel='version',
        )
        return response

    @action(detail=True, methods=['post'], url_path=r'versions/(?P<version_id>\d+)/restore')
    def restore_version(self, request, pk=None, version_id=None):
        """恢复历史版本，并将恢复结果保存为新的当前版本。"""
        file_asset = self.get_object()
        self.check_object_permissions(request, file_asset)
        try:
            selected_version = FileVersion.objects.get(
                id=version_id, file_asset=file_asset
            )
        except FileVersion.DoesNotExist:
            raise Http404('版本不存在')
        if not selected_version.file:
            raise Http404('版本文件不存在')

        current_version = file_asset.version or 1
        if file_asset.file:
            FileVersion.objects.create(
                file_asset=file_asset,
                file=file_asset.file,
                version=current_version,
                uploader=file_asset.uploader,
            )

        try:
            selected_version.file.open('rb')
            restored_name = os.path.basename(
                file_asset.name or selected_version.file.name
            )
            file_asset.file.save(
                restored_name, File(selected_version.file), save=False
            )
        except FileNotFoundError:
            raise Http404('版本文件未找到')
        finally:
            try:
                selected_version.file.close()
            except Exception:
                pass

        file_asset.version = current_version + 1
        file_asset.size = file_asset.file.size
        file_asset.content_type = ''
        file_asset.uploader = request.user
        file_asset.save(update_fields=[
            'file', 'version', 'size', 'content_type', 'uploader', 'updated_at',
        ])
        return success_response(
            FileAssetSerializer(file_asset, context={'request': request}).data,
            message=f'已将 v{selected_version.version} 恢复为新的 v{file_asset.version}',
        )

    @action(detail=True, methods=['get'], url_path='check-duplicate')
    def check_duplicate(self, request, pk=None):
        """
        检查文件重复（基于 SHA-256 哈希）
        GET /api/v1/files/{id}/check-duplicate/
        返回与当前文件哈希相同（排除自身）的文件列表
        """
        file_asset = self.get_object()
        if not file_asset.file_hash:
            return success_response({
                'has_duplicate': False,
                'duplicates': [],
                'message': '该文件尚未计算哈希，无法查重',
            })
        duplicates = self.get_queryset().filter(
            file_hash=file_asset.file_hash
        ).exclude(pk=file_asset.pk).values('id', 'name', 'project_id', 'uploader_id', 'created_at')
        dup_list = list(duplicates)
        return success_response({
            'has_duplicate': len(dup_list) > 0,
            'duplicates': dup_list,
            'file_hash': file_asset.file_hash,
            'count': len(dup_list),
        })

    @action(detail=True, methods=['get'], url_path='download-watermarked')
    def download_watermarked(self, request, pk=None):
        """
        下载带水印的图片
        GET /api/v1/files/{id}/download-watermarked/?text=水印文字
        - 优先使用查询参数 text 作为水印文字，否则使用文件自身的 watermark_text
        - 仅支持图片文件，非图片返回 400
        """
        from .watermark_service import add_text_watermark, is_image_file

        file_asset = self.get_object()

        # 校验下载权限
        permission = FileDownloadPermission()
        if not permission.has_object_permission(request, self, file_asset):
            record_download_audit(
                request,
                module='files',
                object_type='FileAsset',
                object_id=file_asset.id,
                channel='watermarked',
                is_success=False,
                response_status=status.HTTP_403_FORBIDDEN,
            )
            return error_response(
                message='权限不足，无法下载此文件',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if not file_asset.file:
            record_download_audit(
                request,
                module='files',
                object_type='FileAsset',
                object_id=file_asset.id,
                channel='watermarked',
                is_success=False,
                response_status=status.HTTP_404_NOT_FOUND,
            )
            raise Http404('文件不存在')

        # 水印文字：优先查询参数，其次文件自身字段
        watermark_text = (
            request.query_params.get('text', '').strip()
            or (file_asset.watermark_text or '').strip()
        )
        if not watermark_text:
            record_download_audit(
                request,
                module='files',
                object_type='FileAsset',
                object_id=file_asset.id,
                channel='watermarked',
                is_success=False,
                response_status=status.HTTP_400_BAD_REQUEST,
            )
            return error_response(
                message='请提供水印文字（通过 text 参数或设置文件 watermark_text 字段）',
                code=1005,
            )

        # 非图片文件无法加水印
        if not is_image_file(file_asset.name, file_asset.content_type):
            record_download_audit(
                request,
                module='files',
                object_type='FileAsset',
                object_id=file_asset.id,
                channel='watermarked',
                is_success=False,
                response_status=status.HTTP_400_BAD_REQUEST,
            )
            return error_response(
                message='仅支持对图片文件添加水印',
                code=1006,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        watermarked_io = add_text_watermark(file_asset.file, watermark_text)
        if watermarked_io is None:
            record_download_audit(
                request,
                module='files',
                object_type='FileAsset',
                object_id=file_asset.id,
                channel='watermarked',
                is_success=False,
                response_status=status.HTTP_400_BAD_REQUEST,
            )
            return error_response(
                message='无法为该文件添加水印（可能缺少 Pillow 或文件损坏）',
                code=1007,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        # 返回水印图片（PNG 格式）
        from django.http import HttpResponse
        response = HttpResponse(watermarked_io, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="watermarked_{file_asset.name}.png"'
        record_download_audit(
            request,
            module='files',
            object_type='FileAsset',
            object_id=file_asset.id,
            channel='watermarked',
        )
        return response


class FileTagViewSet(ModelViewSet):
    """
    文件标签管理 ViewSet
    - CRUD: 标签的增删改查
    - assign:   POST /api/v1/files/tags/assign/     给文件分配标签
    - unassign: POST /api/v1/files/tags/unassign/   取消文件的标签
    - by_file:  GET  /api/v1/files/tags/by_file/?file=<id>  获取文件的标签列表
    """
    queryset = FileTag.objects.all().order_by('-created_at')
    serializer_class = FileTagSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['project', 'created_by']
    search_fields = ['name']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        """内部成员透明读取；外部协作者仅可见获授权项目标签。"""
        queryset = scope_project_queryset(
            super().get_queryset(),
            self.request.user,
            project_lookup='project',
        )
        project = self.request.query_params.get('project')
        if project:
            if project in ('null', ''):
                queryset = queryset.filter(project__isnull=True)
            else:
                queryset = queryset.filter(project_id=project)
        return queryset

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        write = request.method not in ('GET', 'HEAD', 'OPTIONS')
        if not user_can_access_project(request.user, obj.project, write=write):
            self.permission_denied(request, message='无权访问该项目标签')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        """创建标签"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data.get('project')
        if not user_can_access_project(request.user, project, write=True):
            return error_response(
                message='无权在该项目创建标签',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        tag = serializer.save(created_by=request.user)
        return success_response(
            FileTagSerializer(tag, context={'request': request}).data,
            message='标签创建成功',
        )

    def update(self, request, *args, **kwargs):
        """更新标签"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        target_project = serializer.validated_data.get('project', instance.project)
        if not user_can_access_project(
            request.user,
            target_project,
            write=True,
        ):
            return error_response(
                message='无权将标签移动到该项目',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        tag = serializer.save()
        return success_response(
            FileTagSerializer(tag, context={'request': request}).data,
            message='标签更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除标签（同时删除关联关系）"""
        instance = self.get_object()
        instance.delete()
        return success_response(message='标签删除成功')

    @action(detail=False, methods=['get'], url_path='by-file')
    def by_file(self, request):
        """
        获取文件的标签列表
        GET /api/v1/files/tags/by-file/?file=<id>
        """
        file_id = request.query_params.get('file')
        if not file_id:
            return error_response(message='请提供 file 参数')
        try:
            file_asset = FileAsset.objects.select_related('project').get(id=file_id)
        except FileAsset.DoesNotExist:
            return error_response(
                message='文件不存在',
                code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        if not user_can_access_file(request.user, file_asset):
            return error_response(
                message='无权访问该文件',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        relations = FileTagRelation.objects.filter(
            file=file_asset
        ).select_related('tag', 'file')
        serializer = FileTagRelationSerializer(relations, many=True, context={'request': request})
        return success_response(serializer.data)

    @action(detail=False, methods=['post'])
    def assign(self, request):
        """
        给文件分配标签
        POST /api/v1/files/tags/assign/
        body: {"file": <file_id>, "tags": [<tag_id>, ...]}
        """
        serializer = AssignTagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_id = serializer.validated_data['file']
        tag_ids = serializer.validated_data['tags']

        try:
            file_asset = FileAsset.objects.select_related('project').get(id=file_id)
        except FileAsset.DoesNotExist:
            return error_response(
                message='文件不存在', code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        if (
            not user_can_access_file(request.user, file_asset)
            or not user_can_access_project(
                request.user,
                file_asset.project,
                write=True,
            )
        ):
            return error_response(
                message='无权修改该文件的标签',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        tags = list(self.get_queryset().filter(id__in=tag_ids))
        if len(tags) != len(set(tag_ids)):
            return error_response(
                message='包含不存在或无权使用的标签',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if any(
            tag.project_id not in (None, file_asset.project_id)
            or not user_can_access_project(
                request.user,
                tag.project,
                write=True,
            )
            for tag in tags
        ):
            return error_response(
                message='标签必须属于同一项目且当前用户有权使用',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        created_count = 0
        for tag in tags:
            _, created = FileTagRelation.objects.get_or_create(
                file=file_asset, tag=tag,
            )
            if created:
                created_count += 1

        return success_response(
            {'assigned': created_count, 'total': len(tag_ids)},
            message='标签分配成功',
        )

    @action(detail=False, methods=['post'])
    def unassign(self, request):
        """
        取消文件的标签
        POST /api/v1/files/tags/unassign/
        body: {"file": <file_id>, "tags": [<tag_id>, ...]}
        """
        serializer = AssignTagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_id = serializer.validated_data['file']
        tag_ids = serializer.validated_data['tags']

        try:
            file_asset = FileAsset.objects.select_related('project').get(id=file_id)
        except FileAsset.DoesNotExist:
            return error_response(
                message='文件不存在',
                code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        if (
            not user_can_access_file(request.user, file_asset)
            or not user_can_access_project(
                request.user,
                file_asset.project,
                write=True,
            )
        ):
            return error_response(
                message='无权修改该文件的标签',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        deleted_count, _ = FileTagRelation.objects.filter(
            file=file_asset, tag_id__in=tag_ids,
        ).delete()

        return success_response(
            {'unassigned': deleted_count},
            message='标签取消成功',
        )
