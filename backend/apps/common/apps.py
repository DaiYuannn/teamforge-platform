"""common 应用的 apps 配置"""
from django.apps import AppConfig


class CommonConfig(AppConfig):
    """common 应用配置（动态流等横切能力）"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    verbose_name = '通用'
