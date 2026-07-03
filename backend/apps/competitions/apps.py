"""competitions 应用的 apps 配置"""
from django.apps import AppConfig


class CompetitionsConfig(AppConfig):
    """competitions 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.competitions'
    verbose_name = '比赛管理'
