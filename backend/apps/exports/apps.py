"""exports 应用的 apps 配置"""
from django.apps import AppConfig


class ExportsConfig(AppConfig):
    """exports 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.exports'
    verbose_name = '数据导出'
