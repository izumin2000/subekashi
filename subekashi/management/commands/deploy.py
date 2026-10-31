from django.core.management.base import BaseCommand, CommandError
from config.local_settings import PYTHONANYWHERE_USERNAME, PYTHONANYWHERE_TOKEN, VENV_PATH
import subprocess
import time
import requests

RELOAD_TIMEOUT = 30
RELOAD_MAX_ATTEMPTS = 4
RELOAD_RETRY_INTERVAL = 10


class Command(BaseCommand) :
    def add_arguments(self, parser):
        parser.add_argument(
            '-m', '--no-migrate',
            action='store_true',
            help='マイグレーションをスキップする',
        )

    def handle(self, *args, **options):
        # VENV_PATHが設定されていれば仮想環境のpip/pythonを使う。
        # 未設定（空文字列）の場合は従来通りグローバルのpip/pythonを使う
        pip = f"{VENV_PATH}/bin/pip" if VENV_PATH else "pip"
        python = f"{VENV_PATH}/bin/python" if VENV_PATH else "python"

        COMMANDS = [
            "git pull origin main",
            f"{pip} install -r requirements.txt",
            f"{python} manage.py collectstatic --noinput --clear",
            f"{python} manage.py appversion"
        ]
        if not options['no_migrate']:
            COMMANDS.insert(2, f"{python} manage.py migrate")

        # 失敗はCommandErrorで伝え、0以外の終了コードで終える
        if (PYTHONANYWHERE_USERNAME == "") or (PYTHONANYWHERE_TOKEN == "") :
            raise CommandError("PYTHONANYWHERE_USERNAMEかPYTHONANYWHERE_TOKENが空です。")

        # コマンドを1行ずつ実行
        for command in COMMANDS:
            try:
                output = subprocess.check_output(command.split())
            except subprocess.CalledProcessError as e:
                raise CommandError(
                    f"{command} が失敗しました（終了コード{e.returncode}）。リロードは実行していません。"
                ) from None
            if type(output) == bytes:
                output = output.decode()
            self.stdout.write(self.style.HTTP_INFO(output))

        self.reload(COMMANDS)
        self.stdout.write(self.style.SUCCESS("デプロイが完了しました。"))

    def reload(self, completed_commands):
        # 一時的な接続失敗（接続エラー・タイムアウト・5xx）だけ間隔を空けて再試行する。4xxなどは再試行しても直らない
        for attempt in range(1, RELOAD_MAX_ATTEMPTS + 1):
            try:
                response = requests.post(
                    f'https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/webapps/lyrics.imicomweb.com/reload/',
                    headers={'Authorization': f'Token {PYTHONANYWHERE_TOKEN}'},
                    timeout=RELOAD_TIMEOUT,
                )
            except (requests.ConnectionError, requests.Timeout) as e:
                reason = str(e)
            except requests.RequestException as e:
                raise self.reload_error(str(e), completed_commands) from None
            else:
                if response.status_code == 200:
                    return
                reason = '{}: {!r}'.format(response.status_code, response.content)
                if response.status_code < 500:
                    raise self.reload_error(reason, completed_commands)

            if attempt < RELOAD_MAX_ATTEMPTS:
                self.stderr.write(self.style.WARNING(
                    f"リロードに失敗しました（{reason}）。{RELOAD_RETRY_INTERVAL}秒後に再試行します（{attempt}/{RELOAD_MAX_ATTEMPTS}回目）"
                ))
                time.sleep(RELOAD_RETRY_INTERVAL)

        raise self.reload_error(reason, completed_commands)

    def reload_error(self, reason, completed_commands):
        # 古いコードのまま新しいDBスキーマで動き続けないよう、どこまで終わっていて何をすればよいかを伝える
        completed = "\n".join(f"  - {command}" for command in completed_commands)
        return CommandError(
            f"リロードに失敗しました（{reason}）。アプリは再起動されていません。\n"
            f"完了した手順:\n{completed}\n"
            "PythonAnywhereのWebタブでReloadを押すか、python manage.py deploy -m を再実行してください。"
        )
