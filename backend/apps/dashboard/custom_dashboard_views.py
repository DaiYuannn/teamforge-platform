"""
自定义看板视图
- CustomDashboardViewSet: 看板 CRUD + set_default（设为默认）
每个用户只能管理自己的看板；默认看板全局唯一（同一用户仅一条）
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from common.response import success_response, error_response
from .custom_dashboard_models import CustomDashboard
from .custom_dashboard_serializers import CustomDashboardSerializer


class CustomDashboardViewSet(ModelViewSet):
    """
    自定义看板管理 ViewSet
    - list/retrieve/create/update/destroy: 仅操作当前用户的看板
    - set_default: 设为默认看板（取消该用户其他默认）
    """

    serializer_class = CustomDashboardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """仅返回当前用户的看板"""
        return CustomDashboard.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _ensure_single_default(self, user, exclude_id=None):
        """确保同一用户仅有一条默认看板"""
        qs = CustomDashboard.objects.filter(user=user, is_default=True)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        qs.update(is_default=False)

    def create(self, request, *args, **kwargs):
        """创建看板"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dashboard = serializer.save(user=request.user)
        if dashboard.is_default:
            self._ensure_single_default(request.user, exclude_id=dashboard.id)
        return success_response(
            CustomDashboardSerializer(dashboard).data,
            message='看板创建成功',
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """更新看板"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        dashboard = serializer.save()
        if dashboard.is_default:
            self._ensure_single_default(request.user, exclude_id=dashboard.id)
        return success_response(
            CustomDashboardSerializer(dashboard).data,
            message='看板更新成功',
        )

    def destroy(self, request, *args, **kwargs):
        """删除看板"""
        instance = self.get_object()
        instance.delete()
        return success_response(message='看板已删除')

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        设为默认看板
        POST /api/v1/dashboard/custom/{id}/set_default/
        """
        dashboard = self.get_object()
        self._ensure_single_default(request.user, exclude_id=dashboard.id)
        dashboard.is_default = True
        dashboard.save(update_fields=['is_default', 'updated_at'])
        return success_response(
            CustomDashboardSerializer(dashboard).data,
            message='已设为默认看板',
        )

    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        获取当前用户的默认看板
        GET /api/v1/dashboard/custom/default/
        """
        dashboard = CustomDashboard.objects.filter(
            user=request.user, is_default=True
        ).first()
        if not dashboard:
            return error_response(message='未找到默认看板', code=1004)
        return success_response(
            CustomDashboardSerializer(dashboard).data,
            message='success',
        )
