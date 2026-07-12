"""
前端错误监控视图（N57 错误监控）
- ErrorLogView / ErrorLogViewSet: 列表 / 创建前端错误日志

接口：
- GET  /api/v1/common/error-logs/        列表（仅管理员/教师可查，可按 level 过滤，分页）
- POST /api/v1/common/error-logs/        创建（任意已登录用户可上报，自动记录 user）
"""
from rest_framework import serializers, status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated

from common.response import success_response
from common.permissions import IsTeacherOrAdmin
from .error_models import ErrorLog


class ErrorLogSerializer(serializers.ModelSerializer):
    """前端错误日志序列化器"""

    level_display = serializers.CharField(source='get_level_display', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True, default='')

    class Meta:
        model = ErrorLog
        fields = (
            'id', 'level', 'level_display',
            'message', 'stack', 'url', 'user_agent',
            'user', 'user_name', 'metadata', 'created_at',
        )
        read_only_fields = ('id', 'user', 'user_name', 'level_display', 'created_at')


class ErrorLogCreateSerializer(serializers.Serializer):
    """前端错误上报请求"""
    level = serializers.ChoiceField(choices=ErrorLog.Level.choices, default='error')
    message = serializers.CharField(max_length=5000)
    stack = serializers.CharField(required=False, allow_blank=True, default='')
    url = serializers.URLField(max_length=500, required=False, allow_blank=True, default='')
    user_agent = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.JSONField(required=False, default=dict)


class ErrorLogViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    前端错误日志视图集
    - GET  /api/v1/common/error-logs/   列表（仅管理员/教师）
    - POST /api/v1/common/error-logs/   创建（任意已登录用户）
    """

    queryset = ErrorLog.objects.all()

    def get_permissions(self):
        """列表仅管理员/教师可查；创建任意已登录用户可上报"""
        if self.action == 'list':
            return [IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ErrorLogCreateSerializer
        return ErrorLogSerializer

    def get_queryset(self):
        queryset = ErrorLog.objects.select_related('user').all()
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        return queryset

    def list(self, request, *args, **kwargs):
        """错误日志列表（分页）"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """上报前端错误日志"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        error_log = ErrorLog.objects.create(
            level=data['level'],
            message=data['message'],
            stack=data.get('stack', ''),
            url=data.get('url', ''),
            user_agent=data.get('user_agent', ''),
            metadata=data.get('metadata', {}),
            user=request.user if request.user.is_authenticated else None,
        )
        return success_response(
            ErrorLogSerializer(error_log).data,
            message='错误日志已记录',
            http_status=status.HTTP_201_CREATED,
        )


# 兼容命名：ErrorLogView 即 ErrorLogViewSet
ErrorLogView = ErrorLogViewSet
