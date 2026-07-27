"""
N59: 性能监控测试
- GET /api/v1/common/performance/metrics/
- GET /api/v1/common/performance/slow-queries/
"""
import pytest

from apps.common.performance_metrics import _safe_sql_summary


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


def test_sql_summary_redacts_inline_literals():
    summary = _safe_sql_summary(
        "SELECT * FROM members WHERE email = 'private@example.com' AND score >= 98.5"
    )

    assert 'private@example.com' not in summary
    assert '98.5' not in summary
    assert "email = '?'" in summary


@pytest.mark.api
@pytest.mark.django_db
class TestPerformanceMetrics:
    """性能指标测试"""

    def test_metrics_requires_auth(self, api_client):
        """性能指标需认证"""
        resp = api_client.get('/api/v1/common/performance/metrics/')
        assert resp.status_code in (401, 403)

    def test_metrics_member_forbidden(self, member_client):
        """普通成员不可访问性能指标"""
        resp = member_client.get('/api/v1/common/performance/metrics/')
        assert resp.status_code == 403

    def test_metrics_teacher_forbidden(self, teacher_client):
        """工程指标仅系统管理员可访问。"""
        resp = teacher_client.get('/api/v1/common/performance/metrics/')
        assert resp.status_code == 403

    def test_metrics_admin_ok(self, admin_client):
        resp = admin_client.get('/api/v1/common/performance/metrics/')
        assert resp.status_code == 200, resp.json()

    def test_metrics_returns_required_fields(self, admin_client):
        """返回必需字段"""
        data = extract_data(admin_client.get('/api/v1/common/performance/metrics/'))
        for key in (
            'request_count', 'window_capacity', 'requests_per_minute',
            'query_count', 'avg_response_time_ms', 'p95_response_time_ms',
            'status_codes', 'collected_at', 'slow_query_threshold_seconds',
            'cache_hit_rate', 'cache_metrics_available',
        ):
            assert key in data, f'缺失字段 {key}'
        assert isinstance(data['status_codes'], dict)
        assert data['window_capacity'] >= data['request_count']

    def test_metrics_query_count_is_int(self, admin_client):
        """query_count 为整数"""
        data = extract_data(admin_client.get('/api/v1/common/performance/metrics/'))
        assert isinstance(data['query_count'], int)
        assert data['query_count'] >= 0

    def test_metrics_do_not_invent_cache_hit_rate(self, admin_client):
        """未接入缓存采样时明确返回 unavailable，而不是固定模拟值。"""
        data = extract_data(admin_client.get('/api/v1/common/performance/metrics/'))
        assert data['cache_hit_rate'] is None
        assert data['cache_metrics_available'] is False

    def test_metrics_are_collected_from_real_requests(self, admin_client):
        admin_client.get('/api/v1/dashboard/')
        data = extract_data(admin_client.get('/api/v1/common/performance/metrics/'))
        assert data['request_count'] >= 1
        assert data['avg_response_time_ms'] >= 0
        assert data['p95_response_time_ms'] >= 0

    def test_metrics_returns_debug_mode(self, admin_client):
        """返回 debug_mode 字段"""
        data = extract_data(admin_client.get('/api/v1/common/performance/metrics/'))
        assert 'debug_mode' in data


@pytest.mark.api
@pytest.mark.django_db
class TestSlowQueryLog:
    """慢查询日志测试"""

    def test_slow_queries_requires_auth(self, api_client):
        """慢查询需认证"""
        resp = api_client.get('/api/v1/common/performance/slow-queries/')
        assert resp.status_code in (401, 403)

    def test_slow_queries_teacher_forbidden(self, teacher_client):
        """老师不能访问工程慢查询。"""
        resp = teacher_client.get('/api/v1/common/performance/slow-queries/')
        assert resp.status_code == 403

    def test_slow_queries_returns_fields(self, admin_client):
        """返回必需字段"""
        data = extract_data(admin_client.get('/api/v1/common/performance/slow-queries/'))
        assert 'slow_queries' in data
        assert 'total' in data
        assert 'threshold_seconds' in data
        assert data['source'] == 'request_middleware'
        assert isinstance(data['slow_queries'], list)

    def test_slow_queries_admin_ok(self, admin_client):
        """管理员可访问慢查询"""
        resp = admin_client.get('/api/v1/common/performance/slow-queries/')
        assert resp.status_code == 200
