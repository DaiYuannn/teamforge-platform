"""dashboard 应用的 apps 配置"""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """dashboard 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = '驾驶舱看板'
