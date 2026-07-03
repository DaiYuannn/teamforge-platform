"""audit 应用的 apps 配置"""
from django.apps import AppConfig


class AuditConfig(AppConfig):
    """audit 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = '操作审计'
