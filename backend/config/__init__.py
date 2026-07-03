# Django 项目配置包

# 导入 Celery 应用（架构预留）
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    pass
