"""
管理コマンドのテスト

delete: is_removedをfalseのままにする--keep-linksオプションを検証する。
youtube: DBロック対策で処理方式を変更した後の挙動（id指定・全件処理・リンク無しスキップ・動画削除時の扱い）を検証する。
detect_primary_name_duplicates: 一番有名な名義の重複候補検出レポート（#1008）を検証する。
backup: バックアップ先をサーバーストレージからGoogle Driveに変更した挙動（#1050）を検証する。
"""
from datetime import datetime
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from subekashi.models import Author, AuthorAlias, Song, SongLink


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


class DetectPrimaryNameDuplicatesCommandTest(TestCase):
    """detect_primary_name_duplicates コマンド（一番有名な名義の重複候補検出、#1008）のテスト"""

    def _run(self):
        out = StringIO()
        call_command("detect_primary_name_duplicates", stdout=out)
        return out.getvalue()

    def test_no_past_aliases_reports_no_duplicates(self):
        Author.objects.create(name="通常作者")
        output = self._run()
        self.assertIn("重複候補は見つかりませんでした", output)

    def test_past_alias_without_conflicting_author_reports_no_duplicates(self):
        author = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=author, alias_type="past")
        output = self._run()
        self.assertIn("重複候補は見つかりませんでした", output)

    def test_non_past_alias_conflict_is_not_reported(self):
        # another等、past以外の種別は重複候補として扱わない
        author = Author.objects.create(name="現在の名義2")
        Author.objects.create(name="別名義候補")
        AuthorAlias.objects.create(name="別名義候補", author=author, alias_type="another")
        output = self._run()
        self.assertIn("重複候補は見つかりませんでした", output)

    def test_conflicting_past_alias_is_reported(self):
        primary = Author.objects.create(name="現在の名義3")
        duplicate = Author.objects.create(name="以前の名義3")
        AuthorAlias.objects.create(name="以前の名義3", author=primary, alias_type="past")

        output = self._run()

        self.assertIn("重複候補", output)
        self.assertIn(f"id={primary.id}", output)
        self.assertIn(f"id={duplicate.id}", output)
        self.assertIn("以前の名義3", output)

    def test_duplicate_song_title_is_reported_as_error(self):
        primary = Author.objects.create(name="現在の名義4")
        duplicate = Author.objects.create(name="以前の名義4")
        AuthorAlias.objects.create(name="以前の名義4", author=primary, alias_type="past")

        primary_song = Song.objects.create(title="同じタイトルの曲")
        primary_song.authors.add(primary)
        duplicate_song = Song.objects.create(title="同じタイトルの曲")
        duplicate_song.authors.add(duplicate)

        output = self._run()

        self.assertIn("曲タイトル重複", output)
        self.assertIn("同じタイトルの曲", output)
        self.assertIn(f"id={primary_song.id}", output)
        self.assertIn(f"id={duplicate_song.id}", output)

    def test_non_duplicate_song_is_reported_without_error(self):
        primary = Author.objects.create(name="現在の名義5")
        duplicate = Author.objects.create(name="以前の名義5")
        AuthorAlias.objects.create(name="以前の名義5", author=primary, alias_type="past")

        duplicate_song = Song.objects.create(title="重複しない曲")
        duplicate_song.authors.add(duplicate)

        output = self._run()

        self.assertIn("統合対象曲（重複なし）", output)
        self.assertIn("重複しない曲", output)
        self.assertNotIn("曲タイトル重複", output)

    def test_does_not_modify_any_data(self):
        # レポート専用であり、Author・AuthorAlias・Songのいずれも変更・削除しない
        primary = Author.objects.create(name="現在の名義6")
        duplicate = Author.objects.create(name="以前の名義6")
        AuthorAlias.objects.create(name="以前の名義6", author=primary, alias_type="past")
        song = Song.objects.create(title="変更されない曲")
        song.authors.add(duplicate)

        self._run()

        self.assertTrue(Author.objects.filter(pk=primary.pk).exists())
        self.assertTrue(Author.objects.filter(pk=duplicate.pk).exists())
        self.assertTrue(AuthorAlias.objects.filter(name="以前の名義6").exists())
        self.assertTrue(Song.objects.filter(pk=song.pk, authors=duplicate).exists())


class BackupCommandTest(TestCase):
    """backup コマンドのテスト（バックアップ先をGoogle Driveに変更、#1050）"""

    def _run(self):
        out = StringIO()
        err = StringIO()
        call_command("backup", stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

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
    @patch("subekashi.management.commands.backup.shutil.copy2")
    @patch("subekashi.management.commands.backup.datetime")
    def test_uploads_to_drive_and_prunes_old_backups_on_scheduled_hour(
        self, mock_datetime, mock_copy2, mock_upload, mock_delete, *_
    ):
        mock_datetime.now.return_value = datetime(2026, 1, 1, 6, 0, 0)

        self._run()

        mock_copy2.assert_called_once()
        mock_upload.assert_called_once()
        self.assertEqual(mock_upload.call_args.args[1], "2026-01-01-06.sqlite3")
        mock_delete.assert_called_once_with(50)

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.send_discord")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.shutil.copy2")
    @patch("subekashi.management.commands.backup.datetime")
    def test_reports_error_and_skips_pruning_when_upload_fails(
        self, mock_datetime, mock_copy2, mock_upload, mock_delete, mock_send_discord, *_
    ):
        mock_datetime.now.return_value = datetime(2026, 1, 1, 12, 0, 0)
        mock_upload.side_effect = Exception("アップロード失敗")

        _, err = self._run()

        self.assertIn("Google Driveへのバックアップ中にエラーが発生しました", err)
        mock_delete.assert_not_called()
        mock_send_discord.assert_called_once()
