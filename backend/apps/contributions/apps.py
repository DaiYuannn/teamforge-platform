"""contributions 应用的 apps 配置"""
from django.apps import AppConfig


class ContributionsConfig(AppConfig):
    """contributions 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.contributions'
    verbose_name = '贡献度管理'
