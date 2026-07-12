"""
N58: 健康检查测试
- GET /api/v1/common/health/   无需认证
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestHealthCheck:
    """健康检查测试"""

    def test_health_no_auth_required(self, api_client):
        """健康检查无需认证"""
        resp = api_client.get('/api/v1/common/health/')
        assert resp.status_code == 200, resp.json()

    def test_returns_overall_status(self, api_client):
        """返回总体状态字段"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert 'status' in data
        assert data['status'] in ('healthy', 'degraded', 'unhealthy')

    def test_returns_checks_dict(self, api_client):
        """返回各项检查字典"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert 'checks' in data
        assert isinstance(data['checks'], dict)

    def test_includes_database_check(self, api_client):
        """包含数据库检查"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert 'database' in data['checks']
        db = data['checks']['database']
        assert 'status' in db
        assert 'message' in db

    def test_database_is_healthy(self, api_client):
        """数据库连接正常"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert data['checks']['database']['status'] == 'healthy'

    def test_includes_cache_check(self, api_client):
        """包含缓存检查"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert 'cache' in data['checks']
        assert data['checks']['cache']['status'] in ('healthy', 'degraded', 'unhealthy')

    def test_includes_celery_check(self, api_client):
        """包含 Celery 检查"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert 'celery' in data['checks']

    def test_includes_storage_check(self, api_client):
        """包含存储检查"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert 'storage' in data['checks']

    def test_includes_migrations_check(self, api_client):
        """包含迁移状态检查"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert 'migrations' in data['checks']

    def test_migrations_all_applied(self, api_client):
        """测试库所有迁移已应用"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert data['checks']['migrations']['status'] == 'healthy'

    def test_returns_timestamp(self, api_client):
        """返回时间戳"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        assert 'timestamp' in data
        assert data['timestamp']

    def test_overall_status_aggregation(self, api_client):
        """总体状态等于最严重的单项状态"""
        data = extract_data(api_client.get('/api/v1/common/health/'))
        statuses = [c['status'] for c in data['checks'].values()]
        rank = {'healthy': 0, 'degraded': 1, 'unhealthy': 2}
        worst = max(statuses, key=lambda s: rank.get(s, 0))
        assert data['status'] == worst
