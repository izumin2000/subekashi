import subprocess
from django.core.management.base import BaseCommand
from subekashi.models import *


class Command(BaseCommand) :
    def handle(self, *args, **options):
        try:
            subprocess.check_output(['git', 'pull', 'origin', 'main'])
            subprocess.check_output(['pip', 'install', '-r', 'requirements.txt'])
            subprocess.check_output(['python', 'manage.py', 'makemigrations'])
            subprocess.check_output(['python', 'manage.py', 'migrate'])
            subprocess.check_output(['python', 'manage.py', 'collectstatic', '--noinput'])
            self.stdout.write(self.style.SUCCESS(f"デプロイが完了しました。"))
            command = ['git', 'rev-list', '--count', 'main']
            commit_count = subprocess.check_output(command).strip().decode('utf8')
            self.stdout.write(self.style.SUCCESS(f"commit数: {commit_count}"))
            subprocess.check_output(['python', 'manage.py', 'setlast', '--v', commit_count])
        except :
            pass
