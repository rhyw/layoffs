"""
Django settings for layoffs_tracker project.
"""

from pathlib import Path
import environ

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
env.read_env(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Application definition
INSTALLED_APPS = [
    # Django built-in
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'corsheaders',
    'rest_framework',
    'django_htmx',
    'django_celery_beat',

    # Custom apps
    'layoffs',
    'news',
    'scraper',
    'community',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'layoffs_tracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'layoffs' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'layoffs_tracker.wsgi.application'

# Database
DATABASES = {
    'default': env.db_url('DATABASE_URL', default='sqlite:///db.sqlite3'),
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'layoffs' / 'static',
]

# WhiteNoise static file compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_ORDERING': ['-date_reported'],
}

# Celery Configuration
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery Beat schedule — defines periodic task intervals in code.
# Tasks can also be managed at runtime via django-celery-beat admin.
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'collect-all-sources': {
        'task': 'scraper.tasks.collect_all_sources',
        'schedule': crontab(hour='0,12', minute='0'),
        'options': {'expires': 600},
    },
    'collect-news-articles': {
        'task': 'scraper.tasks.collect_news_articles',
        'schedule': crontab(hour='0,12', minute='5'),
        'options': {'expires': 600},
    },
    'enrich-pending-events': {
        'task': 'scraper.tasks.enrich_pending_events',
        'schedule': crontab(hour='0,12', minute='10'),
        'options': {'expires': 300},
    },
    'process-scraped-articles': {
        'task': 'scraper.tasks.process_scraped_articles',
        'schedule': crontab(hour='0,12', minute='15'),
        'options': {'expires': 600},
    },
    'cleanup-stale-data': {
        'task': 'scraper.tasks.cleanup_stale_data',
        'schedule': crontab(hour='3', minute='0'),
        'options': {'expires': 3600},
    },
}

# Security — production settings behind Cloudflare proxy
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False          # Cloudflare handles HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# CORS — allow GitHub Pages to fetch from the API
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['https://myname.github.io'],
)
CORS_URLS_REGEX = r'^/api/.*$'

# DeepSeek LLM Configuration
DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY', default='')
DEEPSEEK_MODEL = env('DEEPSEEK_MODEL', default='deepseek-chat')
DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
