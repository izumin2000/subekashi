from django.core.management.base import BaseCommand
from config.local_settings import PYTHONANYWHERE_USERNAME, PYTHONANYWHERE_TOKEN
import subprocess
import requests


class Command(BaseCommand) :
    def add_arguments(self, parser):
        parser.add_argument(
            '-m', '--no-migrate',
            action='store_true',
            help='マイグレーションをスキップする',
        )

    def handle(self, *args, **options):
        COMMANDS = [
            "git pull origin main",
            "pip install -r requirements.txt",
            "python manage.py collectstatic --noinput",
            "python manage.py appversion"
        ]
        if not options['no_migrate']:
            COMMANDS.insert(2, "python manage.py migrate")
        
        try:
            # エラーハンドリング
            if (PYTHONANYWHERE_USERNAME == "") or (PYTHONANYWHERE_TOKEN == "") :
                raise ValueError("PYTHONANYWHERE_USERNAMEかPYTHONANYWHERE_TOKENが空です。")
            
            # コマンドを1行ずつ実行
            for command in COMMANDS:
                output = subprocess.check_output(command.split())
                if type(output) == bytes:
                    output = output.decode()
                self.stdout.write(self.style.HTTP_INFO(output))
            
            # アプリをリロード
            response = requests.post(
                f'https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/webapps/lyrics.imicomweb.com/reload/',
                headers={'Authorization': f'Token {PYTHONANYWHERE_TOKEN}'}
            )
            
            # リロードの通信に失敗したら
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("デプロイが完了しました。"))
            else:
                self.stderr.write(self.style.ERROR('{}: {!r}'.format(response.status_code, response.content)))
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(e))
            pass
