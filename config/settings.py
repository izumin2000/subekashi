from pathlib import Path
import os
from .local_settings import *

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "subekashi" ,"static"),
]

ROOT_URL = "http://subekashi.localhost:8000" if DEBUG else "https://lyrics.imicomweb.com"

CORS_ALLOW_CREDENTIALS = True
ALLOWED_HOSTS = [
    'subekashi.localhost',
    'lyrics.imicomweb.com',
]

INSTALLED_APPS = [
    'config',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_hosts',
    'subekashi',
    'article',
    'corsheaders',
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
    'django_hosts.middleware.HostsResponseMiddleware',
    'subekashi.middleware.restrict_ip.RestrictIPMiddleware',
    'subekashi.middleware.cache.CacheControlMiddleware',
    'subekashi.middleware.rate_limit.RatelimitMiddleware',
    'subekashi.middleware.normalize_post_middleware.NormalizePostDataMiddleware',
]

ROOT_URLCONF = 'config.urls'
ROOT_HOSTCONF = 'config.hosts'
DEFAULT_HOST = 'subekashi'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'subekashi.lib.context_processors.context_processors',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

WSGI_APPLICATION = 'config.wsgi.application'

SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = 'sessions'

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

if DEBUG :
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else :
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "izuminapp$default",
            "USER": "izuminapp",
            "PASSWORD": MYSQL_PASSWORD,
            "HOST": "izuminapp.mysql.pythonanywhere-services.com",
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'ja'

TIME_ZONE = 'Asia/Tokyo'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

DEFAULT_AUTO_FIELD='django.db.models.AutoField'

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "django_ratelimit": {
            "handlers": ["null"],
            "level": "ERROR",  # もしくは "CRITICAL" にしてログを抑制
            "propagate": False,
        },
    },
}

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

CORS_ALLOW_ALL_ORIGINS = True