"""Process-local request and database performance sampling.

The collector intentionally stores a bounded, non-persistent window. It gives
operators truthful live diagnostics without retaining request bodies, query
parameters, or database parameter values.
"""
from __future__ import annotations

import math
import re
import threading
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.db import connection


_WHITESPACE_RE = re.compile(r'\s+')
_SQL_STRING_LITERAL_RE = re.compile(r"(?i)(?:N)?'(?:''|[^'])*'")
_SQL_NUMBER_LITERAL_RE = re.compile(r'(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w.])')


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _safe_sql_summary(sql: str) -> str:
    """Keep query shape only; parameters are never recorded."""
    redacted = _SQL_STRING_LITERAL_RE.sub("'?'", sql)
    redacted = _SQL_NUMBER_LITERAL_RE.sub('?', redacted)
    compact = _WHITESPACE_RE.sub(' ', redacted).strip()
    return compact[:500]


@dataclass(frozen=True)
class RequestSample:
    timestamp: str
    monotonic_time: float
    method: str
    path: str
    status_code: int
    duration_ms: float
    query_count: int
    query_time_ms: float


@dataclass(frozen=True)
class SlowQuerySample:
    timestamp: str
    method: str
    path: str
    duration_ms: float
    sql: str


class QueryCollector:
    def __init__(self, threshold_seconds: float):
        self.threshold_seconds = threshold_seconds
        self.count = 0
        self.total_seconds = 0.0
        self.slow_queries: list[tuple[float, str]] = []

    def __call__(self, execute, sql, params, many, context):
        started = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            elapsed = time.perf_counter() - started
            self.count += 1
            self.total_seconds += elapsed
            if elapsed >= self.threshold_seconds:
                self.slow_queries.append((elapsed, _safe_sql_summary(sql)))


class PerformanceRegistry:
    def __init__(self):
        sample_limit = int(getattr(settings, 'PERFORMANCE_SAMPLE_LIMIT', 500))
        slow_limit = int(getattr(settings, 'PERFORMANCE_SLOW_QUERY_LIMIT', 100))
        self._samples: deque[RequestSample] = deque(maxlen=max(10, sample_limit))
        self._slow_queries: deque[SlowQuerySample] = deque(maxlen=max(10, slow_limit))
        self._lock = threading.Lock()

    def record(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        collector: QueryCollector,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        sample = RequestSample(
            timestamp=now,
            monotonic_time=time.monotonic(),
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 3),
            query_count=collector.count,
            query_time_ms=round(collector.total_seconds * 1000, 3),
        )
        slow_queries = [
            SlowQuerySample(
                timestamp=now,
                method=method,
                path=path,
                duration_ms=round(duration * 1000, 3),
                sql=sql,
            )
            for duration, sql in collector.slow_queries
        ]
        with self._lock:
            self._samples.append(sample)
            self._slow_queries.extend(slow_queries)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            samples = list(self._samples)
        durations = [sample.duration_ms for sample in samples]
        query_times = [sample.query_time_ms for sample in samples]
        query_count = sum(sample.query_count for sample in samples)
        now = time.monotonic()
        recent = [sample for sample in samples if now - sample.monotonic_time <= 60]
        errors = sum(sample.status_code >= 500 for sample in samples)
        status_codes = Counter(str(sample.status_code) for sample in samples)
        return {
            'request_count': len(samples),
            'window_capacity': self._samples.maxlen,
            'requests_per_minute': len(recent),
            'avg_response_time_ms': round(sum(durations) / len(durations), 3) if durations else 0.0,
            'p50_response_time_ms': round(_percentile(durations, 0.50), 3),
            'p95_response_time_ms': round(_percentile(durations, 0.95), 3),
            'p99_response_time_ms': round(_percentile(durations, 0.99), 3),
            'query_count': query_count,
            'avg_query_count': round(query_count / len(samples), 3) if samples else 0.0,
            'avg_query_time_ms': round(sum(query_times) / len(query_times), 3) if query_times else 0.0,
            'error_rate': round(errors / len(samples), 4) if samples else 0.0,
            'status_codes': dict(sorted(status_codes.items())),
            'cache_hit_rate': None,
            'cache_metrics_available': False,
            'collected_at': datetime.now(timezone.utc).isoformat(),
        }

    def slow_query_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            values = list(self._slow_queries)
        values.sort(key=lambda item: item.duration_ms, reverse=True)
        return [asdict(value) for value in values]

    def reset(self) -> None:
        with self._lock:
            self._samples.clear()
            self._slow_queries.clear()


performance_registry = PerformanceRegistry()


class PerformanceMetricsMiddleware:
    """Measure real request and SQL timings for a bounded in-memory window."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        threshold = float(getattr(settings, 'PERFORMANCE_SLOW_QUERY_SECONDS', 0.5))
        collector = QueryCollector(threshold)
        started = time.perf_counter()
        status_code = 500
        try:
            with connection.execute_wrapper(collector):
                response = self.get_response(request)
            status_code = response.status_code
            return response
        finally:
            performance_registry.record(
                method=request.method,
                path=request.path,
                status_code=status_code,
                duration_ms=(time.perf_counter() - started) * 1000,
                collector=collector,
            )
