"""
lib/song_service.py のテスト

曲作成・更新・削除・Discord テキスト生成・short版/full版の判定のサービス関数を検証する。
"""
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from config.settings import ROOT_URL
from subekashi.models import Author, AuthorAlias, Song, SongLink, SongFields
from subekashi.lib.song_service import (
    check_reject_list,
    validate_song_url,
    create_song,
    set_song_authors_and_links,
    create_song_with_relations,
    get_imitate_songs,
    update_song,
    remove_song,
    build_delete_discord_text,
    build_new_song_discord_text,
    build_edit_song_discord_text,
    yes_no,
    category_label,
    get_short_base_title,
    get_full_base_title,
    get_short_and_full_songs,
    split_songs_by_category,
)


class YesNoTest(TestCase):
    """yes_no() のテスト"""

    def test_true_returns_hai(self):
        self.assertEqual(yes_no(True), "はい")

    def test_false_returns_iie(self):
        self.assertEqual(yes_no(False), "いいえ")


class CategoryLabelTest(TestCase):
    """category_label() のテスト（#423）"""

    def test_returns_label(self):
        self.assertEqual(category_label("arrange"), "アレンジ")

    def test_unknown_category_returns_value(self):
        self.assertEqual(category_label("unknown"), "unknown")


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

    def test_url_of_only_removed_song_allows_registration(self):
        # 削除した曲（#1239）だけに紐づくURLは、登録されていないURLとして扱う
        self.song.is_removed = True
        self.song.save()
        result = validate_song_url("https://youtu.be/existing1234")
        self.assertIsNone(result)

    def test_url_of_removed_and_existing_songs_returns_error_message(self):
        # allow_dup=FalseのURLが削除した曲と削除していない曲の両方に紐づく場合は、削除していない曲と重複する
        removed_song = Song.objects.create(title="削除した曲", is_removed=True)
        self.link.songs.add(removed_song)
        result = validate_song_url("https://youtu.be/existing1234")
        self.assertIsNotNone(result)

    def test_url_of_removed_and_existing_songs_when_editing_other_song_returns_error_message(self):
        removed_song = Song.objects.create(title="削除した曲", is_removed=True)
        other_song = Song.objects.create(title="編集している曲")
        self.link.songs.add(removed_song)
        result = validate_song_url("https://youtu.be/existing1234", exclude_song_id=other_song.id)
        self.assertIsNotNone(result)

    def test_url_of_removed_and_editing_song_returns_none(self):
        # 編集している曲自身のURLは、削除した曲にも紐づいていても登録できる
        removed_song = Song.objects.create(title="削除した曲", is_removed=True)
        self.link.songs.add(removed_song)
        result = validate_song_url("https://youtu.be/existing1234", exclude_song_id=self.song.id)
        self.assertIsNone(result)

    def test_url_at_max_length_returns_none(self):
        # #1085: MySQL移行時のData too long for column対策
        max_length = SongLink._meta.get_field("url").max_length
        url = "https://youtu.be/" + "a" * (max_length - len("https://youtu.be/"))
        self.assertEqual(len(url), max_length)
        result = validate_song_url(url)
        self.assertIsNone(result)

    def test_url_over_max_length_returns_error_message(self):
        max_length = SongLink._meta.get_field("url").max_length
        url = "https://youtu.be/" + "a" * (max_length - len("https://youtu.be/") + 1)
        result = validate_song_url(url)
        self.assertIsNotNone(result)
        self.assertIn(str(max_length), result)


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

    def test_is_questionable_is_set(self):
        fields = SongFields(title="界隈曲テスト", is_questionable=True)
        song = create_song(fields)
        self.assertTrue(song.is_questionable)

    def test_category_is_set(self):
        fields = SongFields(title="音MADテスト", category="otomad")
        song = create_song(fields)
        song.refresh_from_db()
        self.assertEqual(song.category, "otomad")

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

    def test_song_link_shared_with_removed_song_is_not_deleted(self):
        # 削除した曲（#1239）を復元したときのために、削除した曲に紐づくURLは残す
        removed_song = Song.objects.create(title="削除した曲", is_removed=True)
        self.link.songs.add(removed_song)
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        update_song(self.song, fields, [self.author1], [], [])
        self.assertEqual(list(removed_song.links.all()), [self.link])
        self.assertEqual(self.song.links.count(), 0)

    def test_imitate_to_removed_song_is_kept(self):
        # 編集画面に表示されない削除した曲（#1239）との模倣関係は、編集しても消さない
        removed_song = Song.objects.create(title="削除した模倣元", is_removed=True)
        self.song.imitates.add(removed_song)
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        update_song(self.song, fields, [self.author1], [], ["https://youtu.be/beforeupdate1"])
        self.assertTrue(Song.imitates.through.objects.filter(from_song=self.song, to_song=removed_song).exists())

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

    def test_is_questionable_is_updated(self):
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞", is_questionable=True)
        update_song(self.song, fields, [self.author1], [], ["https://youtu.be/beforeupdate1"])
        self.song.refresh_from_db()
        self.assertTrue(self.song.is_questionable)

    def test_category_is_updated(self):
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞", category="medley")
        update_song(self.song, fields, [self.author1], [], ["https://youtu.be/beforeupdate1"])
        self.song.refresh_from_db()
        self.assertEqual(self.song.category, "medley")

    def test_imitates_are_updated(self):
        target_song = Song.objects.create(title="新しい模倣元")
        fields = SongFields(title="更新前タイトル", lyrics="更新前歌詞")
        update_song(
            self.song, fields, [self.author1], [target_song],
            ["https://youtu.be/beforeupdate1"]
        )
        self.assertIn(target_song, self.song.imitates.all())


class RemoveSongTest(TestCase):
    """remove_song() のテスト（#1239）"""

    def setUp(self):
        self.author = Author.objects.create(name="削除テスト作者")
        self.target = Song.objects.create(title="削除テストの模倣元")
        self.song = Song.objects.create(title="削除する曲", lyrics="歌詞")
        self.song.authors.add(self.author)
        self.song.imitates.add(self.target)
        self.link = SongLink.objects.create(url="https://youtu.be/removesong01")
        self.link.songs.add(self.song)

    def test_song_is_removed(self):
        remove_song(self.song)
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)
        self.assertFalse(Song.objects.filter(pk=self.song.pk).exists())

    def test_relations_are_kept(self):
        # 復元できるよう、作者・URL・模倣元は残す
        remove_song(self.song)
        song = Song.all_objects.get(pk=self.song.pk)
        self.assertEqual(list(song.authors.all()), [self.author])
        self.assertEqual(list(song.links.all()), [self.link])
        self.assertEqual(list(song.imitates.all()), [self.target])
        self.link.refresh_from_db()
        self.assertFalse(self.link.is_removed)

    def test_other_fields_are_not_changed(self):
        post_time = Song.objects.get(pk=self.song.pk).post_time
        self.song.title = "保存されないタイトル"
        remove_song(self.song)
        song = Song.all_objects.get(pk=self.song.pk)
        self.assertEqual(song.title, "削除する曲")
        self.assertEqual(song.post_time, post_time)


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

    def test_text_starts_like_new_song_text(self):
        # 先頭は新規作成と同じく「〜されました」・曲のページのURL・空行の形式にする（#1239）
        text = build_delete_discord_text(self.song, "理由", "editor_ip")
        self.assertTrue(text.startswith(f"削除されました\n{ROOT_URL}/songs/{self.song.id}\n\nタイトル：削除申請曲\n"))


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

    def test_text_contains_questionable_label_when_true(self):
        fields = SongFields(title="新規テスト曲", is_questionable=True)
        _, text = build_new_song_discord_text(
            self.song.id, fields, [self.author], "", "editor_ip"
        )
        self.assertIn("界隈曲?", text)

    def test_text_contains_category_label(self):
        """#423: カテゴリは選択肢の表示名で通知・履歴に残す"""
        fields = SongFields(title="新規テスト曲", category="medley")
        changes, text = build_new_song_discord_text(
            self.song.id, fields, [self.author], "", "editor_ip"
        )
        self.assertIn(["カテゴリ", "メドレー"], changes)
        self.assertIn("**カテゴリ**：`メドレー`", text)


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

    def test_is_questionable_change_is_detected(self):
        fields = SongFields(title="編集前タイトル", lyrics="編集前歌詞", is_questionable=True)
        _, _, _, changed_labels = build_edit_song_discord_text(
            self.song.id, self.song, fields, [self.author], "", []
        )
        self.assertIn("界隈曲?", changed_labels)

    def test_category_change_is_detected(self):
        """#423: カテゴリの変更は選択肢の表示名で履歴に残す"""
        fields = SongFields(title="編集前タイトル", lyrics="編集前歌詞", category="cover")
        _, changes, _, changed_labels = build_edit_song_discord_text(
            self.song.id, self.song, fields, [self.author], "", []
        )
        self.assertIn("カテゴリ", changed_labels)
        self.assertIn(["カテゴリ", "曲", "カバー"], changes)

    def test_same_category_is_not_detected(self):
        fields = SongFields(title="編集前タイトル", lyrics="編集前歌詞")
        _, _, _, changed_labels = build_edit_song_discord_text(
            self.song.id, self.song, fields, [self.author], "", []
        )
        self.assertNotIn("カテゴリ", changed_labels)


class SplitSongsByCategoryTest(TestCase):
    """split_songs_by_category() のテスト（#423）"""

    def test_splits_songs_jokes_and_categorys(self):
        song = Song.objects.create(title="曲")
        joke = Song.objects.create(title="ネタ曲", is_joke=True)
        cover = Song.objects.create(title="カバー", category="cover")
        arrange1 = Song.objects.create(title="アレンジ1", category="arrange")
        arrange2 = Song.objects.create(title="アレンジ2", category="arrange")
        groups = split_songs_by_category(Song.objects.order_by("id"))
        self.assertEqual(groups["songs"], [song])
        self.assertEqual(groups["joke_songs"], [joke])
        # カテゴリごとのまとまりは、曲の並びではなくSONG_CATEGORIESの順（アレンジ・カバー）に並ぶ
        self.assertEqual(
            [(group["category"]["value"], group["songs"]) for group in groups["category_groups"]],
            [("arrange", [arrange1, arrange2]), ("cover", [cover])],
        )

    def test_joke_song_of_other_category_is_grouped_by_category(self):
        """曲以外のカテゴリの曲は、ネタ曲でもカテゴリの方にまとめる"""
        meme_joke = Song.objects.create(title="ネタ曲のネタ動画", category="meme", is_joke=True)
        groups = split_songs_by_category(Song.objects.all())
        self.assertEqual(groups["joke_songs"], [])
        self.assertEqual(groups["category_groups"][0]["category"]["value"], "meme")
        self.assertEqual(groups["category_groups"][0]["songs"], [meme_joke])

    def test_unknown_category_is_not_grouped(self):
        """選択肢にないカテゴリの曲は、カテゴリが曲の曲と同じく扱う"""
        unknown = Song.objects.create(title="移行前のネタ動画", category="joke")
        groups = split_songs_by_category(Song.objects.all())
        self.assertEqual(groups["songs"], [unknown])
        self.assertEqual(groups["category_groups"], [])

    def test_empty(self):
        self.assertEqual(split_songs_by_category(Song.objects.none()), {"songs": [], "joke_songs": [], "category_groups": []})


class GetShortBaseTitleTest(TestCase):
    """get_short_base_title() のテスト（#667）"""

    def test_square_bracket(self):
        self.assertEqual(get_short_base_title("鏡[short]"), "鏡")

    def test_space_before_bracket_is_removed(self):
        self.assertEqual(get_short_base_title("鏡 [short]"), "鏡")

    def test_capitalized_short(self):
        self.assertEqual(get_short_base_title("痕跡[Short]"), "痕跡")

    def test_upper_case_short(self):
        self.assertEqual(get_short_base_title("濛（SHORT）"), "濛")

    def test_bracket_with_other_words(self):
        self.assertEqual(get_short_base_title("00C(Short Ver.)"), "00C")
        self.assertEqual(get_short_base_title("夜雨[very short]"), "夜雨")
        self.assertEqual(get_short_base_title("無常【short】"), "無常")

    def test_text_after_short_is_removed(self):
        self.assertEqual(get_short_base_title("微細構造[short] (旧:▇)"), "微細構造")
        self.assertEqual(get_short_base_title("#40 [short] [Demo]"), "#40")

    def test_without_bracket(self):
        self.assertEqual(get_short_base_title("NNN - short ver."), "NNN")
        self.assertEqual(get_short_base_title("死んだらしいshort"), "死んだらしい")
        self.assertEqual(get_short_base_title("炭酸 short. (off vocal)"), "炭酸")

    def test_first_short_is_used(self):
        self.assertEqual(get_short_base_title("目 short.(旧:👁 short.)"), "目")

    def test_title_of_only_short_returns_empty_string(self):
        self.assertEqual(get_short_base_title("short"), "")
        self.assertEqual(get_short_base_title("[short]"), "")

    def test_non_short_title_returns_none(self):
        self.assertIsNone(get_short_base_title("鏡"))
        self.assertIsNone(get_short_base_title("relix[full]"))


class GetFullBaseTitleTest(TestCase):
    """get_full_base_title() のテスト（#667）"""

    def test_bracket_full_is_removed(self):
        self.assertEqual(get_full_base_title("relix[full]"), "relix")
        self.assertEqual(get_full_base_title("ʓ [Full]"), "ʓ")
        self.assertEqual(get_full_base_title("チェーン（Full）"), "チェーン")
        self.assertEqual(get_full_base_title("///[FULL]"), "///")
        self.assertEqual(get_full_base_title("曲 (Full ver.)"), "曲")

    def test_full_word_at_end_is_removed(self):
        self.assertEqual(get_full_base_title("死んだらしいfull"), "死んだらしい")
        self.assertEqual(get_full_base_title("淫夢グミ　FULLスギ"), "淫夢グミ")

    def test_full_in_english_word_is_kept(self):
        self.assertEqual(get_full_base_title("Beautiful"), "Beautiful")

    def test_full_not_at_end_is_kept(self):
        self.assertEqual(get_full_base_title("Full Moon"), "Full Moon")

    def test_title_without_full_is_unchanged(self):
        self.assertEqual(get_full_base_title(" 鏡 "), "鏡")


class GetShortAndFullSongsTest(TestCase):
    """get_short_and_full_songs() のテスト（#667）"""

    def setUp(self):
        self.author = Author.objects.create(name="作者A")
        self.other_author = Author.objects.create(name="作者B")

    def create_song(self, title, author=None):
        song = Song.objects.create(title=title)
        song.authors.set([author or self.author])
        return song

    def test_short_song_returns_full_song(self):
        full = self.create_song("鏡")
        short = self.create_song("鏡[short]")
        self.assertEqual(get_short_and_full_songs(short), ([full], []))

    def test_full_song_returns_short_song(self):
        full = self.create_song("鏡")
        short = self.create_song("鏡[short]")
        self.assertEqual(get_short_and_full_songs(full), ([], [short]))

    def test_all_full_candidates_are_returned(self):
        full1 = self.create_song("≡")
        full2 = self.create_song("≡")
        short = self.create_song("≡[short]")
        self.assertEqual(get_short_and_full_songs(short), ([full1, full2], []))

    def test_all_short_candidates_are_returned(self):
        full = self.create_song("鏡")
        short1 = self.create_song("鏡[short]")
        short2 = self.create_song("鏡(very short)")
        self.assertEqual(get_short_and_full_songs(full), ([], [short1, short2]))

    def test_different_author_is_not_linked(self):
        self.create_song("鏡", self.other_author)
        short = self.create_song("鏡[short]")
        self.assertEqual(get_short_and_full_songs(short), ([], []))

    def test_author_linked_by_alias_is_linked(self):
        AuthorAlias.objects.create(author=self.author, name="作者B", alias_type="another")
        full = self.create_song("鏡", self.other_author)
        short = self.create_song("鏡[short]")
        self.assertEqual(get_short_and_full_songs(short), ([full], []))
        self.assertEqual(get_short_and_full_songs(full), ([], [short]))

    def test_author_linked_by_group_alias_is_not_linked(self):
        AuthorAlias.objects.create(author=self.author, name="作者B", alias_type="group")
        self.create_song("鏡", self.other_author)
        short = self.create_song("鏡[short]")
        self.assertEqual(get_short_and_full_songs(short), ([], []))

    def test_one_of_multiple_authors_matches(self):
        full = self.create_song("鏡")
        short = self.create_song("鏡[short]")
        short.authors.add(self.other_author)
        self.assertEqual(get_short_and_full_songs(short), ([full], []))

    def test_full_song_with_full_tag_is_linked(self):
        full = self.create_song("relix[full]")
        short = self.create_song("relix[short]")
        self.assertEqual(get_short_and_full_songs(short), ([full], []))
        self.assertEqual(get_short_and_full_songs(full), ([], [short]))

    def test_ascii_case_is_ignored(self):
        full = self.create_song("00c")
        short = self.create_song("00C(Short Ver.)")
        self.assertEqual(get_short_and_full_songs(short), ([full], []))
        self.assertEqual(get_short_and_full_songs(full), ([], [short]))

    def test_non_ascii_case_is_not_ignored(self):
        self.create_song("λ")
        full = self.create_song("Λ")
        short = self.create_song("Λ [short]")
        self.assertEqual(get_short_and_full_songs(short), ([full], []))

    def test_full_width_and_half_width_are_distinguished(self):
        self.create_song("-")
        short = self.create_song("﹣[short]")
        self.assertEqual(get_short_and_full_songs(short), ([], []))

    def test_symbol_count_must_match(self):
        self.create_song("⬚")
        short = self.create_song("⬚⬚[short]")
        self.assertEqual(get_short_and_full_songs(short), ([], []))

    def test_short_songs_are_not_linked_to_each_other(self):
        self.create_song("鏡[very short]")
        short = self.create_song("鏡[short]")
        self.assertEqual(get_short_and_full_songs(short), ([], []))

    def test_title_of_only_short_is_not_linked(self):
        self.create_song("")
        short = self.create_song("short")
        self.assertEqual(get_short_and_full_songs(short), ([], []))

    def test_song_without_related_songs_returns_empty_lists(self):
        song = self.create_song("鏡")
        self.assertEqual(get_short_and_full_songs(song), ([], []))

    def test_song_without_authors_returns_empty_lists(self):
        Song.objects.create(title="鏡")
        short = Song.objects.create(title="鏡[short]")
        self.assertEqual(get_short_and_full_songs(short), ([], []))
