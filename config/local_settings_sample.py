# from django.core.management.utils import get_random_secret_key
# get_random_secret_key()

SECRET_KEY = ''

NEW_DISCORD_URL = ''
CONTACT_DISCORD_URL = ''
ERROR_DISCORD_URL = ''
DSP_DISCORD_URL = ''

PYTHONANYWHERE_USERNAME = ''
PYTHONANYWHERE_TOKEN = ''

# manage.py deploy でpip/pythonを実行する際に使う仮想環境のパス（例: '/home/username/.virtualenvs/subekashi-venv'）。
# 空文字列の場合はグローバルのpip/pythonを使う
VENV_PATH = ''

YOUTUBE_API_KEY = ''

# manage.py timeline で読み取るすべあな界隈年表のID（URLの /d/ と /edit の間の文字列）と、Google Sheets APIを有効にしたAPIキー。
# APIキーでは公開されているスプレッドシートの読み取りしかできない
GOOGLE_SHEETS_SPREADSHEET_ID = '1kkVYxRtlby7KuCcAO4ATT_4ruHUoIYZRN2bDoew8T9w'
GOOGLE_SHEETS_API_KEY = ''

# /api/news/ にニュースをPOSTするときのX-API-Keyヘッダーの値。空文字列の場合はPOSTを受け付けない
# import secrets
# secrets.token_urlsafe(32)
API_KEY = ''

DEBUG = True

SEND_DISCORD = False

USE_MYSQL = False
MYSQL_HOST = ""
MYSQL_PORT = ""
MYSQL_USER = ""
MYSQL_NAME = ""
MYSQL_PASSWORD = ""

GOOGLE_DRIVE_CLIENT_ID = ""
GOOGLE_DRIVE_CLIENT_SECRET = ""
GOOGLE_DRIVE_REFRESH_TOKEN = ""
GOOGLE_DRIVE_FOLDER_ID = ""
