from django.core.management.base import BaseCommand
from config.local_settings import PYTHONANYWHERE_USERNAME, PYTHONANYWHERE_TOKEN
import subprocess
import requests


class Command(BaseCommand) :
    def handle(self, *args, **options):
        COMMANDS = [
            "git pull origin main", 
            "pip install -r requirements.txt", 
            "python manage.py makemigrations", 
            "python manage.py migrate", 
            "python manage.py collectstatic --noinput", 
            "python manage.py appversion"
        ]
        
        try:
            for command in COMMANDS:
                output = subprocess.check_output(command.split())
                if type(output) == bytes:
                    output = output.decode()
                self.stdout.write(self.style.HTTP_INFO(output))
            
            response = requests.post(
                f'https://www.pythonanywhere.com/api/v0/user/{PYTHONANYWHERE_USERNAME}/webapps/lyrics.imicomweb.com/reload/',
                headers={'Authorization': f'Token {PYTHONANYWHERE_TOKEN}'}
            )
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("デプロイが完了しました。"))
            else:
                self.stderr.write(self.style.ERROR('{}: {!r}'.format(response.status_code, response.content)))
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(e))
            pass
