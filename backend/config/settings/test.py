"""
测试环境配置
- 使用独立测试数据库
- Celery 同步执行
- 内存邮件后端
- 禁用 debug toolbar
"""
import os

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ['*']

# 独立测试数据库
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('TEST_DB_NAME', 'team_management_test'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# 加密密钥（测试固定值）
os.environ.setdefault(
    'FIELD_ENCRYPTION_KEY',
    'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=',
)

# Celery 同步执行
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# 内存邮件后端
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# 密码哈希使用最快算法（加速测试）
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 禁用 debug toolbar
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]  # noqa: F405

# 测试环境媒体文件
MEDIA_ROOT = str(BASE_DIR / 'test_media')
