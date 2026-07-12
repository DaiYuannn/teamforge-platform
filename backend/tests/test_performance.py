"""
N59: 性能监控测试
- GET /api/v1/common/performance/metrics/
- GET /api/v1/common/performance/slow-queries/
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


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

    def test_metrics_teacher_ok(self, teacher_client):
        """老师可访问性能指标"""
        resp = teacher_client.get('/api/v1/common/performance/metrics/')
        assert resp.status_code == 200, resp.json()

    def test_metrics_returns_required_fields(self, teacher_client):
        """返回必需字段"""
        data = extract_data(teacher_client.get('/api/v1/common/performance/metrics/'))
        for key in ('query_count', 'avg_response_time_ms', 'cache_hit_rate'):
            assert key in data, f'缺失字段 {key}'

    def test_metrics_query_count_is_int(self, teacher_client):
        """query_count 为整数"""
        data = extract_data(teacher_client.get('/api/v1/common/performance/metrics/'))
        assert isinstance(data['query_count'], int)
        assert data['query_count'] >= 0

    def test_metrics_cache_hit_rate_in_range(self, teacher_client):
        """cache_hit_rate 在 0~1 之间"""
        data = extract_data(teacher_client.get('/api/v1/common/performance/metrics/'))
        assert 0 <= data['cache_hit_rate'] <= 1

    def test_metrics_returns_debug_mode(self, teacher_client):
        """返回 debug_mode 字段"""
        data = extract_data(teacher_client.get('/api/v1/common/performance/metrics/'))
        assert 'debug_mode' in data


@pytest.mark.api
@pytest.mark.django_db
class TestSlowQueryLog:
    """慢查询日志测试"""

    def test_slow_queries_requires_auth(self, api_client):
        """慢查询需认证"""
        resp = api_client.get('/api/v1/common/performance/slow-queries/')
        assert resp.status_code in (401, 403)

    def test_slow_queries_teacher_ok(self, teacher_client):
        """老师可访问慢查询"""
        resp = teacher_client.get('/api/v1/common/performance/slow-queries/')
        assert resp.status_code == 200, resp.json()

    def test_slow_queries_returns_fields(self, teacher_client):
        """返回必需字段"""
        data = extract_data(teacher_client.get('/api/v1/common/performance/slow-queries/'))
        assert 'slow_queries' in data
        assert 'total' in data
        assert 'threshold_seconds' in data
        assert isinstance(data['slow_queries'], list)

    def test_slow_queries_admin_ok(self, admin_client):
        """管理员可访问慢查询"""
        resp = admin_client.get('/api/v1/common/performance/slow-queries/')
        assert resp.status_code == 200
