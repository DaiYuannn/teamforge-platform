"""
P12: 用户偏好设置测试
- GET /api/v1/users/preference/ 获取偏好（不存在则返回默认值，不自动创建）
- PUT /api/v1/users/preference/ 更新偏好（不存在则自动创建）
- 偏好为账户级配置，与用户一对一
"""
import pytest

from apps.users.models import UserPreference


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


DEFAULT_EXPECTED = {
    'dashboard_layout': {},
    'theme_color': 'blue',
    'default_landing': 'dashboard',
    'sidebar_collapsed': False,
    'notification_sound': True,
    'items_per_page': 20,
}


@pytest.mark.api
@pytest.mark.django_db
class TestUserPreference:
    """用户偏好设置接口测试"""

    def test_get_default_preference(self, member_client):
        """无偏好记录时返回默认值且不自动创建"""
        resp = member_client.get('/api/v1/users/preference/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['theme_color'] == 'blue'
        assert data['default_landing'] == 'dashboard'
        assert data['sidebar_collapsed'] is False
        assert data['notification_sound'] is True
        assert data['items_per_page'] == 20
        assert data['dashboard_layout'] == {}
        # 不应自动创建记录
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    def test_update_creates_preference(self, member_client):
        """首次更新自动创建偏好记录"""
        resp = member_client.put('/api/v1/users/preference/', {
            'theme_color': 'green',
            'items_per_page': 50,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['theme_color'] == 'green'
        assert data['items_per_page'] == 50
        # 记录已创建
        assert UserPreference.objects.filter(user=member_client.user).exists()
        pref = UserPreference.objects.get(user=member_client.user)
        assert pref.theme_color == 'green'
        assert pref.items_per_page == 50

    def test_update_existing_preference(self, member_client):
        """更新已存在的偏好记录"""
        # 先创建
        member_client.put('/api/v1/users/preference/', {'theme_color': 'green'}, format='json')
        # 再更新
        resp = member_client.put('/api/v1/users/preference/', {
            'theme_color': 'purple',
            'sidebar_collapsed': True,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        pref = UserPreference.objects.get(user=member_client.user)
        assert pref.theme_color == 'purple'
        assert pref.sidebar_collapsed is True
        # 仍只有一条记录
        assert UserPreference.objects.filter(user=member_client.user).count() == 1

    def test_update_dashboard_layout(self, member_client):
        """更新仪表盘布局（JSON 对象）"""
        layout = {'cards': ['a', 'b'], 'order': 1}
        resp = member_client.put('/api/v1/users/preference/', {
            'dashboard_layout': layout,
        }, format='json')
        assert resp.status_code == 200, resp.json()
        data = extract_data(resp)
        assert data['dashboard_layout'] == layout
        pref = UserPreference.objects.get(user=member_client.user)
        assert pref.dashboard_layout == layout

    def test_invalid_theme_color_rejected(self, member_client):
        """非法主题色被拒绝"""
        resp = member_client.put('/api/v1/users/preference/', {
            'theme_color': 'pink',
        }, format='json')
        assert resp.status_code in (400, 422)

    def test_invalid_landing_rejected(self, member_client):
        """非法默认着陆页被拒绝"""
        resp = member_client.put('/api/v1/users/preference/', {
            'default_landing': 'unknown',
        }, format='json')
        assert resp.status_code in (400, 422)

    def test_invalid_items_per_page_rejected(self, member_client):
        """非法每页条数被拒绝"""
        resp = member_client.put('/api/v1/users/preference/', {
            'items_per_page': 999,
        }, format='json')
        assert resp.status_code in (400, 422)

    def test_invalid_dashboard_layout_rejected(self, member_client):
        """dashboard_layout 必须为对象类型"""
        resp = member_client.put('/api/v1/users/preference/', {
            'dashboard_layout': 'not-an-object',
        }, format='json')
        assert resp.status_code in (400, 422)

    def test_preference_isolated_per_user(self, member_client, make_user, api_client):
        """不同用户偏好相互隔离"""
        # 用户 A 设置偏好
        member_client.put('/api/v1/users/preference/', {'theme_color': 'green'}, format='json')

        # 用户 B 获取默认值
        user_b = make_user(email='userb@test.com', global_role='member')
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user_b)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        resp = api_client.get('/api/v1/users/preference/')
        assert resp.status_code == 200
        data = extract_data(resp)
        # 用户 B 仍是默认蓝色
        assert data['theme_color'] == 'blue'

    def test_persistence_across_requests(self, member_client):
        """偏好设置持久化，再次 GET 能取回"""
        member_client.put('/api/v1/users/preference/', {
            'theme_color': 'orange',
            'notification_sound': False,
            'items_per_page': 10,
        }, format='json')

        resp = member_client.get('/api/v1/users/preference/')
        assert resp.status_code == 200
        data = extract_data(resp)
        assert data['theme_color'] == 'orange'
        assert data['notification_sound'] is False
        assert data['items_per_page'] == 10

    def test_unauthenticated_cannot_access(self, api_client):
        """未认证用户无法访问偏好设置"""
        resp = api_client.get('/api/v1/users/preference/')
        assert resp.status_code in (401, 403)

    def test_partial_update_keeps_other_fields(self, member_client):
        """部分更新不影响其他字段"""
        member_client.put('/api/v1/users/preference/', {
            'theme_color': 'green',
            'notification_sound': False,
        }, format='json')
        # 仅更新主题色
        member_client.put('/api/v1/users/preference/', {
            'theme_color': 'purple',
        }, format='json')
        pref = UserPreference.objects.get(user=member_client.user)
        assert pref.theme_color == 'purple'
        # notification_sound 保持不变
        assert pref.notification_sound is False

    @pytest.mark.parametrize('payload', [
        {'sidebar_collapsed': 1},
        {'notification_sound': 'false'},
        {'theme_color': []},
        {'primary_color': 176_107_115},
        {'items_per_page': []},
        {'items_per_page': True},
        {'dashboard_layout': []},
        {'sidebar_order': ['workspace', 'workspace']},
        {'favorite_routes': ['/tasks', 3]},
        {'saved_filters': {'tasks': ['todo']}},
        {'notification_preferences': {'categories': {'task': 1}}},
        {'notification_preferences': {'channels': {'email': 'yes'}}},
        {'notification_preferences': {
            'quiet_hours': {'enabled': True, 'start': '25:00', 'end': '07:30'},
        }},
        {'notification_preferences': {'digest': 'hourly'}},
        {'notification_preferences': {'unknown': True}},
    ])
    def test_rejects_invalid_structured_preferences(self, member_client, payload):
        response = member_client.patch(
            '/api/v1/users/preference/', payload, format='json'
        )

        assert response.status_code == 400, response.json()
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    @pytest.mark.parametrize('payload', [
        [],
        {},
        {'unexpected_field': 'value'},
    ])
    def test_rejects_empty_or_unknown_updates(self, member_client, payload):
        response = member_client.patch(
            '/api/v1/users/preference/', payload, format='json'
        )

        assert response.status_code == 400, response.json()
        assert not UserPreference.objects.filter(user=member_client.user).exists()

    def test_accepts_complete_notification_preference_schema(self, member_client):
        payload = {
            'sidebar_order': ['workspace', 'execution'],
            'favorite_routes': ['/projects', '/tasks'],
            'saved_filters': {'tasks': {'status': ['todo']}},
            'notification_preferences': {
                'categories': {'task': True, 'finance': False},
                'channels': {'in_app': True, 'email': False},
                'quiet_hours': {
                    'enabled': True,
                    'start': '22:00',
                    'end': '07:30',
                },
                'digest': 'daily',
            },
        }

        response = member_client.patch(
            '/api/v1/users/preference/', payload, format='json'
        )

        assert response.status_code == 200, response.json()
        preference = UserPreference.objects.get(user=member_client.user)
        assert preference.notification_preferences == payload['notification_preferences']
