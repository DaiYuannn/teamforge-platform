"""Celery 实例配置，包含通知检查与定时报表 Beat 任务。"""
import os

from celery import Celery

# 设置 Django 配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('team_management')

# 从 Django settings 中读取 Celery 配置（以 CELERY_ 开头的配置项）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各 app 中的 tasks.py
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """调试任务，打印请求信息"""
    print(f'Request: {self.request!r}')
