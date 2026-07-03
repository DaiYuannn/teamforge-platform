"""integrations 应用的 apps 配置"""
from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    """integrations 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.integrations'
    verbose_name = '第三方集成'
