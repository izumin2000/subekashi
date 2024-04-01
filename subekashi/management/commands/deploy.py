import subprocess
from django.core.management.base import BaseCommand
from subekashi.models import *
from config.local_settings import PYTHONANYWHERE_USERNAME, PYTHONANYWHERE_TOKEN
import requests


class Command(BaseCommand) :
    def handle(self, *args, **options):
        try:
            subprocess.check_output(['git', 'pull', 'origin', 'main'])
            subprocess.check_output(['pip', 'install', '-r', 'requirements.txt'])
            subprocess.check_output(['python', 'manage.py', 'makemigrations'])
            subprocess.check_output(['python', 'manage.py', 'migrate'])
            subprocess.check_output(['python', 'manage.py', 'collectstatic', '--noinput'])
            command = ['git', 'rev-list', '--count', 'main']
            commit_count = subprocess.check_output(command).strip().decode('utf8')
            subprocess.check_output(['python', 'manage.py', 'setlast', '--v', commit_count])
            
            response = requests.post(
                f'https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/webapps/lyrics.imicomweb.com/reload/',
                headers={'Authorization': f'Token {PYTHONANYWHERE_TOKEN}'}
            )
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f"デプロイが完了しました。"))
            else:
                self.stderr.write(self.style.ERROR('{}: {!r}'.format(response.status_code, response.content)))
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(e))
            pass
