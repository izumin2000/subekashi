"""
管理コマンドのテスト

delete: is_removedをfalseのままにする--keep-linksオプションを検証する。
youtube: DBロック対策で処理方式を変更した後の挙動（id指定・全件処理・リンク無しスキップ・動画削除時の扱い）を検証する。
backup: バックアップ先をサーバーストレージからGoogle Driveに変更した挙動（#1050）を検証する。
word: word.jsonから模倣単語候補をWordに一括登録する処理（#1053）を検証する。
ai: Song.lyricsの単語をランダムに入れ替えてgenetype="janome"のAiレコードをシードする処理を検証する。
stats: 月次統計(Stats)を最古のSongの月〜今月まで再計算する処理（#334）を検証する。
"""
import json
import os
import stat
import subprocess
from datetime import datetime
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from subekashi.management.commands.backup import Command
from subekashi.models import Ai, Song, SongLink, Stats, Word


def timezone_aware(year, month, day):
    return timezone.make_aware(datetime(year, month, day))


class DeleteCommandTest(TestCase):
    """delete コマンドのテスト"""

    def setUp(self):
        self.song = Song.objects.create(title="削除テスト曲")
        self.link = SongLink.objects.create(url="https://youtu.be/deletetest01")
        self.link.songs.add(self.song)

    def test_delete_removes_song(self):
        call_command("delete", str(self.song.id))
        self.assertFalse(Song.objects.filter(pk=self.song.id).exists())

    def test_delete_sets_links_is_removed_true_by_default(self):
        call_command("delete", str(self.song.id))
        self.link.refresh_from_db()
        self.assertTrue(self.link.is_removed)

    def test_delete_with_keep_links_does_not_set_is_removed(self):
        call_command("delete", str(self.song.id), "--keep-links")
        self.link.refresh_from_db()
        self.assertFalse(self.link.is_removed)

    def test_nonexistent_song_id_does_not_raise(self):
        # 存在しないIDを指定してもエラーにならないこと
        call_command("delete", "999999")


class YoutubeCommandTest(TestCase):
    """youtube コマンドのテスト"""

    def setUp(self):
        self.song1 = Song.objects.create(title="YouTube曲1")
        self.link1 = SongLink.objects.create(url="https://youtu.be/aaaaaaaaaaa")
        self.link1.songs.add(self.song1)

        self.song2 = Song.objects.create(title="YouTube曲2")
        self.link2 = SongLink.objects.create(url="https://youtu.be/bbbbbbbbbbb")
        self.link2.songs.add(self.song2)

        self.song_without_link = Song.objects.create(title="リンク無し曲")

    @patch("subekashi.management.commands.youtube.sleep")
    @patch("subekashi.management.commands.youtube.get_youtube_api")
    def test_id_option_updates_only_that_song(self, mock_api, mock_sleep):
        mock_api.return_value = {"view": 100, "like": 10, "upload_time": None}
        call_command("youtube", id=self.song1.id)

        self.song1.refresh_from_db()
        self.song2.refresh_from_db()
        self.assertEqual(self.song1.view, 100)
        self.assertEqual(self.song2.view, None)

    @patch("subekashi.management.commands.youtube.sleep")
    @patch("subekashi.management.commands.youtube.get_youtube_api")
    def test_without_id_updates_all_songs_with_links(self, mock_api, mock_sleep):
        mock_api.return_value = {"view": 50, "like": 5, "upload_time": None}
        call_command("youtube")

        self.song1.refresh_from_db()
        self.song2.refresh_from_db()
        self.assertEqual(self.song1.view, 50)
        self.assertEqual(self.song2.view, 50)

    @patch("subekashi.management.commands.youtube.sleep")
    @patch("subekashi.management.commands.youtube.get_youtube_api")
    def test_song_without_links_is_skipped(self, mock_api, mock_sleep):
        mock_api.return_value = {"view": 50, "like": 5, "upload_time": None}
        call_command("youtube")

        self.song_without_link.refresh_from_db()
        self.assertIsNone(self.song_without_link.view)

    @patch("subekashi.management.commands.youtube.sleep")
    @patch("subekashi.management.commands.youtube.get_youtube_api")
    def test_all_videos_unavailable_marks_song_deleted(self, mock_api, mock_sleep):
        # 動画が削除されている場合、get_youtube_apiは{}を返す
        mock_api.return_value = {}
        call_command("youtube", id=self.song1.id)

        self.song1.refresh_from_db()
        self.assertTrue(self.song1.is_deleted)
        self.assertEqual(self.song1.view, 0)


SQLITE_DB_SETTINGS = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "/tmp/db.sqlite3"},
}
MYSQL_DB_SETTINGS = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "testdb",
        "USER": "testuser",
        "PASSWORD": "testpass",
        "HOST": "testhost",
        "PORT": "3307",
    },
}


class BackupCommandTest(TestCase):
    """backup コマンドのテスト（バックアップ先をGoogle Driveに変更、#1050。
    MySQL移行対応でmysqldump方式を追加、#1086）

    DATABASESはUSE_MYSQL設定によって実行環境ごとに変わるため、テストごとに
    SQLITE_DB_SETTINGS/MYSQL_DB_SETTINGSへ明示的に差し替えて分岐を検証する。
    """

    def _run(self):
        out = StringIO()
        err = StringIO()
        call_command("backup", stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    @staticmethod
    def _create_dummy_file(src, dst):
        """shutil.copy2()のside_effectとして使う。実装がコピー後にos.chmod(dst, ...)を
        呼ぶため、モックで済ませず実際にファイルを作成しておく必要がある"""
        with open(dst, "wb") as f:
            f.write(b"dummy")

    def _capture_cnf_and_return(self, captured, returncode=0, stderr=b""):
        """subprocess.run()のside_effectとして使う。--defaults-extra-fileで指定された
        一時オプションファイルは_dump_mysql()のfinallyで削除されるため、削除される前に
        中身・パーミッション・コマンド全体をcapturedに保存しておく"""
        def side_effect(command, **kwargs):
            cnf_arg = next(a for a in command if a.startswith("--defaults-extra-file="))
            cnf_path = cnf_arg.split("=", 1)[1]
            with open(cnf_path) as f:
                captured["cnf_content"] = f.read()
            captured["cnf_mode"] = stat.S_IMODE(os.stat(cnf_path).st_mode)
            captured["cnf_path"] = cnf_path
            captured["command"] = command
            return MagicMock(returncode=returncode, stderr=stderr)
        return side_effect

    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.datetime")
    def test_skips_when_not_scheduled_hour(self, mock_datetime, mock_upload, mock_delete):
        # 6時間おき（0, 6, 12, 18時）以外は何もしない
        mock_datetime.now.return_value = datetime(2026, 1, 1, 1, 0, 0)

        self._run()

        mock_upload.assert_not_called()
        mock_delete.assert_not_called()

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.datetime")
    def test_skips_when_drive_credentials_missing(self, mock_datetime, mock_upload, mock_delete):
        mock_datetime.now.return_value = datetime(2026, 1, 1, 0, 0, 0)

        _, err = self._run()

        self.assertIn("Google Driveの認証情報が設定されていません", err)
        mock_upload.assert_not_called()
        mock_delete.assert_not_called()

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.os.chmod")
    @patch("subekashi.management.commands.backup.shutil.copy2")
    @patch("subekashi.management.commands.backup.DATABASES", SQLITE_DB_SETTINGS)
    @patch("subekashi.management.commands.backup.datetime")
    def test_sqlite_uploads_to_drive_and_prunes_old_backups_on_scheduled_hour(
        self, mock_datetime, mock_copy2, mock_chmod, mock_upload, mock_delete, *_
    ):
        mock_datetime.now.return_value = datetime(2026, 1, 1, 6, 0, 0)
        mock_copy2.side_effect = self._create_dummy_file

        self._run()

        mock_copy2.assert_called_once_with("/tmp/db.sqlite3", mock_copy2.call_args.args[1])
        mock_upload.assert_called_once()
        self.assertEqual(mock_upload.call_args.args[1], "2026-01-01-06.sqlite3")
        self.assertEqual(mock_upload.call_args.kwargs["mimetype"], "application/x-sqlite3")
        mock_delete.assert_called_once_with(50)
        # コードレビュー指摘対応: DBダンプという機密性の高いファイルのため、
        # tempfile.TemporaryDirectory()のumask依存のパーミッションに任せず明示的に絞る。
        # コマンド完了後（tempfile.TemporaryDirectory()の終了時）に一時ファイル自体は
        # 削除されるため、os.statではなくos.chmodの呼び出し引数を直接検証する
        backup_path = mock_copy2.call_args.args[1]
        mock_chmod.assert_called_once_with(backup_path, stat.S_IRUSR | stat.S_IWUSR)

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.send_discord")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.shutil.copy2")
    @patch("subekashi.management.commands.backup.DATABASES", SQLITE_DB_SETTINGS)
    @patch("subekashi.management.commands.backup.datetime")
    def test_reports_error_and_skips_pruning_when_upload_fails(
        self, mock_datetime, mock_copy2, mock_upload, mock_delete, mock_send_discord, *_
    ):
        mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 0, 0)
        mock_copy2.side_effect = self._create_dummy_file
        mock_upload.side_effect = Exception("アップロード失敗")

        _, err = self._run()

        self.assertIn("Google Driveへのバックアップ中にエラーが発生しました", err)
        mock_delete.assert_not_called()
        mock_send_discord.assert_called_once()

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.send_discord")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.shutil.copy2")
    @patch("subekashi.management.commands.backup.DATABASES", SQLITE_DB_SETTINGS)
    @patch("subekashi.management.commands.backup.datetime")
    def test_reports_cleanup_error_separately_when_upload_succeeds_but_pruning_fails(
        self, mock_datetime, mock_copy2, mock_upload, mock_delete, mock_send_discord, *_
    ):
        # アップロード自体は成功しているので、削除失敗と混同しないメッセージになること
        mock_datetime.now.return_value = datetime(2026, 1, 1, 18, 0, 0)
        mock_copy2.side_effect = self._create_dummy_file
        mock_delete.side_effect = Exception("削除失敗")

        _, err = self._run()

        mock_upload.assert_called_once()
        self.assertIn("Google Driveの古いバックアップの削除中にエラーが発生しました", err)
        self.assertNotIn("Google Driveへのバックアップ中にエラーが発生しました", err)
        mock_send_discord.assert_called_once()

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.subprocess.run")
    @patch("subekashi.management.commands.backup.DATABASES", MYSQL_DB_SETTINGS)
    @patch("subekashi.management.commands.backup.datetime")
    def test_mysql_uploads_to_drive_and_prunes_old_backups_on_scheduled_hour(
        self, mock_datetime, mock_run, mock_upload, mock_delete, *_
    ):
        # #1086: USE_MYSQL=True環境ではshutil.copy2ではなくmysqldumpでダンプを取得する
        mock_datetime.now.return_value = datetime(2026, 1, 1, 6, 0, 0)
        captured = {}
        mock_run.side_effect = self._capture_cnf_and_return(captured)

        self._run()

        mock_run.assert_called_once()
        command = captured["command"]
        self.assertEqual(command[0], "mysqldump")
        self.assertTrue(command[1].startswith("--defaults-extra-file="))
        self.assertEqual(
            command[2:],
            [
                "--no-tablespaces", "--single-transaction", "--default-character-set=utf8mb4",
                "--routines", "--events", "--triggers",
                "testdb",
            ],
        )
        # コードレビュー指摘対応: MySQL_PWD環境変数はps等で露出しうるため、
        # 認証情報はコマンドライン引数にも環境変数にも含めず、
        # --defaults-extra-fileで指定した一時オプションファイル経由で渡す
        self.assertNotIn("testpass", command)
        self.assertNotIn("testhost", command)
        self.assertNotIn("testuser", command)
        self.assertNotIn("env", mock_run.call_args.kwargs)
        self.assertIn('user="testuser"', captured["cnf_content"])
        self.assertIn('password="testpass"', captured["cnf_content"])
        self.assertIn('host="testhost"', captured["cnf_content"])
        self.assertIn("port=3307", captured["cnf_content"])
        if os.name != "nt":
            # Windowsのos.chmod()は完全なUnixパーミッションを表現できないため、
            # 本番相当のLinux環境でのみ0600ちょうどであることを厳密に検証する
            self.assertEqual(captured["cnf_mode"], 0o600)
        # 一時オプションファイルは処理完了後に削除される
        self.assertFalse(os.path.exists(captured["cnf_path"]))

        # stderrを捕捉し、失敗時にDiscord通知へ含められるようにする
        self.assertEqual(mock_run.call_args.kwargs["stderr"], subprocess.PIPE)
        # ハング対策のタイムアウトが設定されている
        self.assertEqual(mock_run.call_args.kwargs["timeout"], Command.MYSQLDUMP_TIMEOUT_SECONDS)

        mock_upload.assert_called_once()
        self.assertEqual(mock_upload.call_args.args[1], "2026-01-01-06.sql")
        self.assertEqual(mock_upload.call_args.kwargs["mimetype"], "text/plain")
        mock_delete.assert_called_once_with(50)

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.subprocess.run")
    @patch("subekashi.management.commands.backup.DATABASES", {
        "default": {**MYSQL_DB_SETTINGS["default"], "PORT": ""},
    })
    @patch("subekashi.management.commands.backup.datetime")
    def test_mysql_omits_port_flag_when_port_not_configured(
        self, mock_datetime, mock_run, mock_upload, mock_delete, *_
    ):
        # config/settings.pyはMYSQL_PORT未設定時、DATABASESに'PORT'キー自体を含めない
        # （空文字ではなくキー無し）ため、その場合を再現して検証する
        mock_datetime.now.return_value = datetime(2026, 1, 1, 6, 0, 0)
        captured = {}
        mock_run.side_effect = self._capture_cnf_and_return(captured)

        self._run()

        # ポートはコマンドライン引数ではなく--defaults-extra-fileのport=として渡すため、
        # 未設定時はcnfファイルにport=行自体が含まれない
        self.assertNotIn("port=", captured["cnf_content"])

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.send_discord")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.subprocess.run")
    @patch("subekashi.management.commands.backup.DATABASES", MYSQL_DB_SETTINGS)
    @patch("subekashi.management.commands.backup.datetime")
    def test_mysql_reports_error_when_mysqldump_command_not_found(
        self, mock_datetime, mock_run, mock_upload, mock_delete, mock_send_discord, *_
    ):
        # mysqldumpコマンド自体が無い場合（PATH未設定等）も
        # 既存の「Google Driveへのバックアップ中にエラーが発生しました」に集約される
        mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 0, 0)
        mock_run.side_effect = FileNotFoundError("mysqldump not found")

        _, err = self._run()

        self.assertIn("Google Driveへのバックアップ中にエラーが発生しました", err)
        mock_upload.assert_not_called()
        mock_delete.assert_not_called()
        mock_send_discord.assert_called_once()
        # subprocess.run自体が例外を送出するケースでも、一時オプションファイルは
        # finallyブロックで確実に削除される
        command = mock_run.call_args.args[0]
        cnf_path = next(a for a in command if a.startswith("--defaults-extra-file=")).split("=", 1)[1]
        self.assertFalse(os.path.exists(cnf_path))

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.send_discord")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.subprocess.run")
    @patch("subekashi.management.commands.backup.DATABASES", MYSQL_DB_SETTINGS)
    @patch("subekashi.management.commands.backup.datetime")
    def test_mysql_logs_stderr_but_keeps_it_out_of_discord_notification(
        self, mock_datetime, mock_run, mock_upload, mock_delete, mock_send_discord, *_
    ):
        # コードレビュー指摘対応: mysqldumpのstderrにはホスト名・ユーザー名等の
        # 接続情報が含まれ得る。ERROR_DISCORD_URLは公開チャンネルのため、詳細は
        # サーバーの標準エラー出力（ログ）にのみ残し、Discord通知には一般化した
        # メッセージのみを送る（exit codeがエラー終了コードを返した場合の検証）
        mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 0, 0)
        mock_run.return_value = MagicMock(
            returncode=1, stderr=b"mysqldump: Access denied for user 'testuser'@'testhost'"
        )

        _, err = self._run()

        # サーバー側の標準エラー出力（ログ）には詳細情報を残す
        self.assertIn("Access denied for user", err)
        self.assertIn("Google Driveへのバックアップ中にエラーが発生しました", err)
        mock_upload.assert_not_called()
        mock_delete.assert_not_called()
        mock_send_discord.assert_called_once()
        # 公開チャンネル宛のDiscord通知には、ホスト名・ユーザー名等を含む
        # stderrの詳細を送らない
        self.assertNotIn("Access denied for user", mock_send_discord.call_args.args[1])
        self.assertNotIn("testuser", mock_send_discord.call_args.args[1])
        self.assertNotIn("testhost", mock_send_discord.call_args.args[1])

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.send_discord")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.subprocess.run")
    @patch("subekashi.management.commands.backup.DATABASES", MYSQL_DB_SETTINGS)
    @patch("subekashi.management.commands.backup.datetime")
    def test_mysql_reports_error_when_mysqldump_times_out(
        self, mock_datetime, mock_run, mock_upload, mock_delete, mock_send_discord, *_
    ):
        # コードレビュー指摘対応: DBサイズの増加やネットワーク要因でmysqldumpがハングし、
        # バックアップジョブが無期限にブロックされることを防ぐタイムアウトの回帰確認。
        # TimeoutExpired.__str__()は渡したcmdをそのまま文字列化するが、認証情報を
        # --defaults-extra-fileの一時ファイル経由に変更したことで、コマンド自体には
        # そもそもホスト名・ユーザー名・パスワードが含まれなくなった（#1086フォローアップ）
        mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 0, 0)

        def side_effect(command, **kwargs):
            raise subprocess.TimeoutExpired(cmd=command, timeout=Command.MYSQLDUMP_TIMEOUT_SECONDS)

        mock_run.side_effect = side_effect

        _, err = self._run()

        self.assertIn("Google Driveへのバックアップ中にエラーが発生しました", err)
        mock_upload.assert_not_called()
        mock_delete.assert_not_called()
        mock_send_discord.assert_called_once()
        # 公開チャンネル宛のDiscord通知には、ホスト名・ユーザー名・パスワードを
        # 含むコマンド全体を送らない（そもそもコマンドにこれらは含まれない）
        self.assertNotIn("testhost", mock_send_discord.call_args.args[1])
        self.assertNotIn("testuser", mock_send_discord.call_args.args[1])
        self.assertNotIn("testpass", mock_send_discord.call_args.args[1])


class StatsCommandTest(TestCase):
    """stats コマンドのテスト（月次統計(Stats)の集計・保存、#334）"""

    def _run(self, *extra_args):
        out = StringIO()
        err = StringIO()
        call_command("stats", *extra_args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    @patch("subekashi.management.commands.stats.now_local")
    def test_skips_when_not_first_of_month(self, mock_now_local):
        mock_now_local.return_value = timezone_aware(2026, 1, 15)
        Song.objects.create(title="曲", upload_time=timezone.make_aware(datetime(2025, 1, 1)))

        self._run()

        self.assertEqual(Stats.objects.count(), 0)

    @patch("subekashi.management.commands.stats.now_local")
    def test_no_songs_does_nothing(self, mock_now_local):
        mock_now_local.return_value = timezone_aware(2026, 1, 1)

        self._run()

        self.assertEqual(Stats.objects.count(), 0)

    @patch("subekashi.management.commands.stats.now_local")
    def test_no_songs_with_upload_time_does_nothing(self, mock_now_local):
        mock_now_local.return_value = timezone_aware(2026, 1, 1)
        Song.objects.create(title="曲", upload_time=None)

        self._run()

        self.assertEqual(Stats.objects.count(), 0)

    @patch("subekashi.management.commands.stats.now_local")
    def test_runs_on_first_of_month_and_creates_stats_for_each_month(self, mock_now_local):
        mock_now_local.return_value = timezone_aware(2026, 3, 1)
        Song.objects.create(title="1月の曲", upload_time=timezone_aware(2026, 1, 15), view=10, is_subeana=True)
        Song.objects.create(title="3月の曲", upload_time=timezone_aware(2026, 3, 15), view=20, is_subeana=False)

        self._run()

        months = sorted(set(Stats.objects.values_list("year", "month")))
        self.assertEqual(months, [(2026, 1), (2026, 2), (2026, 3)])
        # 月ごとにall/subeana/xxの3件ずつ作成される
        self.assertEqual(Stats.objects.filter(year=2026, month=1).count(), 3)

        jan_all = Stats.objects.get(year=2026, month=1, songrange="all")
        self.assertEqual(jan_all.song_count, 1)
        self.assertEqual(jan_all.total_view, 10)

        mar_all = Stats.objects.get(year=2026, month=3, songrange="all")
        self.assertEqual(mar_all.song_count, 2)
        self.assertEqual(mar_all.total_view, 30)

        # is_subeanaで正しく振り分けられていること
        mar_subeana = Stats.objects.get(year=2026, month=3, songrange="subeana")
        self.assertEqual(mar_subeana.song_count, 1)
        mar_xx = Stats.objects.get(year=2026, month=3, songrange="xx")
        self.assertEqual(mar_xx.song_count, 1)

    @patch("subekashi.management.commands.stats.now_local")
    def test_force_bypasses_day_guard(self, mock_now_local):
        mock_now_local.return_value = timezone_aware(2026, 3, 15)
        Song.objects.create(title="曲", upload_time=timezone_aware(2026, 3, 1))

        self._run("--force")

        self.assertEqual(Stats.objects.count(), 3)

    @patch("subekashi.management.commands.stats.now_local")
    def test_rerun_updates_existing_month_instead_of_duplicating(self, mock_now_local):
        mock_now_local.return_value = timezone_aware(2026, 1, 1)
        Song.objects.create(title="曲", upload_time=timezone_aware(2026, 1, 1), view=1)

        self._run()
        Song.objects.create(title="追加曲", upload_time=timezone_aware(2026, 1, 2), view=2)
        self._run("--force")

        self.assertEqual(Stats.objects.filter(year=2026, month=1).count(), 3)
        self.assertEqual(Stats.objects.get(year=2026, month=1, songrange="all").song_count, 2)

    @patch("subekashi.management.commands.stats.now_local")
    def test_now_local_uses_django_timezone_not_os_timezone(self, mock_now_local):
        # now_local()はtimezone.localtime(timezone.now())のラッパーであり、
        # サーバーOSのタイムゾーン設定に依存しないことの回帰確認（レビュー指摘対応）
        mock_now_local.return_value = timezone_aware(2026, 1, 1)
        Song.objects.create(title="曲", upload_time=timezone_aware(2026, 1, 1))

        self._run()

        mock_now_local.assert_called_once()
        self.assertEqual(Stats.objects.count(), 3)


class WordCommandTest(TestCase):
    """word コマンドのテスト"""

    def test_imports_candidates_from_json(self):
        data = json.dumps([
            {"word": "走る", "hinshi": "動詞", "candidates": ["駆ける", "疾走する"]},
        ])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        self.assertEqual(Word.objects.count(), 2)
        self.assertTrue(Word.objects.filter(word="走る", hinshi="動詞", candidate="駆ける").exists())
        self.assertTrue(Word.objects.filter(word="走る", hinshi="動詞", candidate="疾走する").exists())

    def test_imports_katsuyou_from_json(self):
        data = json.dumps([
            {"word": "走る", "hinshi": "動詞", "katsuyou": "基本形", "candidates": ["駆ける"]},
        ])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        word = Word.objects.get(word="走る", hinshi="動詞", candidate="駆ける")
        self.assertEqual(word.katsuyou, "基本形")

    def test_missing_katsuyou_defaults_to_empty_string(self):
        # 旧形式（katsuyou未対応）のword.jsonでも例外にならないようにする
        data = json.dumps([
            {"word": "走る", "hinshi": "動詞", "candidates": ["駆ける"]},
        ])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        word = Word.objects.get(word="走る", hinshi="動詞", candidate="駆ける")
        self.assertEqual(word.katsuyou, "")

    def test_multiple_entries_are_all_imported(self):
        data = json.dumps([
            {"word": "走る", "hinshi": "動詞", "candidates": ["駆ける"]},
            {"word": "犬", "hinshi": "名詞", "candidates": ["猫", "狼"]},
        ])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        self.assertEqual(Word.objects.count(), 3)

    def test_entry_without_word_or_hinshi_is_skipped(self):
        data = json.dumps([
            {"word": "", "hinshi": "動詞", "candidates": ["駆ける"]},
            {"word": "走る", "hinshi": "", "candidates": ["駆ける"]},
        ])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        self.assertEqual(Word.objects.count(), 0)

    def test_missing_file_does_not_raise(self):
        with patch("builtins.open", side_effect=OSError):
            call_command("word")

        self.assertEqual(Word.objects.count(), 0)

    def test_invalid_json_does_not_raise(self):
        with patch("builtins.open", mock_open(read_data="not a json")):
            call_command("word")

        self.assertEqual(Word.objects.count(), 0)

    def test_reimport_does_not_create_duplicates(self):
        data = json.dumps([{"word": "走る", "hinshi": "動詞", "candidates": ["駆ける"]}])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")
            call_command("word")

        self.assertEqual(Word.objects.count(), 1)

    def test_completion_message_reports_actual_new_count(self):
        # bulk_create(ignore_conflicts=True)は登録を試みた件数を返すため、
        # 実際にDBのcount()差分から新規作成数を算出していることを確認する
        data = json.dumps([{"word": "走る", "hinshi": "動詞", "candidates": ["駆ける"]}])
        out = StringIO()
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word", stdout=out)
            self.assertIn("新規Word候補数：1", out.getvalue())

            out2 = StringIO()
            call_command("word", stdout=out2)
            self.assertIn("新規Word候補数：0", out2.getvalue())

    def test_candidates_as_string_is_skipped(self):
        # candidatesが文字列だと1文字ずつイテレートされてしまうため、
        # listでないエントリは丸ごとスキップする
        data = json.dumps([{"word": "走る", "hinshi": "動詞", "candidates": "駆ける"}])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        self.assertEqual(Word.objects.count(), 0)

    def test_non_string_candidate_in_list_is_skipped(self):
        data = json.dumps([{"word": "走る", "hinshi": "動詞", "candidates": ["駆ける", 123, None]}])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        self.assertEqual(Word.objects.count(), 1)
        self.assertTrue(Word.objects.filter(candidate="駆ける").exists())

    def test_self_referential_candidate_is_skipped(self):
        # word == candidateの自己参照エントリはWordモデルのCheckConstraintで
        # 弾かれるが、bulk_create(ignore_conflicts=True)がCHECK制約違反を
        # スキップするかどうかはDBバックエンド依存のため、コマンド側で
        # 明示的にフィルタしていることを確認する（#940, PR #1068）
        data = json.dumps([{"word": "走る", "hinshi": "動詞", "candidates": ["走る", "駆ける"]}])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        self.assertEqual(Word.objects.count(), 1)
        self.assertTrue(Word.objects.filter(candidate="駆ける").exists())
        self.assertFalse(Word.objects.filter(word="走る", candidate="走る").exists())

    def test_top_level_object_does_not_raise(self):
        # トップレベルがlistでない（例: dict）場合、for文でdictのキーが
        # 渡ってentry.get()がAttributeErrorになるのを防ぐ
        data = json.dumps({"word": "走る", "hinshi": "動詞", "candidates": ["駆ける"]})
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        self.assertEqual(Word.objects.count(), 0)

    def test_non_dict_entry_in_list_is_skipped(self):
        data = json.dumps(["走る", {"word": "犬", "hinshi": "名詞", "candidates": ["猫"]}])
        with patch("builtins.open", mock_open(read_data=data)):
            call_command("word")

        self.assertEqual(Word.objects.count(), 1)
        self.assertTrue(Word.objects.filter(word="犬", candidate="猫").exists())


class AiCommandTest(TestCase):
    """ai コマンドのテスト（Song.lyricsからjanome Aiレコードをシードする、#1053）"""

    def test_creates_janome_ai_record_from_song_lyrics(self):
        # 「今日も一人で私は走る」(10文字) -> 「今日も一人で私は駆ける」(11文字)
        # 作成物は7文字以上20文字以下のみ対象とするため、判定に影響しない長さにしている
        Song.objects.create(title="曲1", lyrics="今日も一人で私は走る", is_joke=False, is_questionable=False)
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        call_command("ai")

        ai = Ai.objects.get(genetype="janome")
        self.assertEqual(ai.lyrics, "今日も一人で私は駆ける")
        self.assertEqual(ai.score, 0)

    def test_excludes_joke_songs(self):
        Song.objects.create(title="ネタ曲", lyrics="今日も一人で私は走る", is_joke=True, is_questionable=False)
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        call_command("ai")

        self.assertEqual(Ai.objects.filter(genetype="janome").count(), 0)

    def test_excludes_questionable_songs(self):
        Song.objects.create(title="界隈曲", lyrics="今日も一人で私は走る", is_joke=False, is_questionable=True)
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        call_command("ai")

        self.assertEqual(Ai.objects.filter(genetype="janome").count(), 0)

    def test_song_without_eligible_token_is_skipped_without_error(self):
        # Word候補が1件も無いため、置き換え可能なトークンが存在しない
        Song.objects.create(title="曲1", lyrics="ありがとう", is_joke=False, is_questionable=False)

        call_command("ai")

        self.assertEqual(Ai.objects.filter(genetype="janome").count(), 0)

    def test_excludes_result_shorter_than_seven_characters(self):
        # 「私は走る」(5文字) -> 「私は駆ける」(5文字)、7文字未満のため対象外
        Song.objects.create(title="曲1", lyrics="私は走る", is_joke=False, is_questionable=False)
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        call_command("ai")

        self.assertEqual(Ai.objects.filter(genetype="janome").count(), 0)

    def test_excludes_result_longer_than_twenty_characters(self):
        # 「今日もまた一人でとても寂しく悲しく私は走る」(21文字)
        # -> 「...駆ける」(22文字)、20文字超のため対象外
        Song.objects.create(
            title="曲1",
            lyrics="今日もまた一人でとても寂しく悲しく私は走る",
            is_joke=False,
            is_questionable=False,
        )
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        call_command("ai")

        self.assertEqual(Ai.objects.filter(genetype="janome").count(), 0)

    def test_count_option_limits_created_records(self):
        Song.objects.create(title="曲1", lyrics="今日も一人で私は走る", is_joke=False, is_questionable=False)
        Song.objects.create(title="曲2", lyrics="今日も一人で私は歩く", is_joke=False, is_questionable=False)
        Song.objects.create(title="曲3", lyrics="今日も一人で私は飛ぶ", is_joke=False, is_questionable=False)
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")
        Word.objects.create(word="歩く", hinshi="動詞", katsuyou="基本形", candidate="進む")
        Word.objects.create(word="飛ぶ", hinshi="動詞", katsuyou="基本形", candidate="跳ねる")

        call_command("ai", "--count", "1")

        self.assertEqual(Ai.objects.filter(genetype="janome").count(), 1)

    def test_rerun_does_not_create_duplicate_ai_record(self):
        # 対象が1曲・候補が1件のみのため、入れ替え結果は毎回同じになる
        Song.objects.create(title="曲1", lyrics="今日も一人で私は走る", is_joke=False, is_questionable=False)
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        call_command("ai")
        call_command("ai")

        self.assertEqual(Ai.objects.filter(genetype="janome").count(), 1)

    def test_completion_message_reports_created_count(self):
        Song.objects.create(title="曲1", lyrics="今日も一人で私は走る", is_joke=False, is_questionable=False)
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        out = StringIO()
        call_command("ai", stdout=out)

        self.assertIn("新規Aiレコード数：1件（対象1曲中）", out.getvalue())
