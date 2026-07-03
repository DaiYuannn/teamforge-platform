"""notifications 应用的 apps 配置"""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """notifications 应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = '通知公告'
