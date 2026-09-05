from config.settings import BASE_DIR, DATABASES
from config.local_settings import (
    ERROR_DISCORD_URL,
    GOOGLE_DRIVE_CLIENT_ID,
    GOOGLE_DRIVE_CLIENT_SECRET,
    GOOGLE_DRIVE_REFRESH_TOKEN,
    GOOGLE_DRIVE_FOLDER_ID,
)
from django.core.management.base import BaseCommand
from django.utils import timezone
from subekashi.lib.discord import send_discord
from subekashi.lib.google_drive import upload_backup, delete_old_backups
import os
import shutil
import stat
import subprocess
import tempfile

# 所有者のみ読み書き可能（0600）。DBダンプ・DB認証情報という機密性の高いファイルを
# 一時的に書き出す際、他ユーザーから読み取れないようにするため使う
OWNER_READ_WRITE_ONLY = stat.S_IRUSR | stat.S_IWUSR


class Command(BaseCommand):
    help = "バックアップ"

    BACKUP_FOLDER_NUMS = 50
    MYSQLDUMP_TIMEOUT_SECONDS = 600
    NOW_OPTION_FILE_NAME = "subekashi_latest"

    def add_arguments(self, parser):
        parser.add_argument(
            '-n', '--now',
            action='store_true',
            help='スケジュールを無視し、固定ファイル名でダンプの取得のみを行う'
                 '（Google Driveへのアップロード・古いバックアップの削除は行わない。ローカル開発環境への同期用）',
        )

    def handle(self, *args, **options):
        db_settings = DATABASES['default']
        is_mysql = db_settings['ENGINE'] == 'django.db.backends.mysql'

        if options['now']:
            self._dump_now(db_settings, is_mysql)
            return

        # サーバーOSのタイムゾーン設定（本番PythonAnywhereサーバーはUTC）に依存する
        # datetime.now()は使わず、Djangoの設定タイムゾーン(Asia/Tokyo)基準で
        # スケジュール判定・ファイル名生成を行う
        now = timezone.localtime(timezone.now())
        if now.hour % 6 != 0:
            return

        if not (GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET and GOOGLE_DRIVE_REFRESH_TOKEN and GOOGLE_DRIVE_FOLDER_ID):
            self.stderr.write(self.style.ERROR("Google Driveの認証情報が設定されていません"))
            return

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
                    # DBダンプという機密性の高いファイルのため、tempfile.TemporaryDirectory()
                    # のumask依存のパーミッションに任せず明示的に絞る
                    os.chmod(backup_path, OWNER_READ_WRITE_ONLY)
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

    def _dump_now(self, db_settings, is_mysql):
        """--now指定時の処理。スケジュールガード・Google Driveへのアップロード・
        古いバックアップの削除は行わず、固定ファイル名でのダンプの取得のみを行う
        （ローカル開発環境への同期スクリプト等から常に同じパスを参照できるようにするため）"""
        file_name = f"{self.NOW_OPTION_FILE_NAME}.{'sql' if is_mysql else 'sqlite3'}"
        backup_path = os.path.join(BASE_DIR, file_name)
        try:
            if is_mysql:
                self._dump_mysql(db_settings, backup_path)
            else:
                shutil.copy2(db_settings['NAME'], backup_path)
                # DBダンプという機密性の高いファイルのため、明示的にパーミッションを絞る
                os.chmod(backup_path, OWNER_READ_WRITE_ONLY)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"ダンプの取得中にエラーが発生しました：{str(e)}"))
            return

        self.stdout.write(self.style.SUCCESS(f"ダンプを取得しました：{backup_path}"))

    def _dump_mysql(self, db_settings, backup_path):
        """mysqldumpでDB全体をSQLファイルに出力する。
        --no-tablespacesは、共有ホスティング環境のDBユーザーには通常PROCESS権限が
        付与されておらず、付けないとテーブルスペース情報のダンプでエラーになるため付与する。
        --single-transactionは、InnoDB前提でLOCK TABLES権限が無くても整合性のある
        スナップショットを取得するため（テーブルは全てInnoDBであることを確認済み）。
        --default-character-set=utf8mb4は、絵文字等の4バイト文字を含むデータの
        文字化けを防ぐため（config/settings.pyのDB接続設定と合わせる）。
        --routines --eventsは、ストアドプロシージャ・イベントを使い始めた場合に備えて
        付与する（現状は未使用だが、mysqldumpは既定でこれらをダンプしない。
        --triggersは既定で有効だが意図を明示するため付与する）"""
        cnf_fd, cnf_path = tempfile.mkstemp(suffix=".cnf")
        try:
            # MySQL公式ドキュメントでは、環境変数MYSQL_PWD経由のパスワード受け渡しも
            # 一部環境ではpsやプロセス環境の参照で露出しうるとして非推奨としているため、
            # パーミッション0600の一時オプションファイル経由で渡す（コードレビュー対応）
            os.chmod(cnf_path, OWNER_READ_WRITE_ONLY)
            with os.fdopen(cnf_fd, "w") as cnf_file:
                cnf_file.write("[client]\n")
                cnf_file.write(f'user="{self._escape_cnf_value(db_settings["USER"])}"\n')
                cnf_file.write(f'password="{self._escape_cnf_value(db_settings["PASSWORD"])}"\n')
                cnf_file.write(f'host="{self._escape_cnf_value(db_settings["HOST"])}"\n')
                if db_settings.get("PORT"):
                    cnf_file.write(f'port={db_settings["PORT"]}\n')

            # --defaults-extra-fileはmysqldumpの最初のオプションとして指定する必要がある
            command = [
                "mysqldump", f"--defaults-extra-file={cnf_path}",
                "--no-tablespaces", "--single-transaction", "--default-character-set=utf8mb4",
                "--routines", "--events", "--triggers",
                db_settings["NAME"],
            ]

            try:
                with open(backup_path, "wb") as f:
                    # DBダンプという機密性の高いファイルのため、tempfile.TemporaryDirectory()の
                    # umask依存のパーミッションに任せず明示的に絞る
                    os.chmod(backup_path, OWNER_READ_WRITE_ONLY)
                    result = subprocess.run(
                        command, stdout=f, stderr=subprocess.PIPE, timeout=self.MYSQLDUMP_TIMEOUT_SECONDS
                    )
            except subprocess.TimeoutExpired as e:
                # TimeoutExpired.__str__()は渡したcmd（DB名を含むコマンド引数リストそのもの）を
                # そのまま文字列化するため、returncode != 0のケースと同様に詳細はサーバーの
                # 標準エラー出力にのみ残し、例外（Discord通知に使われる）には
                # 一般化したメッセージのみを含める
                self.stderr.write(self.style.ERROR(f"mysqldumpタイムアウト詳細：{str(e)}"))
                raise RuntimeError(f"mysqldumpがタイムアウトしました（{self.MYSQLDUMP_TIMEOUT_SECONDS}秒）")

            if result.returncode != 0:
                # mysqldumpのstderrにはホスト名・ユーザー名等の接続情報が含まれ得る。
                # ERROR_DISCORD_URLは公開チャンネルのため、詳細はサーバーの標準エラー
                # 出力にのみ残し、例外（Discord通知に使われる）には一般化した
                # メッセージのみを含める
                self.stderr.write(self.style.ERROR(
                    f"mysqldump stderr（exit code {result.returncode}）：{result.stderr.decode(errors='replace')}"
                ))
                raise RuntimeError(f"mysqldumpが失敗しました（exit code {result.returncode}）")
        finally:
            os.remove(cnf_path)

    @staticmethod
    def _escape_cnf_value(value):
        """MySQLオプションファイルのダブルクォート内で使える形にエスケープする"""
        return value.replace("\\", "\\\\").replace('"', '\\"')
