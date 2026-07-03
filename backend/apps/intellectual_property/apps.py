"""intellectual_property 应用的 apps 配置"""
from django.apps import AppConfig


class IntellectualPropertyConfig(AppConfig):
    """intellectual_property 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.intellectual_property'
    verbose_name = '知识产权管理'
