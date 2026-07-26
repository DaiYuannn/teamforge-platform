import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-secret-key-change-in-production',
)
DEBUG = False
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_celery_beat',
    'django_celery_results',
    'apps.users',
    'apps.projects',
    'apps.competitions',
    'apps.tasks',
    'apps.members',
    'apps.finance',
    'apps.files',
    'apps.imports',
    'apps.dashboard',
    'apps.contributions',
    'apps.sensitive',
    'apps.notifications',
    'apps.audit',
    'apps.exports',
    'apps.intellectual_property',
    'apps.integrations',
    'apps.common',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.OperationLogMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'team_management'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# ============ 安全设置（P20）============
# X-Frame-Options：防止点击劫持（由 XFrameOptionsMiddleware 写入响应头）
X_FRAME_OPTIONS = 'DENY'
# X-Content-Type-Options：防止 MIME 类型嗅探（由 SecurityMiddleware 写入响应头）
SECURE_CONTENT_TYPE_NOSNIFF = True
# X-XSS-Protection：启用浏览器 XSS 过滤（旧版浏览器保护，新版浏览器已内置）
SECURE_BROWSER_XSS_FILTER = True
# 跨域凭据
CORS_ALLOW_CREDENTIALS = True

STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('STATIC_ROOT', str(BASE_DIR / 'staticfiles'))

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', str(BASE_DIR / 'media'))
DEMO_BACKUP_ROOT = os.environ.get('DEMO_BACKUP_ROOT', str(BASE_DIR / 'demo_backups'))

# 非 public/ 媒体不再暴露永久可猜测 URL。业务序列化器只向已获授权的
# 调用方签发限时 URL，下载请求再由后端验签。
STORAGES = {
    'default': {
        'BACKEND': 'common.storage.ProtectedMediaStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
PROTECTED_MEDIA_API_URL = '/api/v1/common/media/'
PROTECTED_MEDIA_URL_TTL = int(os.environ.get('PROTECTED_MEDIA_URL_TTL', '7200'))
PROTECTED_MEDIA_INTERNAL_PREFIX = '/_protected_media/'
PROTECTED_MEDIA_USE_X_ACCEL_REDIRECT = (
    os.environ.get('PROTECTED_MEDIA_USE_X_ACCEL_REDIRECT', 'False').lower() == 'true'
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'common.authentication.ScopedJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
NOTIFICATION_STREAM_REDIS_URL = os.environ.get(
    'NOTIFICATION_STREAM_REDIS_URL',
    CELERY_BROKER_URL,
)
NOTIFICATION_STREAM_ENABLED = (
    os.environ.get('NOTIFICATION_STREAM_ENABLED', 'true').lower() == 'true'
)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'check-task-overdue': {
        'task': 'apps.notifications.tasks.check_task_overdue',
        'schedule': crontab(minute=0, hour='*/3'),
    },
    'check-leader-update': {
        'task': 'apps.notifications.tasks.check_leader_update',
        'schedule': crontab(minute=30, hour=9),
    },
    'check-competition-deadlines': {
        'task': 'apps.notifications.tasks.check_competition_deadlines',
        'schedule': crontab(minute=0, hour=9),
    },
    'remind-flexible-schedule': {
        'task': 'apps.notifications.tasks.remind_flexible_schedule',
        'schedule': crontab(minute=0, hour=10, day_of_month='1,16'),
    },
    'check-ip-returns': {
        'task': 'apps.notifications.tasks.check_ip_returns',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'check-ip-objections': {
        'task': 'apps.notifications.tasks.check_ip_objections',
        'schedule': crontab(minute=15, hour='*/6'),
    },
    'check-pending-contributions': {
        'task': 'apps.notifications.tasks.check_pending_contributions',
        'schedule': crontab(minute=30, hour='*/6'),
    },
    'check-sensitive-requests': {
        'task': 'apps.notifications.tasks.check_sensitive_requests',
        'schedule': crontab(minute=45, hour='*/6'),
    },
    'run-due-scheduled-reports': {
        'task': 'apps.exports.tasks.run_due_scheduled_reports',
        'schedule': crontab(minute='*'),
    },
    'send-daily-notification-digest': {
        'task': 'apps.notifications.tasks.send_daily_notification_digest',
        'schedule': crontab(minute=0, hour=8),
    },
    'send-weekly-notification-digest': {
        'task': 'apps.notifications.tasks.send_weekly_notification_digest',
        'schedule': crontab(minute=15, hour=8, day_of_week='monday'),
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.qq.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

TESSERACT_CMD = os.environ.get('TESSERACT_CMD', '')
OCR_TESSERACT_LANG = os.environ.get('OCR_TESSERACT_LANG', 'chi_sim+eng')

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
