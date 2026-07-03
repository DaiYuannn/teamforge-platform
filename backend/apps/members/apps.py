"""members 应用的 apps 配置"""
from django.apps import AppConfig


class MembersConfig(AppConfig):
    """members 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.members'
    verbose_name = '成员管理'
