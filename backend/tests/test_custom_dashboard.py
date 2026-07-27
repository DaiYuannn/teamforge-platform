"""
N48 自定义看板测试
- CRUD、set_default、用户隔离、默认看板唯一
"""
import pytest

from apps.dashboard.custom_dashboard_models import CustomDashboard

CUSTOM_DASHBOARD_URL = '/api/v1/dashboard/custom/'


def extract_data(resp):
    body = resp.json()
    if isinstance(body, dict) and 'code' in body:
        return body.get('data', body)
    return body


@pytest.mark.api
@pytest.mark.django_db
class TestCustomDashboard:
    """自定义看板 API 测试"""

    # ---------- 认证 ----------

    def test_requires_auth(self, api_client):
        """未认证不可访问"""
        resp = api_client.get(CUSTOM_DASHBOARD_URL)
        assert resp.status_code == 401

    # ---------- 创建 ----------

    def test_create_dashboard(self, member_client):
        """创建看板"""
        resp = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '我的看板',
            'config': {'widgets': ['projects', 'tasks']},
            'is_default': False,
        }, format='json')
        assert resp.status_code in (200, 201), resp.json()
        data = extract_data(resp)
        assert data['name'] == '我的看板'
        assert data['config'] == {'widgets': ['projects', 'tasks']}
        assert data['user'] == member_client.user.id

    def test_create_dashboard_with_positions(self, member_client):
        """创建带布局的看板"""
        config = {
            'widgets': [
                {'type': 'chart', 'position': {'x': 0, 'y': 0, 'w': 6, 'h': 4}},
                {'type': 'table', 'position': {'x': 6, 'y': 0, 'w': 6, 'h': 4}},
            ],
            'filters': {'project_id': 1, 'date_range': '7d'},
        }
        resp = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '布局看板',
            'config': config,
        }, format='json')
        assert resp.status_code in (200, 201)
        data = extract_data(resp)
        assert len(data['config']['widgets']) == 2

    # ---------- 列表 / 用户隔离 ----------

    def test_list_only_own_dashboards(self, member_client, make_user, api_client):
        """用户只能看到自己的看板"""
        from rest_framework_simplejwt.tokens import RefreshToken
        # 用户 A 创建看板
        resp = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': 'A的看板', 'config': {},
        }, format='json')
        assert resp.status_code in (200, 201)

        # 用户 B 登录
        user_b = make_user(email='b@test.com', global_role='member')
        refresh = RefreshToken.for_user(user_b)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        resp_b = api_client.get(CUSTOM_DASHBOARD_URL)
        assert resp_b.status_code == 200
        data_b = extract_data(resp_b)
        results = data_b.get('results', data_b) if isinstance(data_b, dict) else data_b
        # B 看不到 A 的看板
        names = [r['name'] for r in results]
        assert 'A的看板' not in names

    # ---------- 详情 / 更新 / 删除 ----------

    def test_retrieve_dashboard(self, member_client):
        """查看详情"""
        resp = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '详情看板', 'config': {'k': 'v'},
        }, format='json')
        dash_id = extract_data(resp)['id']
        resp = member_client.get(f'{CUSTOM_DASHBOARD_URL}{dash_id}/')
        assert resp.status_code == 200
        assert extract_data(resp)['id'] == dash_id

    def test_update_dashboard(self, member_client):
        """更新看板"""
        resp = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '原名', 'config': {},
        }, format='json')
        dash_id = extract_data(resp)['id']
        resp = member_client.patch(f'{CUSTOM_DASHBOARD_URL}{dash_id}/', {
            'name': '新名',
            'config': {'updated': True},
        }, format='json')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['name'] == '新名'
        assert data['config'] == {'updated': True}

    def test_delete_dashboard(self, member_client):
        """删除看板"""
        resp = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '待删除', 'config': {},
        }, format='json')
        dash_id = extract_data(resp)['id']
        resp = member_client.delete(f'{CUSTOM_DASHBOARD_URL}{dash_id}/')
        assert resp.status_code in (200, 204)
        assert not CustomDashboard.objects.filter(id=dash_id).exists()

    # ---------- set_default ----------

    def test_set_default(self, member_client):
        """设为默认看板"""
        resp1 = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '看板1', 'config': {}, 'is_default': True,
        }, format='json')
        dash1_id = extract_data(resp1)['id']
        resp2 = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '看板2', 'config': {},
        }, format='json')
        dash2_id = extract_data(resp2)['id']

        # 将看板2设为默认
        resp = member_client.post(f'{CUSTOM_DASHBOARD_URL}{dash2_id}/set_default/')
        assert resp.status_code == 200
        # 看板1 不再是默认
        assert not CustomDashboard.objects.get(id=dash1_id).is_default
        assert CustomDashboard.objects.get(id=dash2_id).is_default

    def test_only_one_default(self, member_client):
        """同一用户仅一个默认看板"""
        member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '默认A', 'config': {}, 'is_default': True,
        }, format='json')
        member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '默认B', 'config': {}, 'is_default': True,
        }, format='json')
        defaults = CustomDashboard.objects.filter(
            user=member_client.user, is_default=True
        )
        assert defaults.count() == 1

    def test_get_default(self, member_client):
        """获取默认看板"""
        member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '默认看板', 'config': {}, 'is_default': True,
        }, format='json')
        resp = member_client.get(f'{CUSTOM_DASHBOARD_URL}default/')
        assert resp.status_code == 200
        assert extract_data(resp)['is_default'] is True

    def test_get_default_not_found(self, member_client):
        """无默认看板时返回错误"""
        member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '非默认', 'config': {},
        }, format='json')
        resp = member_client.get(f'{CUSTOM_DASHBOARD_URL}default/')
        assert resp.status_code in (400, 404)

    def test_dashboard_data_uses_widgets_and_project_scope(
        self, member_client, make_project, make_task, make_finance
    ):
        selected = make_project(name='Selected project')
        other = make_project(name='Other project')
        selected_task = make_task(project=selected, title='Selected task')
        make_task(project=other, title='Other task')
        make_finance(project=selected, amount=125)
        make_finance(project=other, amount=900)
        response = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': 'Runtime dashboard',
            'config': {
                'widgets': ['signals', 'priority', 'delivery', 'business'],
                'project_id': selected.id,
                'date_range': 'month',
            },
        }, format='json')
        dashboard_id = extract_data(response)['id']

        runtime = member_client.get(
            f'{CUSTOM_DASHBOARD_URL}{dashboard_id}/data/'
        )

        assert runtime.status_code == 200, runtime.json()
        data = extract_data(runtime)
        assert set(data['widgets']) == {'signals', 'priority', 'delivery', 'business'}
        assert data['widgets']['signals']['metrics'][0]['value'] == 1
        assert data['widgets']['priority']['items'][0]['id'] == selected_task.id
        assert data['widgets']['delivery']['items'][0]['id'] == selected.id
        assert data['widgets']['business']['metrics'][0]['value'] == 125.0


@pytest.mark.model
@pytest.mark.django_db
class TestCustomDashboardModel:
    """自定义看板模型测试"""

    def test_str(self, make_user):
        user = make_user(name='张三')
        dash = CustomDashboard.objects.create(user=user, name='看板X', config={})
        assert '张三' in str(dash)
        assert '看板X' in str(dash)

    def test_unique_together(self, member_client):
        """同一用户同名看板唯一"""
        member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '重复名', 'config': {},
        }, format='json')
        resp = member_client.post(CUSTOM_DASHBOARD_URL, {
            'name': '重复名', 'config': {},
        }, format='json')
        assert resp.status_code in (400, 500)

    def test_default_config(self, make_user):
        """默认 config 为空 dict"""
        user = make_user()
        dash = CustomDashboard.objects.create(user=user, name='空配置')
        assert dash.config == {}
        assert dash.is_default is False
