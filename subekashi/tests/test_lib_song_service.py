"""
lib/song_service.py のテスト

曲作成・更新・削除申請・Discord テキスト生成のサービス関数を検証する。
"""
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from subekashi.models import Author, Song, SongLink, SongFields
from subekashi.lib.song_service import (
    check_reject_list,
    validate_song_url,
    create_song,
    set_song_authors_and_links,
    create_song_with_relations,
    get_imitate_songs,
    update_song,
    build_delete_discord_text,
    build_new_song_discord_text,
    build_edit_song_discord_text,
    yes_no,
)


class YesNoTest(TestCase):
    """yes_no() のテスト"""

    def test_true_returns_hai(self):
        self.assertEqual(yes_no(True), "はい")

    def test_false_returns_iie(self):
        self.assertEqual(yes_no(False), "いいえ")


class CheckRejectListTest(TestCase):
    """check_reject_list() のテスト"""

    def setUp(self):
        self.safe_author = Author.objects.create(name="安全な作者")
        self.ng_author = Author.objects.create(name="NGアーティスト")

    def test_safe_author_returns_none(self):
        result = check_reject_list([self.safe_author])
        self.assertIsNone(result)

    def test_empty_authors_returns_none(self):
        result = check_reject_list([])
        self.assertIsNone(result)

    def test_ng_author_returns_error_message(self):
        # check_reject_list は関数内で動的に import するため、
        # sys.modules にモックモジュールを差し込んで REJECT_LIST を制御する
        from unittest.mock import MagicMock
        mock_reject_module = MagicMock()
        mock_reject_module.REJECT_LIST = ["NGアーティスト"]
        with patch.dict("sys.modules", {"subekashi.constants.dynamic.reject": mock_reject_module}):
            result = check_reject_list([self.ng_author])
        self.assertIsNotNone(result)
        self.assertIn("NGアーティスト", result)

    def test_import_error_falls_back_to_empty_list(self):
        # sys.modules[key] = None は Python 仕様として ImportError を発生させる
        # (importlib ドキュメント: "If None, raises an ImportError")
        # これにより reject モジュールが存在しない環境をシミュレートできる
        with patch.dict("sys.modules", {"subekashi.constants.dynamic.reject": None}):
            result = check_reject_list([self.safe_author])
        self.assertIsNone(result)


class ValidateSongUrlTest(TestCase):
    """validate_song_url() のテスト"""

    def setUp(self):
        self.song = Song.objects.create(title="既存曲")
        self.link = SongLink.objects.create(url="https://youtu.be/existing1234")
        self.link.songs.add(self.song)

    def test_duplicate_url_returns_error_message(self):
        result = validate_song_url("https://youtu.be/existing1234")
        self.assertIsNotNone(result)
        self.assertIn("既に登録されています", result)

    def test_new_url_returns_none(self):
        result = validate_song_url("https://youtu.be/brandnew1234")
        self.assertIsNone(result)

    def test_exclude_song_id_allows_same_url(self):
        result = validate_song_url("https://youtu.be/existing1234", exclude_song_id=self.song.id)
        self.assertIsNone(result)

    def test_allow_dup_true_allows_duplicate(self):
        self.link.allow_dup = True
        self.link.save()
        result = validate_song_url("https://youtu.be/existing1234")
        self.assertIsNone(result)

    def test_url_with_no_songs_allows_registration(self):
        SongLink.objects.create(url="https://youtu.be/nosongslink1")
        result = validate_song_url("https://youtu.be/nosongslink1")
        self.assertIsNone(result)


class CreateSongTest(TestCase):
    """create_song() のテスト"""

    def test_song_is_created_in_db(self):
        fields = SongFields(title="新規作成曲")
        song = create_song(fields)
        self.assertIsNotNone(song.pk)
        self.assertEqual(Song.objects.count(), 1)

    def test_song_title_is_set(self):
        fields = SongFields(title="タイトル確認曲")
        song = create_song(fields)
        self.assertEqual(song.title, "タイトル確認曲")

    def test_song_flags_match_fields(self):
        fields = SongFields(
            title="フラグテスト曲",
            is_original=True,
            is_joke=False,
            is_inst=True,
            is_subeana=False,
            is_deleted=False,
        )
        song = create_song(fields)
        self.assertTrue(song.is_original)
        self.assertFalse(song.is_joke)
        self.assertTrue(song.is_inst)
        self.assertFalse(song.is_subeana)

    def test_post_time_is_set_automatically(self):
        before = timezone.now()
        fields = SongFields(title="タイムスタンプテスト曲")
        song = create_song(fields)
        after = timezone.now()
        self.assertGreaterEqual(song.post_time, before)
        self.assertLessEqual(song.post_time, after)


class SetSongAuthorsAndLinksTest(TestCase):
    """set_song_authors_and_links() のテスト"""

    def setUp(self):
        self.song = Song.objects.create(title="リンク設定テスト曲")
        self.author = Author.objects.create(name="リンクテスト作者")

    def test_authors_are_set(self):
        set_song_authors_and_links(self.song, [self.author], "")
        self.assertIn(self.author, self.song.authors.all())

    def test_song_link_is_created(self):
        set_song_authors_and_links(self.song, [], "https://youtu.be/setlinktest1")
        self.assertEqual(SongLink.objects.count(), 1)
        self.assertIn(self.song, SongLink.objects.first().songs.all())

    def test_multiple_urls_create_multiple_links(self):
        set_song_authors_and_links(
            self.song, [], "https://youtu.be/setlink00001,https://youtu.be/setlink00002"
        )
        self.assertEqual(SongLink.objects.count(), 2)

    def test_empty_url_creates_no_links(self):
        set_song_authors_and_links(self.song, [], "")
        self.assertEqual(SongLink.objects.count(), 0)


class CreateSongWithRelationsTest(TestCase):
    """create_song_with_relations() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="リレーション作成テスト作者")

    def test_song_and_relations_are_created(self):
        fields = SongFields(title="リレーション作成テスト曲")
        song = create_song_with_relations(fields, [self.author], "https://youtu.be/relation00001")
        self.assertIsNotNone(song.pk)
        self.assertIn(self.author, song.authors.all())
        self.assertEqual(SongLink.objects.count(), 1)


class GetImitateSongsTest(TestCase):
    """get_imitate_songs() のテスト"""

    def setUp(self):
        self.song1 = Song.objects.create(title="模倣元1")
        self.song2 = Song.objects.create(title="模倣元2")

    def test_valid_ids_return_songs(self):
        result = get_imitate_songs(f"{self.song1.id},{self.song2.id}", self_id=0)
        self.assertIn(self.song1, result)
        self.assertIn(self.song2, result)

    def test_self_id_is_excluded(self):
        result = get_imitate_songs(f"{self.song1.id},{self.song2.id}", self_id=self.song1.id)
        self.assertNotIn(self.song1, result)
        self.assertIn(self.song2, result)

    def test_non_numeric_values_are_ignored(self):
        result = get_imitate_songs(f"{self.song1.id},abc,xyz", self_id=0)
        self.assertIn(self.song1, result)
        self.assertEqual(len(result), 1)

    def test_empty_string_returns_empty_list(self):
        result = get_imitate_songs("", self_id=0)
        self.assertEqual(result, [])

    def test_whitespace_around_ids_is_handled(self):
        result = get_imitate_songs(f" {self.song1.id} , {self.song2.id} ", self_id=0)
        self.assertIn(self.song1, result)
        self.assertIn(self.song2, result)

    def test_nonexistent_id_is_ignored(self):
        result = get_imitate_songs("99999", self_id=0)
        self.assertEqual(result, [])


class UpdateSongTest(TestCase):
    """update_song() のテスト"""

    def setUp(self):
        self.author1 = Author.objects.create(name="更新テスト作者1")
        self.author2 = Author.objects.create(name="更新テスト作者2")
        self.song = Song.objects.create(title="更新前タイトル", lyrics="更新前歌詞")
        self.song.authors.add(self.author1)
        self.link = SongLink.objects.create(url="https://youtu.be/beforeupdate1")
        self.link.songs.add(self.song)

    def test_title_is_updated(self):
        fields = SongFields(title="更新後タイトル", lyrics="更新前歌詞")
        update_song(self.song, fields, [self.author1], [], ["https://youtu.be/beforeupdate1"])
        self.song.refresh_from_db()
        self.assertEqual(self.song.title, "更新後タイトル")

    def test_authors_are_updated(self):
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        update_song(self.song, fields, [self.author2], [], ["https://youtu.be/beforeupdate1"])
        self.song.refresh_from_db()
        self.assertNotIn(self.author1, self.song.authors.all())
        self.assertIn(self.author2, self.song.authors.all())

    def test_removed_url_is_deleted_from_link(self):
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        update_song(self.song, fields, [self.author1], [], [])
        self.song.refresh_from_db()
        self.assertEqual(self.song.links.count(), 0)

    def test_orphaned_song_link_is_deleted(self):
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        update_song(self.song, fields, [self.author1], [], [])
        self.assertEqual(SongLink.objects.filter(url="https://youtu.be/beforeupdate1").count(), 0)

    def test_shared_song_link_is_not_deleted(self):
        other_song = Song.objects.create(title="他の曲")
        self.link.songs.add(other_song)
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        update_song(self.song, fields, [self.author1], [], [])
        # other_songがまだリンクを使っているため SongLink は残るべき
        self.assertEqual(SongLink.objects.filter(url="https://youtu.be/beforeupdate1").count(), 1)

    def test_new_url_is_added(self):
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        new_url = "https://youtu.be/afterupdate12"
        update_song(
            self.song, fields, [self.author1], [],
            ["https://youtu.be/beforeupdate1", new_url]
        )
        self.song.refresh_from_db()
        urls = list(self.song.links.values_list("url", flat=True))
        self.assertIn(new_url, urls)

    def test_imitates_are_updated(self):
        target_song = Song.objects.create(title="新しい模倣元")
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        update_song(
            self.song, fields, [self.author1], [target_song],
            ["https://youtu.be/beforeupdate1"]
        )
        self.assertIn(target_song, self.song.imitates.all())


class BuildDeleteDiscordTextTest(TestCase):
    """build_delete_discord_text() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="削除テスト作者")
        self.song = Song.objects.create(title="削除申請曲")
        self.song.authors.add(self.author)

    def test_text_contains_song_id(self):
        text = build_delete_discord_text(self.song, "削除理由", "editor_ip")
        self.assertIn(str(self.song.id), text)

    def test_text_contains_title(self):
        text = build_delete_discord_text(self.song, "削除理由", "editor_ip")
        self.assertIn("削除申請曲", text)

    def test_text_contains_reason(self):
        text = build_delete_discord_text(self.song, "テスト削除理由", "editor_ip")
        self.assertIn("テスト削除理由", text)

    def test_text_contains_author(self):
        text = build_delete_discord_text(self.song, "理由", "editor_ip")
        self.assertIn("削除テスト作者", text)


class BuildNewSongDiscordTextTest(TestCase):
    """build_new_song_discord_text() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="新規テスト作者")
        self.song = Song.objects.create(title="新規テスト曲")
        self.fields = SongFields(title="新規テスト曲", is_original=True)

    def test_returns_changes_list_and_text(self):
        changes, text = build_new_song_discord_text(
            self.song.id, self.fields, [self.author], "https://youtu.be/newtest12345", "editor_ip"
        )
        self.assertIsInstance(changes, list)
        self.assertIsInstance(text, str)

    def test_changes_has_header_row(self):
        changes, _ = build_new_song_discord_text(
            self.song.id, self.fields, [self.author], "", "editor_ip"
        )
        self.assertEqual(changes[0], ["種類", "内容"])

    def test_text_contains_title(self):
        _, text = build_new_song_discord_text(
            self.song.id, self.fields, [self.author], "", "editor_ip"
        )
        self.assertIn("新規テスト曲", text)

    def test_text_contains_author_name(self):
        _, text = build_new_song_discord_text(
            self.song.id, self.fields, [self.author], "", "editor_ip"
        )
        self.assertIn("新規テスト作者", text)


class BuildEditSongDiscordTextTest(TestCase):
    """build_edit_song_discord_text() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="編集テスト作者")
        self.song = Song.objects.create(title="編集前タイトル", lyrics="編集前歌詞")
        self.song.authors.add(self.author)

    def test_title_change_is_detected(self):
        fields = SongFields(title="編集後タイトル", lyrics="編集前歌詞")
        edit_title, changes, text, changed_labels = build_edit_song_discord_text(
            self.song.id, self.song, fields, [self.author], "", []
        )
        self.assertIn("タイトル", changed_labels)

    def test_no_change_returns_empty_labels(self):
        fields = SongFields(title="編集前タイトル", lyrics="編集前歌詞")
        _, _, _, changed_labels = build_edit_song_discord_text(
            self.song.id, self.song, fields, [self.author], "", []
        )
        self.assertNotIn("タイトル", changed_labels)

    def test_edit_title_contains_changed_label(self):
        fields = SongFields(title="編集後タイトル", lyrics="編集前歌詞")
        edit_title, _, _, _ = build_edit_song_discord_text(
            self.song.id, self.song, fields, [self.author], "", []
        )
        self.assertIn("タイトル", edit_title)

    def test_changes_list_header_has_before_after(self):
        fields = SongFields(title="編集後タイトル", lyrics="編集前歌詞")
        _, changes, _, _ = build_edit_song_discord_text(
            self.song.id, self.song, fields, [self.author], "", []
        )
        self.assertEqual(changes[0], ["種類", "編集前", "編集後"])

    def test_multiple_field_changes(self):
        fields = SongFields(title="編集後タイトル", lyrics="編集後歌詞", is_original=True)
        _, _, _, changed_labels = build_edit_song_discord_text(
            self.song.id, self.song, fields, [self.author], "", []
        )
        self.assertIn("タイトル", changed_labels)
        self.assertIn("歌詞", changed_labels)
        self.assertIn("オリジナル", changed_labels)
