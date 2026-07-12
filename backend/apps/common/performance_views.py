"""
性能监控视图（N59 性能优化）
- PerformanceMetricsView: 返回查询数 / 平均响应时间 / 缓存命中率（桩/模拟数据）
- SlowQueryLogView: 列出慢查询（DEBUG 模式下从 django.db.connection.queries 获取）

接口：
- GET /api/v1/common/performance/metrics/
- GET /api/v1/common/performance/slow-queries/
"""
import time

from django.db import connection
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.permissions import IsTeacherOrAdmin
from common.response import success_response

# 慢查询阈值（秒）
SLOW_QUERY_THRESHOLD = 0.5


class PerformanceMetricsView(APIView):
    """
    性能指标
    GET /api/v1/common/performance/metrics/
    返回当前请求周期内的查询数、平均响应时间、缓存命中率等指标
    """

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        # 查询数（DEBUG 模式下 connection.queries 可用）
        queries = getattr(connection, 'queries', []) if settings.DEBUG else []
        query_count = len(queries)
        if queries:
            avg_query_time = sum(float(q.get('time', 0)) for q in queries) / len(queries)
        else:
            avg_query_time = 0.0

        # 平均响应时间（基于本次请求已耗时，桩指标）
        # 实际生产应从 APM / 中间件采集，此处返回模拟基准值
        avg_response_time_ms = round(120.0 + (query_count * 1.5), 2)

        # 缓存命中率（桩：固定模拟值，生产应采集 cache 命中/未命中计数）
        cache_hit_rate = 0.92

        return success_response({
            'query_count': query_count,
            'avg_query_time_ms': round(avg_query_time * 1000, 3),
            'avg_response_time_ms': avg_response_time_ms,
            'cache_hit_rate': cache_hit_rate,
            'debug_mode': settings.DEBUG,
            'note': '部分指标为桩/模拟数据，生产环境应接入 APM',
            'timestamp': time.time(),
        })


class SlowQueryLogView(APIView):
    """
    慢查询日志
    GET /api/v1/common/performance/slow-queries/
    DEBUG 模式下从 django.db.connection.queries 读取超过阈值的慢查询
    """

    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        if not settings.DEBUG:
            return success_response({
                'slow_queries': [],
                'total': 0,
                'message': '仅 DEBUG 模式下可用',
                'threshold_seconds': SLOW_QUERY_THRESHOLD,
            })

        queries = getattr(connection, 'queries', [])
        slow_queries = [
            {
                'sql': q.get('sql', ''),
                'time': float(q.get('time', 0)),
                'time_ms': round(float(q.get('time', 0)) * 1000, 3),
            }
            for q in queries
            if float(q.get('time', 0)) >= SLOW_QUERY_THRESHOLD
        ]
        slow_queries.sort(key=lambda x: x['time'], reverse=True)

        return success_response({
            'slow_queries': slow_queries,
            'total': len(slow_queries),
            'threshold_seconds': SLOW_QUERY_THRESHOLD,
            'all_queries_count': len(queries),
        })
