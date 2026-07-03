"""finance 应用的 apps 配置"""
from django.apps import AppConfig


class FinanceConfig(AppConfig):
    """finance 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.finance'
    verbose_name = '经费管理'
