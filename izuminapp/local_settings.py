import os

#settings.pyからそのままコピー
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'q93+xpfmw33@ug#5xea$z6i1p!yhn(qxi4-88=-npj^ppftd+a'

#settings.pyからそのままコピー
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

DEBUG = True #ローカルでDebugできるようになります