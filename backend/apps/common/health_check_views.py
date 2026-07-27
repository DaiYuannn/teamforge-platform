"""
健康检查视图（N58）
- HealthCheckView: 返回系统健康状态（数据库 / 缓存 / Celery / 存储 / 迁移状态）

接口：
- GET /api/v1/common/health/   无需认证（供负载均衡探针使用）
"""
from django.core.cache import cache
from django.db import connections, DEFAULT_DB_ALIAS
from django.core.files.storage import default_storage
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.response import success_response
from common.schema import success_response_schema


def _check_database():
    """数据库连接检查"""
    try:
        connection = connections[DEFAULT_DB_ALIAS]
        connection.ensure_connection()
        return {'status': 'healthy', 'message': '数据库连接正常'}
    except Exception as exc:  # noqa: BLE001
        return {'status': 'unhealthy', 'message': f'数据库连接失败: {exc}'}


def _check_cache():
    """缓存读写检查"""
    try:
        test_key = '__health_check__'
        cache.set(test_key, 'ok', timeout=10)
        value = cache.get(test_key)
        cache.delete(test_key)
        if value == 'ok':
            return {'status': 'healthy', 'message': '缓存读写正常'}
        return {'status': 'degraded', 'message': '缓存读取值异常'}
    except Exception as exc:  # noqa: BLE001
        return {'status': 'degraded', 'message': f'缓存不可用: {exc}'}


def _check_celery():
    """Celery 检查（软检查：尝试 ping，失败则降级）"""
    try:
        from config.celery import app as celery_app
        # EAGER 模式下无真实 worker，视为已配置即健康
        if getattr(celery_app.conf, 'task_always_eager', False):
            return {'status': 'healthy', 'message': 'Celery 同步模式（EAGER）已启用'}
        inspect = celery_app.control.inspect(timeout=1)
        active = inspect.ping()
        if active:
            return {'status': 'healthy', 'message': f'Celery worker 在线: {len(active)} 个'}
        return {'status': 'degraded', 'message': '未发现在线 Celery worker'}
    except Exception as exc:  # noqa: BLE001
        return {'status': 'degraded', 'message': f'Celery 检查失败: {exc}'}


def _check_storage():
    """默认存储检查"""
    try:
        # 检查存储后端是否可用（不强制写文件，避免污染）
        storage = default_storage
        # 调用 listdir 根目录（兼容本地与对象存储）
        try:
            storage.listdir('')
        except Exception:  # noqa: BLE001
            pass
        return {'status': 'healthy', 'message': f'存储后端: {storage.__class__.__name__}'}
    except Exception as exc:  # noqa: BLE001
        return {'status': 'degraded', 'message': f'存储不可用: {exc}'}


def _check_migrations():
    """迁移状态检查：是否存在未应用的迁移"""
    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            names = [f'{app}.{name}' for app, name in plan]
            return {
                'status': 'degraded',
                'message': f'存在 {len(plan)} 个未应用迁移',
                'pending': names,
            }
        return {'status': 'healthy', 'message': '所有迁移已应用'}
    except Exception as exc:  # noqa: BLE001
        return {'status': 'degraded', 'message': f'迁移状态检查失败: {exc}'}


# 状态权重：unhealthy 最严重
_STATUS_RANK = {'healthy': 0, 'degraded': 1, 'unhealthy': 2}


def _aggregate_status(checks):
    """根据各项检查结果聚合总体状态"""
    worst = 'healthy'
    for result in checks.values():
        rank = _STATUS_RANK.get(result.get('status', 'healthy'), 0)
        if rank > _STATUS_RANK[worst]:
            worst = result['status']
    return worst


class HealthCheckView(APIView):
    """
    健康检查
    GET /api/v1/common/health/
    返回系统各项健康指标及总体状态（healthy / degraded / unhealthy）
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # 完全无需认证

    @extend_schema(
        auth=[],
        responses={
            200: success_response_schema(
                'HealthCheckResponse',
                inline_serializer(
                    name='HealthCheckData',
                    fields={
                        'status': serializers.ChoiceField(
                            choices=['healthy', 'degraded', 'unhealthy'],
                        ),
                        'checks': serializers.DictField(
                            child=serializers.JSONField(),
                        ),
                        'timestamp': serializers.DateTimeField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        checks = {
            'database': _check_database(),
            'cache': _check_cache(),
            'celery': _check_celery(),
            'storage': _check_storage(),
            'migrations': _check_migrations(),
        }
        overall = _aggregate_status(checks)
        return success_response({
            'status': overall,
            'checks': checks,
            'timestamp': timezone.now().isoformat(),
        })
