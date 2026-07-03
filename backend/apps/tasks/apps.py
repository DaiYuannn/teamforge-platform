"""tasks 应用的 apps 配置"""
from django.apps import AppConfig


class TasksConfig(AppConfig):
    """tasks 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tasks'
    verbose_name = '任务管理'
