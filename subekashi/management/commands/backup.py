from config.settings import DEBUG, DATABASES
from datetime import datetime
import os
import shutil
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "バックアップ"
    
    def handle(self, *args, **options) :
        BACKUP_FOLDER_NUMS = 30
        BACKUP_FOLDER = "backups/" if DEBUG else "/home/izuminapp/izuminapp/backups/"

        files = os.listdir(BACKUP_FOLDER)
        now = datetime.now()
        if len(files) <= BACKUP_FOLDER_NUMS :
            if now.hour % 6 == 0 :
                db_path = DATABASES['default']['NAME']
                fileName = now.strftime('%Y-%m-%d-%H-%M-%S')
                backup_path = os.path.join(BACKUP_FOLDER, f'{fileName}.sqlite3')
                shutil.copy2(db_path, backup_path)

        if len(files) >= BACKUP_FOLDER_NUMS :
            files.sort()
            first_file = os.path.join(BACKUP_FOLDER, files[0])
            
            try:
                os.remove(first_file)
            except OSError as e:
                self.stdout.write(self.style.ERROR(f"ファイルの削除中にエラーが発生しました：{str(e)}"))