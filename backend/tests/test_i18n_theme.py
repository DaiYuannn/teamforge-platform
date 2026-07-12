"""
N62: 国际化（i18n）与暗色模式测试
- GET /api/v1/common/i18n/translations/
- GET /api/v1/common/i18n/themes/
"""
import pytest


def extract_data(response):
    data = response.json()
    if isinstance(data, dict) and 'code' in data:
        return data.get('data', data)
    return data


@pytest.mark.api
@pytest.mark.django_db
class TestTranslations:
    """翻译语言测试"""

    def test_translations_no_auth_required(self, api_client):
        """翻译接口无需认证"""
        resp = api_client.get('/api/v1/common/i18n/translations/')
        assert resp.status_code == 200, resp.json()

    def test_translations_returns_list(self, api_client):
        """返回翻译语言列表"""
        data = extract_data(api_client.get('/api/v1/common/i18n/translations/'))
        assert 'translations' in data
        assert isinstance(data['translations'], list)
        assert len(data['translations']) >= 2

    def test_translations_includes_zh_and_en(self, api_client):
        """包含 zh-CN 和 en"""
        data = extract_data(api_client.get('/api/v1/common/i18n/translations/'))
        codes = [t['code'] for t in data['translations']]
        assert 'zh-CN' in codes
        assert 'en' in codes

    def test_translations_default_is_zh(self, api_client):
        """默认语言为 zh-CN"""
        data = extract_data(api_client.get('/api/v1/common/i18n/translations/'))
        assert data['default'] == 'zh-hans' or data['default'].startswith('zh')

    def test_translations_returns_locale_middleware_flag(self, api_client):
        """返回 locale 中间件启用状态"""
        data = extract_data(api_client.get('/api/v1/common/i18n/translations/'))
        assert 'locale_middleware_enabled' in data
        assert isinstance(data['locale_middleware_enabled'], bool)


@pytest.mark.api
@pytest.mark.django_db
class TestThemes:
    """主题（暗色模式）测试"""

    def test_themes_no_auth_required(self, api_client):
        """主题接口无需认证"""
        resp = api_client.get('/api/v1/common/i18n/themes/')
        assert resp.status_code == 200, resp.json()

    def test_themes_returns_list(self, api_client):
        """返回主题列表"""
        data = extract_data(api_client.get('/api/v1/common/i18n/themes/'))
        assert 'themes' in data
        assert isinstance(data['themes'], list)

    def test_themes_includes_light_dark_auto(self, api_client):
        """包含 light / dark / auto"""
        data = extract_data(api_client.get('/api/v1/common/i18n/themes/'))
        codes = [t['code'] for t in data['themes']]
        assert 'light' in codes
        assert 'dark' in codes
        assert 'auto' in codes

    def test_themes_supports_dark_mode(self, api_client):
        """支持暗色模式"""
        data = extract_data(api_client.get('/api/v1/common/i18n/themes/'))
        assert data['supports_dark_mode'] is True
