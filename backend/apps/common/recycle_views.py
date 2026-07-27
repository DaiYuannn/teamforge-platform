"""
回收站视图
支持项目、任务、经费明细的软删除恢复与永久删除。

接口：
- GET    /api/v1/recycle-bin/?type=project      获取回收站列表（仅已软删除对象）
- POST   /api/v1/recycle-bin/                    恢复对象  {"type": "project", "id": 1}
- DELETE /api/v1/recycle-bin/?type=project&id=1  永久删除对象

权限：
- GET（列表）：所有认证用户
- POST（恢复）：老师 / 管理员
- DELETE（永久删除）：仅系统管理员
"""
import importlib

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    PolymorphicProxySerializer,
    extend_schema,
    inline_serializer,
)
from rest_framework import status
from rest_framework import serializers
from rest_framework.views import APIView

from common.permissions import IsInternalTeamMember
from common.response import success_response, error_response
from common.schema import success_response_schema


# 模型映射：type -> 模型与序列化器信息
MODEL_MAP = {
    'project': {
        'module': 'apps.projects.models',
        'model': 'Project',
        'serializer_module': 'apps.projects.serializers',
        'list_serializer': 'ProjectListSerializer',
        'label': '项目',
    },
    'task': {
        'module': 'apps.tasks.models',
        'model': 'Task',
        'serializer_module': 'apps.tasks.serializers',
        'list_serializer': 'TaskListSerializer',
        'label': '任务',
    },
    'finance_expense': {
        'module': 'apps.finance.models',
        'model': 'FinanceExpense',
        'serializer_module': 'apps.finance.serializers',
        'list_serializer': 'FinanceExpenseListSerializer',
        'label': '经费明细',
    },
    'file': {
        'module': 'apps.files.models',
        'model': 'FileAsset',
        'serializer_module': 'apps.files.serializers',
        'list_serializer': 'FileAssetListSerializer',
        'label': '文件',
    },
}

VALID_TYPES = list(MODEL_MAP.keys())


def _recycle_bin_serializers():
    """Load business serializers lazily so schema generation mirrors runtime."""
    return [_get_serializer_class(cfg) for cfg in MODEL_MAP.values()]


def _get_config(model_type):
    """根据类型获取配置"""
    return MODEL_MAP.get(model_type)


def _get_model_class(cfg):
    """根据配置动态加载模型类"""
    module = importlib.import_module(cfg['module'])
    return getattr(module, cfg['model'])


def _get_serializer_class(cfg):
    """根据配置动态加载列表序列化器类"""
    module = importlib.import_module(cfg['serializer_module'])
    return getattr(module, cfg['list_serializer'])


def _get_all_objects_manager(model_cls):
    """获取含已删除对象的 manager（回收站专用）"""
    return getattr(model_cls, 'all_objects', model_cls._default_manager)


def _scope_deleted_queryset(queryset, model_type, user):
    """回收站沿用业务列表的可见范围，避免泄露已删除文件。"""
    if model_type != 'file':
        return queryset

    from django.db.models import Q
    from apps.files.models import FileAsset
    from apps.projects.models import Project, ProjectMember
    from common.project_access import is_external_collaborator, scope_project_queryset

    queryset = queryset.select_related(
        'project', 'folder', 'uploader', 'deleted_by',
    ).prefetch_related('tag_relations__tag')
    if user.global_role in ('sys_admin', 'teacher'):
        return queryset
    if is_external_collaborator(user):
        return scope_project_queryset(
            queryset.exclude(level=FileAsset.Level.SENSITIVE),
            user,
            project_lookup='project',
        )
    member_project_ids = ProjectMember.objects.filter(
        user=user,
        status=ProjectMember.Status.ACTIVE,
    ).values_list('project_id', flat=True)
    led_project_ids = Project.objects.filter(leader=user).values_list('id', flat=True)
    return queryset.filter(
        Q(level=FileAsset.Level.PUBLIC)
        | Q(level=FileAsset.Level.INTERNAL, project_id__in=member_project_ids)
        | Q(level=FileAsset.Level.INTERNAL, project_id__in=led_project_ids)
    ).distinct()


class RecycleBinView(APIView):
    """回收站视图"""
    permission_classes = [IsInternalTeamMember]

    # ---- GET：回收站列表 ----
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=VALID_TYPES,
                default='project',
            ),
        ],
        responses={
            200: success_response_schema(
                'RecycleBinListResponse',
                PolymorphicProxySerializer(
                    component_name='RecycleBinItem',
                    serializers=_recycle_bin_serializers,
                    resource_type_field_name=None,
                    many=True,
                ),
            ),
        },
    )
    def get(self, request):
        """获取回收站列表（仅返回已软删除的对象）"""
        model_type = request.query_params.get('type', 'project')
        cfg = _get_config(model_type)
        if cfg is None:
            return error_response(
                message=f'无效的类型，可选值: {VALID_TYPES}',
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        model_cls = _get_model_class(cfg)
        manager = _get_all_objects_manager(model_cls)
        deleted_qs = manager.filter(is_deleted=True).order_by('-deleted_at')
        deleted_qs = _scope_deleted_queryset(
            deleted_qs, model_type, request.user,
        )

        serializer_cls = _get_serializer_class(cfg)
        serializer = serializer_cls(
            deleted_qs, many=True, context={'request': request},
        )
        return success_response(serializer.data, message='回收站列表获取成功')

    # ---- POST：恢复 ----
    @extend_schema(
        request=inline_serializer(
            name='RecycleBinRestoreRequest',
            fields={
                'type': serializers.ChoiceField(
                    choices=VALID_TYPES, default='project',
                ),
                'id': serializers.IntegerField(),
            },
        ),
        responses={
            200: success_response_schema(
                'RecycleBinRestoreResponse',
                serializers.JSONField(allow_null=True),
            ),
        },
    )
    def post(self, request):
        """恢复对象（从回收站还原）"""
        # 权限校验：恢复操作仅限老师 / 管理员
        if request.user.global_role not in ('teacher', 'sys_admin'):
            return error_response(
                message='权限不足，仅老师或管理员可恢复',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        model_type = request.data.get('type', 'project')
        obj_id = request.data.get('id')

        cfg = _get_config(model_type)
        if cfg is None:
            return error_response(
                message=f'无效的类型，可选值: {VALID_TYPES}',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if not obj_id:
            return error_response(message='请提供 id')

        model_cls = _get_model_class(cfg)
        manager = _get_all_objects_manager(model_cls)
        try:
            obj = manager.get(id=obj_id, is_deleted=True)
        except model_cls.DoesNotExist:
            return error_response(
                message='回收站中未找到该对象',
                code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        obj.restore()
        return success_response(message=f'{cfg["label"]}恢复成功')

    # ---- DELETE：永久删除 ----
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=VALID_TYPES,
                default='project',
            ),
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
        ],
        request=inline_serializer(
            name='RecycleBinDeleteRequest',
            fields={
                'type': serializers.ChoiceField(
                    choices=VALID_TYPES, required=False,
                ),
                'id': serializers.IntegerField(required=False),
            },
        ),
        responses={
            200: success_response_schema(
                'RecycleBinDeleteResponse',
                serializers.JSONField(allow_null=True),
            ),
        },
    )
    def delete(self, request):
        """永久删除（物理删除，不可恢复）"""
        # 权限校验：永久删除仅限系统管理员
        if request.user.global_role != 'sys_admin':
            return error_response(
                message='权限不足，仅系统管理员可永久删除',
                code=1003,
                http_status=status.HTTP_403_FORBIDDEN,
            )

        model_type = request.query_params.get('type') or request.data.get('type', 'project')
        obj_id = request.query_params.get('id') or request.data.get('id')

        cfg = _get_config(model_type)
        if cfg is None:
            return error_response(
                message=f'无效的类型，可选值: {VALID_TYPES}',
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if not obj_id:
            return error_response(message='请提供 id')

        model_cls = _get_model_class(cfg)
        manager = _get_all_objects_manager(model_cls)
        try:
            obj = manager.get(id=obj_id, is_deleted=True)
        except model_cls.DoesNotExist:
            return error_response(
                message='回收站中未找到该对象',
                code=1004,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        if model_type == 'file':
            for version in obj.versions.all():
                if version.file:
                    version.file.delete(save=False)
            if obj.file:
                obj.file.delete(save=False)
        obj.delete()
        return success_response(message=f'{cfg["label"]}已永久删除')
