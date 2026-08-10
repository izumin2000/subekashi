"""
管理コマンドのテスト

delete: is_removedをfalseのままにする--keep-linksオプションを検証する。
youtube: DBロック対策で処理方式を変更した後の挙動（id指定・全件処理・リンク無しスキップ・動画削除時の扱い）を検証する。
"""
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from subekashi.models import Song, SongLink


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
