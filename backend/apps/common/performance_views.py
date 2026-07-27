"""Bounded live performance diagnostics for system administrators."""
from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.views import APIView

from apps.common.performance_metrics import performance_registry
from common.permissions import IsSysAdmin
from common.response import success_response
from common.schema import success_response_schema

# 慢查询阈值（秒）
SLOW_QUERY_THRESHOLD = 0.5


class PerformanceMetricsView(APIView):
    """
    性能指标
    GET /api/v1/common/performance/metrics/
    返回当前请求周期内的查询数、平均响应时间、缓存命中率等指标
    """

    permission_classes = [IsSysAdmin]

    @extend_schema(
        responses={
            200: success_response_schema(
                'PerformanceMetricsResponse',
                inline_serializer(
                    name='PerformanceMetricsData',
                    fields={
                        'request_count': serializers.IntegerField(),
                        'window_capacity': serializers.IntegerField(),
                        'requests_per_minute': serializers.IntegerField(),
                        'avg_response_time_ms': serializers.FloatField(),
                        'p50_response_time_ms': serializers.FloatField(),
                        'p95_response_time_ms': serializers.FloatField(),
                        'p99_response_time_ms': serializers.FloatField(),
                        'query_count': serializers.IntegerField(),
                        'avg_query_count': serializers.FloatField(),
                        'avg_query_time_ms': serializers.FloatField(),
                        'error_rate': serializers.FloatField(),
                        'status_codes': serializers.DictField(
                            child=serializers.IntegerField(),
                        ),
                        'cache_hit_rate': serializers.FloatField(allow_null=True),
                        'cache_metrics_available': serializers.BooleanField(),
                        'collected_at': serializers.DateTimeField(),
                        'debug_mode': serializers.BooleanField(),
                        'slow_query_threshold_seconds': serializers.FloatField(),
                        'note': serializers.CharField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        data = performance_registry.snapshot()
        data.update({
            'debug_mode': settings.DEBUG,
            'slow_query_threshold_seconds': float(
                getattr(settings, 'PERFORMANCE_SLOW_QUERY_SECONDS', SLOW_QUERY_THRESHOLD)
            ),
            'note': '实时指标来自当前服务进程的有界采样窗口；缓存命中率未接入时返回 null。',
        })
        return success_response(data)


class SlowQueryLogView(APIView):
    """
    慢查询日志
    GET /api/v1/common/performance/slow-queries/
    从请求采集中间件的进程内有界窗口读取超过阈值的慢查询
    """

    permission_classes = [IsSysAdmin]

    @extend_schema(
        responses={
            200: success_response_schema(
                'SlowQueryLogResponse',
                inline_serializer(
                    name='SlowQueryLogData',
                    fields={
                        'slow_queries': inline_serializer(
                            name='SlowQuerySample',
                            fields={
                                'timestamp': serializers.DateTimeField(),
                                'method': serializers.CharField(),
                                'path': serializers.CharField(),
                                'duration_ms': serializers.FloatField(),
                                'sql': serializers.CharField(),
                            },
                            many=True,
                        ),
                        'total': serializers.IntegerField(),
                        'threshold_seconds': serializers.FloatField(),
                        'source': serializers.CharField(),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        slow_queries = performance_registry.slow_query_snapshot()

        return success_response({
            'slow_queries': slow_queries,
            'total': len(slow_queries),
            'threshold_seconds': float(
                getattr(settings, 'PERFORMANCE_SLOW_QUERY_SECONDS', SLOW_QUERY_THRESHOLD)
            ),
            'source': 'request_middleware',
        })
