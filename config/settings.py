from pathlib import Path
import os
import sys
from .local_settings import *

# テスト実行時は local_settings.py の値によらず Discord への送信を無効化する
if 'test' in sys.argv:
    SEND_DISCORD = False

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = []

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
    'django.contrib.humanize',
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
    'subekashi.middleware.maintenance.MaintenanceMiddleware',
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

DATABASES = {
    'default':
    {
        "ENGINE": "django.db.backends.mysql",
        "NAME": MYSQL_NAME,
        "USER": MYSQL_USER,
        "PASSWORD": MYSQL_PASSWORD,
        "HOST": MYSQL_HOST,
        **({"PORT": MYSQL_PORT} if MYSQL_PORT else {}),
        # PythonAnywhereの共有MySQLサーバーはsql_modeにSTRICT_TRANS_TABLESを
        # 含まない設定になっており、max_length超過等の不正な値を挿入しようとしても
        # エラーにならず警告のみで黙って切り詰められてしまう（#593の移行作業で発覚、#1091）。
        # サーバー側の設定に依存せず常にstrictな検証が働くよう、接続時に明示的に設定する。
        # 既存のsql_mode（環境によって異なりうる）を上書きしないよう追加する形にする。
        # init_commandは全接続確立時に毎回実行されるため、万一@@sql_modeが空文字列の
        # 環境があった場合に先頭カンマ付きの値になってエラーにならないよう、
        # IF()で空文字列ガードを入れておく（コードレビュー対応）
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": (
                "SET sql_mode=CONCAT("
                "IF(@@sql_mode = '', '', CONCAT(@@sql_mode, ',')), 'STRICT_TRANS_TABLES')"
            ),
        },
        # MySQLサーバーの既定照合順序に依存すると環境ごとに挙動が変わってしまうため
        # （#1092、本番はutf8mb4_binで運用しているが、サーバー設定次第では
        # 大文字小文字を区別しないutf8mb4_general_ci等でテストDBが作られうる）、
        # テストDBの照合順序を明示的に本番と揃える
        "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_bin"},
    }
} if USE_MYSQL else {
    'default':
    {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
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

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "3600/hour",
    },
}
