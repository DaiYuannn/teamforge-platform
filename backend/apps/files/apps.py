"""files 应用的 apps 配置"""
from django.apps import AppConfig


class FilesConfig(AppConfig):
    """files 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.files'
    verbose_name = '文件管理'
