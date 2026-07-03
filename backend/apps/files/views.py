"""
文件视图
- FileAssetViewSet: 文件上传/列表/详情/下载
三级权限: public / internal / sensitive
"""
import os
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from .models import FileAsset
from .serializers import FileAssetSerializer, FileAssetListSerializer
from .permissions import FileUploadPermission, FileDownloadPermission


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

        # 普通成员：获取用户参与的项目ID列表 + 负责的项目ID列表
        member_project_ids = list(
            ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
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
            if file_asset.level == 'sensitive':
                return error_response(
                    message='敏感文件需通过审批流程才能下载，请提交访问申请',
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
            raise Http404('文件不存在')

        try:
            file_handle = open(file_asset.file.path, 'rb')
            response = FileResponse(file_handle, as_attachment=True, filename=file_asset.name)
            return response
        except FileNotFoundError:
            raise Http404('文件未找到')
