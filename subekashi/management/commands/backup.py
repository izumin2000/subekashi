from config.settings import DATABASES
from config.local_settings import (
    ERROR_DISCORD_URL,
    GOOGLE_DRIVE_CLIENT_ID,
    GOOGLE_DRIVE_CLIENT_SECRET,
    GOOGLE_DRIVE_REFRESH_TOKEN,
    GOOGLE_DRIVE_FOLDER_ID,
)
from django.core.management.base import BaseCommand
from datetime import datetime
from subekashi.lib.discord import send_discord
from subekashi.lib.google_drive import upload_backup, delete_old_backups
import os
import shutil
import tempfile


class Command(BaseCommand):
    help = "バックアップ"

    BACKUP_FOLDER_NUMS = 50

    def handle(self, *args, **options):
        now = datetime.now()
        if now.hour % 6 != 0:
            return

        if not (GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET and GOOGLE_DRIVE_REFRESH_TOKEN and GOOGLE_DRIVE_FOLDER_ID):
            self.stderr.write(self.style.ERROR("Google Driveの認証情報が設定されていません"))
            return

        db_path = DATABASES['default']['NAME']
        file_name = f"{now.strftime('%Y-%m-%d-%H')}.sqlite3"

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                backup_path = os.path.join(tmp_dir, file_name)
                shutil.copy2(db_path, backup_path)
                upload_backup(backup_path, file_name)
        except Exception as e:
            message = f"Google Driveへのバックアップ中にエラーが発生しました：{str(e)}"
            self.stderr.write(self.style.ERROR(message))
            send_discord(ERROR_DISCORD_URL, message)
            return

        try:
            delete_old_backups(self.BACKUP_FOLDER_NUMS)
        except Exception as e:
            message = f"Google Driveの古いバックアップの削除中にエラーが発生しました：{str(e)}"
            self.stderr.write(self.style.ERROR(message))
            send_discord(ERROR_DISCORD_URL, message)
