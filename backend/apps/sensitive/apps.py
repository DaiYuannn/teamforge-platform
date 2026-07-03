"""sensitive 应用的 apps 配置"""
from django.apps import AppConfig


class SensitiveConfig(AppConfig):
    """sensitive 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sensitive'
    verbose_name = '敏感资料'
