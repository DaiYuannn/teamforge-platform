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

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response


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
}

VALID_TYPES = list(MODEL_MAP.keys())


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


class RecycleBinView(APIView):
    """回收站视图"""
    permission_classes = [IsAuthenticated]

    # ---- GET：回收站列表 ----
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

        serializer_cls = _get_serializer_class(cfg)
        serializer = serializer_cls(deleted_qs, many=True)
        return success_response(serializer.data, message='回收站列表获取成功')

    # ---- POST：恢复 ----
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

        obj.delete()
        return success_response(message=f'{cfg["label"]}已永久删除')
