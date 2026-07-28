"""
N33: 文件分享链接视图
- FileShareLinkViewSet: 创建分享链接、令牌访问、撤销
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.storage import protected_media_response
from common.mixins import MultiSerializerMixin, MultiPermissionMixin
from .audit import record_download_audit
from .models import FileAsset
from .permissions import scope_file_queryset, user_can_access_file
from .share_models import FileShareLink
from .share_serializers import (
    FileShareLinkSerializer,
    FileShareLinkCreateSerializer,
)


class FileShareLinkViewSet(
    MultiSerializerMixin,
    MultiPermissionMixin,
    ModelViewSet,
):
    """
    文件分享链接管理 ViewSet
    - list: 查看当前用户创建的分享链接
    - retrieve: 查看分享链接详情
    - create: 创建分享链接（body: file, expire_at, max_views）
    - revoke: 撤销分享链接
    - access: 通过令牌访问文件（无需认证）
    - download: 通过令牌下载文件（无需认证）
    """
    queryset = FileShareLink.objects.all().select_related('file', 'created_by')

    serializer_classes_by_action = {
        'list': FileShareLinkSerializer,
        'retrieve': FileShareLinkSerializer,
        'create': FileShareLinkCreateSerializer,
    }

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'destroy': [IsAuthenticated],
        'revoke': [IsAuthenticated],
        'access': [AllowAny],
        'download': [AllowAny],
    }

    filterset_fields = ['file', 'created_by', 'is_active']
    ordering_fields = ['created_at', 'view_count']

    def get_queryset(self):
        """分享管理列表与文件中心使用同一登录态组织边界。"""
        queryset = super().get_queryset().exclude(
            file__level=FileAsset.Level.SENSITIVE
        )
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        visible_file_ids = scope_file_queryset(
            FileAsset.objects.all(),
            user,
        ).values_list('id', flat=True)
        queryset = queryset.filter(file_id__in=visible_file_ids)
        if user.global_role in ['sys_admin', 'teacher']:
            return queryset
        return queryset.filter(created_by=user)

    def create(self, request, *args, **kwargs):
        """创建文件分享链接"""
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        file_id = input_serializer.validated_data['file']
        try:
            with transaction.atomic():
                file_asset = FileAsset.objects.select_for_update().get(id=file_id)
                if file_asset.level == FileAsset.Level.SENSITIVE:
                    return error_response(
                        message='敏感文件禁止创建公开分享链接',
                        code=1003,
                        http_status=status.HTTP_403_FORBIDDEN,
                    )
                if not user_can_access_file(request.user, file_asset):
                    return error_response(
                        message='无权访问该文件，不能创建分享链接',
                        code=1003,
                        http_status=status.HTTP_403_FORBIDDEN,
                    )
                share_link = FileShareLink.objects.create(
                    file=file_asset,
                    created_by=request.user,
                    token=FileShareLink.generate_token(),
                    expire_at=input_serializer.validated_data.get('expire_at'),
                    max_views=input_serializer.validated_data.get('max_views'),
                )
        except FileAsset.DoesNotExist:
            return error_response(
                message='文件不存在', code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError:
            return error_response(
                message='敏感文件禁止创建公开分享链接',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return success_response(
            FileShareLinkSerializer(share_link, context={'request': request}).data,
            message='分享链接创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """删除分享链接（仅创建人或管理员）"""
        instance = self.get_object()
        if not self._can_manage(request.user, instance):
            return error_response(
                message='无权删除此分享链接',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return success_response(message='分享链接已删除')

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        撤销分享链接（设为无效）
        POST /api/v1/files/shares/{id}/revoke/
        """
        share_link = self.get_object()
        if not self._can_manage(request.user, share_link):
            return error_response(
                message='无权撤销此分享链接',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        share_link.is_active = False
        share_link.save(update_fields=['is_active'])
        return success_response(
            FileShareLinkSerializer(share_link, context={'request': request}).data,
            message='分享链接已撤销',
        )

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def access(self, request):
        """
        通过令牌访问分享链接（无需认证）
        GET /api/v1/files/shares/access/?token=xxx
        返回文件信息并增加访问次数
        """
        token = request.query_params.get('token', '').strip()
        if not token:
            return error_response(message='请提供 token 参数', code=1005)

        share_link, failure = self._consume_view(token)
        if failure:
            return self._share_error(failure)

        file_asset = share_link.file
        return success_response({
            'share_id': share_link.id,
            'view_count': share_link.view_count,
            'file': {
                'id': file_asset.id,
                'name': file_asset.name,
                'size': file_asset.size,
                'content_type': file_asset.content_type,
            },
        })

    @action(detail=False, methods=['get'], url_path='download', permission_classes=[AllowAny])
    def download(self, request):
        """
        通过令牌下载分享文件（无需认证）
        GET /api/v1/files/shares/download/?token=xxx
        """
        token = request.query_params.get('token', '').strip()
        if not token:
            record_download_audit(
                request,
                module='files',
                object_type='FileShareLink',
                object_id='',
                channel='share',
                is_success=False,
                response_status=status.HTTP_400_BAD_REQUEST,
            )
            return error_response(message='请提供 token 参数', code=1005)

        try:
            share_link = FileShareLink.objects.select_related('file').get(token=token)
        except FileShareLink.DoesNotExist:
            record_download_audit(
                request,
                module='files',
                object_type='FileShareLink',
                object_id='',
                channel='share',
                is_success=False,
                response_status=status.HTTP_404_NOT_FOUND,
            )
            return error_response(
                message='分享链接不存在', code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if share_link.file.level == FileAsset.Level.SENSITIVE:
            record_download_audit(
                request,
                module='files',
                object_type='FileShareLink',
                object_id=share_link.id,
                channel='share',
                is_success=False,
                response_status=status.HTTP_403_FORBIDDEN,
            )
            return error_response(
                message='敏感文件禁止通过公开分享下载',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if not share_link.is_valid:
            if not share_link.is_active:
                msg, code = '分享链接已撤销', 1008
            elif share_link.is_expired:
                msg, code = '分享链接已过期', 1009
            else:
                msg, code = '分享链接访问次数已达上限', 1010
            record_download_audit(
                request,
                module='files',
                object_type='FileShareLink',
                object_id=share_link.id,
                channel='share',
                is_success=False,
                response_status=status.HTTP_403_FORBIDDEN,
            )
            return error_response(message=msg, code=code,
                                  http_status=status.HTTP_403_FORBIDDEN)

        file_asset = share_link.file
        if not file_asset.file:
            record_download_audit(
                request,
                module='files',
                object_type='FileShareLink',
                object_id=share_link.id,
                channel='share',
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
                object_type='FileShareLink',
                object_id=share_link.id,
                channel='share',
                is_success=False,
                response_status=status.HTTP_404_NOT_FOUND,
            )
            raise

        share_link, failure = self._consume_view(token)
        if failure:
            record_download_audit(
                request,
                module='files',
                object_type='FileShareLink',
                object_id=share_link.id if share_link else '',
                channel='share',
                is_success=False,
                response_status=(
                    status.HTTP_404_NOT_FOUND
                    if failure == 'missing'
                    else status.HTTP_403_FORBIDDEN
                ),
            )
            return self._share_error(failure)
        record_download_audit(
            request,
            module='files',
            object_type='FileShareLink',
            object_id=share_link.id,
            channel='share',
        )
        return response

    @staticmethod
    @transaction.atomic
    def _consume_view(token):
        """Validate and consume one access atomically across access/download."""
        try:
            share_link = (
                FileShareLink.objects.select_for_update()
                .select_related('file')
                .get(token=token)
            )
        except FileShareLink.DoesNotExist:
            return None, 'missing'

        if share_link.file.level == FileAsset.Level.SENSITIVE:
            return share_link, 'sensitive'
        if not share_link.is_active or share_link.file.is_deleted:
            return share_link, 'revoked'
        if share_link.is_expired:
            return share_link, 'expired'
        if share_link.is_view_limit_reached:
            return share_link, 'limit'

        share_link.view_count = (share_link.view_count or 0) + 1
        share_link.save(update_fields=['view_count'])
        return share_link, None

    @staticmethod
    def _share_error(failure):
        if failure == 'missing':
            return error_response(
                message='分享链接不存在', code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        if failure == 'sensitive':
            return error_response(
                message='敏感文件禁止通过公开分享访问', code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        message, code = {
            'revoked': ('分享链接已撤销', 1008),
            'expired': ('分享链接已过期', 1009),
            'limit': ('分享链接访问次数已达上限', 1010),
        }[failure]
        return error_response(
            message=message,
            code=code,
            http_status=status.HTTP_403_FORBIDDEN,
        )

    @staticmethod
    def _can_manage(user, share_link):
        """判断用户是否可管理分享链接"""
        if not user.is_authenticated:
            return False
        if user.global_role in ['sys_admin', 'teacher']:
            return True
        return share_link.created_by_id == user.id
