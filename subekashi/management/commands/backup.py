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
import subprocess
import tempfile


class Command(BaseCommand):
    help = "バックアップ"

    BACKUP_FOLDER_NUMS = 50
    MYSQLDUMP_TIMEOUT_SECONDS = 600

    def handle(self, *args, **options):
        now = datetime.now()
        if now.hour % 6 != 0:
            return

        if not (GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET and GOOGLE_DRIVE_REFRESH_TOKEN and GOOGLE_DRIVE_FOLDER_ID):
            self.stderr.write(self.style.ERROR("Google Driveの認証情報が設定されていません"))
            return

        db_settings = DATABASES['default']
        is_mysql = db_settings['ENGINE'] == 'django.db.backends.mysql'
        file_name = f"{now.strftime('%Y-%m-%d-%H')}.{'sql' if is_mysql else 'sqlite3'}"
        # application/sqlはIANA未登録のため、慣例に合わせテキストファイルとして扱う
        mimetype = "text/plain" if is_mysql else "application/x-sqlite3"

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                backup_path = os.path.join(tmp_dir, file_name)
                if is_mysql:
                    self._dump_mysql(db_settings, backup_path)
                else:
                    shutil.copy2(db_settings['NAME'], backup_path)
                upload_backup(backup_path, file_name, mimetype=mimetype)
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

    def _dump_mysql(self, db_settings, backup_path):
        """mysqldumpでDB全体をSQLファイルに出力する。パスワードは環境変数MYSQL_PWD経由で渡し、
        コマンドライン引数（psコマンド等から見える）には含めない。
        --no-tablespacesは、共有ホスティング環境のDBユーザーには通常PROCESS権限が
        付与されておらず、付けないとテーブルスペース情報のダンプでエラーになるため付与する。
        --single-transactionは、InnoDB前提でLOCK TABLES権限が無くても整合性のある
        スナップショットを取得するため（テーブルは全てInnoDBであることを確認済み）。
        --default-character-set=utf8mb4は、絵文字等の4バイト文字を含むデータの
        文字化けを防ぐため（config/settings.pyのDB接続設定と合わせる）。
        --routines --eventsは、ストアドプロシージャ・イベントを使い始めた場合に備えて
        付与する（現状は未使用だが、mysqldumpは既定でこれらをダンプしない。
        --triggersは既定で有効だが意図を明示するため付与する）"""
        command = [
            'mysqldump', '--no-tablespaces', '--single-transaction', '--default-character-set=utf8mb4',
            '--routines', '--events', '--triggers',
            '-h', db_settings['HOST'], '-u', db_settings['USER'],
        ]
        if db_settings.get('PORT'):
            command += ['-P', str(db_settings['PORT'])]
        command.append(db_settings['NAME'])

        env = os.environ.copy()
        env['MYSQL_PWD'] = db_settings['PASSWORD']

        with open(backup_path, 'wb') as f:
            result = subprocess.run(
                command, stdout=f, stderr=subprocess.PIPE, env=env, timeout=self.MYSQLDUMP_TIMEOUT_SECONDS
            )
        if result.returncode != 0:
            # mysqldumpのstderrにはホスト名・ユーザー名等の接続情報が含まれ得る。
            # ERROR_DISCORD_URLは公開チャンネルのため、詳細はサーバーの標準エラー
            # 出力にのみ残し、例外（Discord通知に使われる）には一般化した
            # メッセージのみを含める
            self.stderr.write(self.style.ERROR(
                f"mysqldump stderr（exit code {result.returncode}）：{result.stderr.decode(errors='replace')}"
            ))
            raise RuntimeError(f"mysqldumpが失敗しました（exit code {result.returncode}）")
