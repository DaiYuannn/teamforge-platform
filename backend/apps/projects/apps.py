"""projects 应用的 apps 配置"""
from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """projects 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.projects'
    verbose_name = '项目管理'
