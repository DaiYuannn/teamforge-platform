"""imports 应用的 apps 配置"""
from django.apps import AppConfig


class ImportsConfig(AppConfig):
    """imports 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.imports'
    verbose_name = '数据导入'
