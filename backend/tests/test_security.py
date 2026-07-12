"""
P20 发布包安全测试
- SECRET_KEY 通过环境变量配置（base.py）
- DEBUG 仅在 dev 为 True
- prod.py 存在且 DEBUG=False
- 安全设置（X_FRAME_OPTIONS / SECURE_CONTENT_TYPE_NOSNIFF / SECURE_BROWSER_XSS_FILTER）已定义
- 响应中包含安全响应头（X-Frame-Options / X-Content-Type-Options）
"""
import os

import pytest
from django.conf import settings


def read_settings_file(name):
    """读取 config/settings/ 下的设置文件内容"""
    path = settings.BASE_DIR / 'config' / 'settings' / name
    return path.read_text(encoding='utf-8')


@pytest.mark.api
@pytest.mark.django_db
class TestSecretKeyHandling:
    """SECRET_KEY 处理测试"""

    def test_secret_key_uses_env_var(self):
        """base.py 中 SECRET_KEY 通过环境变量 DJANGO_SECRET_KEY 读取"""
        content = read_settings_file('base.py')
        assert 'DJANGO_SECRET_KEY' in content, 'base.py 未通过环境变量配置 SECRET_KEY'
        assert 'os.environ' in content

    def test_secret_key_is_set(self):
        """SECRET_KEY 已加载为非空字符串"""
        assert isinstance(settings.SECRET_KEY, str)
        assert settings.SECRET_KEY, 'SECRET_KEY 不能为空'

    def test_prod_secret_key_requires_env(self):
        """prod.py 强制要求 DJANGO_SECRET_KEY 环境变量"""
        content = read_settings_file('prod.py')
        assert 'DJANGO_SECRET_KEY' in content
        assert 'ImproperlyConfigured' in content


@pytest.mark.api
@pytest.mark.django_db
class TestDebugSetting:
    """DEBUG 设置测试"""

    def test_dev_debug_true(self):
        """dev.py 中 DEBUG=True"""
        content = read_settings_file('dev.py')
        assert 'DEBUG = True' in content

    def test_prod_debug_false(self):
        """prod.py 中 DEBUG=False"""
        content = read_settings_file('prod.py')
        assert 'DEBUG = False' in content

    def test_prod_file_exists(self):
        """prod.py 配置文件存在"""
        path = settings.BASE_DIR / 'config' / 'settings' / 'prod.py'
        assert path.exists()

    def test_test_debug_false(self):
        """测试环境 DEBUG=False"""
        assert settings.DEBUG is False


@pytest.mark.api
@pytest.mark.django_db
class TestSecuritySettings:
    """安全设置定义测试"""

    def test_x_frame_options_defined(self):
        """X_FRAME_OPTIONS 已定义"""
        assert hasattr(settings, 'X_FRAME_OPTIONS')
        assert settings.X_FRAME_OPTIONS in ('DENY', 'SAMEORIGIN')

    def test_secure_content_type_nosniff(self):
        """SECURE_CONTENT_TYPE_NOSNIFF 已启用"""
        assert getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False) is True

    def test_secure_browser_xss_filter(self):
        """SECURE_BROWSER_XSS_FILTER 已定义"""
        assert hasattr(settings, 'SECURE_BROWSER_XSS_FILTER')
        assert settings.SECURE_BROWSER_XSS_FILTER is True

    def test_security_middleware_present(self):
        """SecurityMiddleware 已启用"""
        assert 'django.middleware.security.SecurityMiddleware' in settings.MIDDLEWARE

    def test_xframe_options_middleware_present(self):
        """XFrameOptionsMiddleware 已启用"""
        assert 'django.middleware.clickjacking.XFrameOptionsMiddleware' in settings.MIDDLEWARE

    def test_prod_has_security_headers(self):
        """prod.py 中包含安全响应头设置"""
        content = read_settings_file('prod.py')
        assert 'X_FRAME_OPTIONS' in content
        assert 'SECURE_CONTENT_TYPE_NOSNIFF' in content


@pytest.mark.api
@pytest.mark.django_db
class TestSecurityHeaders:
    """安全响应头测试"""

    def test_x_frame_options_header(self, api_client):
        """响应包含 X-Frame-Options 头"""
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        assert 'X-Frame-Options' in resp.headers, '响应缺少 X-Frame-Options 头'
        assert resp.headers['X-Frame-Options'].upper() in ('DENY', 'SAMEORIGIN')

    def test_x_content_type_options_header(self, api_client):
        """响应包含 X-Content-Type-Options: nosniff 头"""
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        assert 'X-Content-Type-Options' in resp.headers, '响应缺少 X-Content-Type-Options 头'
        assert resp.headers['X-Content-Type-Options'].lower() == 'nosniff'

    def test_x_frame_options_value_is_deny(self, api_client):
        """X-Frame-Options 值为 DENY"""
        resp = api_client.get('/api/v1/dashboard/public-portal/')
        # 测试环境继承 base，X_FRAME_OPTIONS = 'DENY'
        assert resp.headers.get('X-Frame-Options', '').upper() == settings.X_FRAME_OPTIONS.upper()
