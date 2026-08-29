"""
管理コマンドのテスト

delete: is_removedをfalseのままにする--keep-linksオプションを検証する。
youtube: DBロック対策で処理方式を変更した後の挙動（id指定・全件処理・リンク無しスキップ・動画削除時の扱い）を検証する。
detect_primary_name_duplicates: 一番有名な名義の重複候補検出レポート（#1008）を検証する。
backup: バックアップ先をサーバーストレージからGoogle Driveに変更した挙動（#1050）を検証する。
word: word.jsonから模倣単語候補をWordに一括登録する処理（#1053）を検証する。
ai: Song.lyricsの単語をランダムに入れ替えてgenetype="janome"のAiレコードをシードする処理を検証する。
"""
import json
from datetime import datetime
from io import StringIO
from unittest.mock import mock_open, patch

from django.core.management import call_command
from django.test import TestCase

from subekashi.models import Ai, Author, AuthorAlias, Song, SongLink, Word


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

    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    @patch("subekashi.management.commands.backup.GOOGLE_DRIVE_CLIENT_ID", "client-id")
    @patch("subekashi.management.commands.backup.send_discord")
    @patch("subekashi.management.commands.backup.delete_old_backups")
    @patch("subekashi.management.commands.backup.upload_backup")
    @patch("subekashi.management.commands.backup.shutil.copy2")
    @patch("subekashi.management.commands.backup.datetime")
    def test_reports_cleanup_error_separately_when_upload_succeeds_but_pruning_fails(
        self, mock_datetime, mock_copy2, mock_upload, mock_delete, mock_send_discord, *_
    ):
        # アップロード自体は成功しているので、削除失敗と混同しないメッセージになること
        mock_datetime.now.return_value = datetime(2026, 1, 1, 18, 0, 0)
        mock_delete.side_effect = Exception("削除失敗")

        _, err = self._run()

        mock_upload.assert_called_once()
        self.assertIn("Google Driveの古いバックアップの削除中にエラーが発生しました", err)
        self.assertNotIn("Google Driveへのバックアップ中にエラーが発生しました", err)
        mock_send_discord.assert_called_once()


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
