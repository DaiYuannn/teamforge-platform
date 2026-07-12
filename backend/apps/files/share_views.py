"""
N33: 文件分享链接视图
- FileShareLinkViewSet: 创建分享链接、令牌访问、撤销
"""
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from common.mixins import MultiSerializerMixin
from .models import FileAsset
from .share_models import FileShareLink
from .share_serializers import (
    FileShareLinkSerializer,
    FileShareLinkCreateSerializer,
)


class FileShareLinkViewSet(MultiSerializerMixin, ModelViewSet):
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
        """普通用户只能查看自己创建的分享链接；管理员可查看全部"""
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.global_role in ['sys_admin', 'teacher']:
            return queryset
        return queryset.filter(created_by=user)

    def create(self, request, *args, **kwargs):
        """创建文件分享链接"""
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        file_id = input_serializer.validated_data['file']
        try:
            file_asset = FileAsset.objects.get(id=file_id)
        except FileAsset.DoesNotExist:
            return error_response(
                message='文件不存在', code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        share_link = FileShareLink.objects.create(
            file=file_asset,
            created_by=request.user,
            token=FileShareLink.generate_token(),
            expire_at=input_serializer.validated_data.get('expire_at'),
            max_views=input_serializer.validated_data.get('max_views'),
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

        try:
            share_link = FileShareLink.objects.select_related('file').get(token=token)
        except FileShareLink.DoesNotExist:
            return error_response(
                message='分享链接不存在', code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        # 校验链接有效性
        if not share_link.is_active:
            return error_response(message='分享链接已撤销', code=1008,
                                  http_status=status.HTTP_403_FORBIDDEN)
        if share_link.is_expired:
            return error_response(message='分享链接已过期', code=1009,
                                  http_status=status.HTTP_403_FORBIDDEN)
        if share_link.is_view_limit_reached:
            return error_response(message='分享链接访问次数已达上限', code=1010,
                                  http_status=status.HTTP_403_FORBIDDEN)

        # 增加访问次数
        share_link.view_count = (share_link.view_count or 0) + 1
        share_link.save(update_fields=['view_count'])

        file_asset = share_link.file
        return success_response({
            'share_id': share_link.id,
            'token': share_link.token,
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
            return error_response(message='请提供 token 参数', code=1005)

        try:
            share_link = FileShareLink.objects.select_related('file').get(token=token)
        except FileShareLink.DoesNotExist:
            return error_response(
                message='分享链接不存在', code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if not share_link.is_valid:
            if not share_link.is_active:
                msg, code = '分享链接已撤销', 1008
            elif share_link.is_expired:
                msg, code = '分享链接已过期', 1009
            else:
                msg, code = '分享链接访问次数已达上限', 1010
            return error_response(message=msg, code=code,
                                  http_status=status.HTTP_403_FORBIDDEN)

        # 增加访问次数
        share_link.view_count = (share_link.view_count or 0) + 1
        share_link.save(update_fields=['view_count'])

        file_asset = share_link.file
        if not file_asset.file:
            raise Http404('文件不存在')

        try:
            file_handle = open(file_asset.file.path, 'rb')
            return FileResponse(file_handle, as_attachment=True, filename=file_asset.name)
        except FileNotFoundError:
            raise Http404('文件未找到')

    @staticmethod
    def _can_manage(user, share_link):
        """判断用户是否可管理分享链接"""
        if not user.is_authenticated:
            return False
        if user.global_role in ['sys_admin', 'teacher']:
            return True
        return share_link.created_by_id == user.id
