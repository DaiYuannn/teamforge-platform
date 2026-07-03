import os

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True

os.environ.setdefault(
    'FIELD_ENCRYPTION_KEY',
    'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=',
)

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

try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS = list(INSTALLED_APPS) + ['debug_toolbar']  # noqa: F405
    MIDDLEWARE = list(MIDDLEWARE) + ['debug_toolbar.middleware.DebugToolbarMiddleware']  # noqa: F405
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass
