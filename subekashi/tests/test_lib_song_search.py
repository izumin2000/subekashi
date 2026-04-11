"""
lib/song_search.py のテスト

song_search() のページネーション・統計情報・バリデーションエラー処理を検証する。
"""
import math
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from subekashi.models import Author, Song, SongLink
from subekashi.lib.song_search import song_search, DEFAULT_SIZE


def _create_songs(count, prefix="テスト曲"):
    return [Song.objects.create(title=f"{prefix}{i}") for i in range(count)]


class SongSearchStatisticsTest(TestCase):
    """song_search() の統計情報テスト"""

    def setUp(self):
        _create_songs(10)

    def test_statistics_contains_required_keys(self):
        _, stats = song_search({})
        self.assertIn("count", stats)
        self.assertIn("page", stats)
        self.assertIn("size", stats)
        self.assertIn("max_page", stats)

    def test_count_matches_total_songs(self):
        _, stats = song_search({})
        self.assertEqual(stats["count"], 10)

    def test_default_page_is_1(self):
        _, stats = song_search({})
        self.assertEqual(stats["page"], 1)

    def test_default_size_is_DEFAULT_SIZE(self):
        _, stats = song_search({})
        self.assertEqual(stats["size"], DEFAULT_SIZE)

    def test_max_page_calculated_correctly(self):
        _, stats = song_search({"size": "3"})
        expected = math.ceil(10 / 3)
        self.assertEqual(stats["max_page"], expected)

    def test_max_page_is_0_when_no_songs(self):
        # math.ceil(0 / size) = 0 が正しい動作
        Song.objects.all().delete()
        _, stats = song_search({})
        self.assertEqual(stats["max_page"], 0)


class SongSearchPaginationTest(TestCase):
    """song_search() のページネーションテスト"""

    def setUp(self):
        _create_songs(25)

    def test_page1_size10_returns_10_songs(self):
        qs, _ = song_search({"page": "1", "size": "10"})
        self.assertEqual(len(list(qs)), 10)

    def test_page3_size10_returns_5_songs(self):
        qs, _ = song_search({"page": "3", "size": "10"})
        self.assertEqual(len(list(qs)), 5)

    def test_page_exceeds_max_returns_empty(self):
        qs, _ = song_search({"page": "99", "size": "10"})
        self.assertEqual(len(list(qs)), 0)

    def test_invalid_page_defaults_to_page1(self):
        _, stats = song_search({"page": "abc"})
        self.assertEqual(stats["page"], 1)

    def test_invalid_size_defaults_to_DEFAULT_SIZE(self):
        _, stats = song_search({"size": "xyz"})
        self.assertEqual(stats["size"], DEFAULT_SIZE)

    def test_size_zero_defaults_to_DEFAULT_SIZE(self):
        _, stats = song_search({"size": "0"})
        self.assertEqual(stats["size"], DEFAULT_SIZE)

    def test_negative_size_defaults_to_DEFAULT_SIZE(self):
        _, stats = song_search({"size": "-1"})
        self.assertEqual(stats["size"], DEFAULT_SIZE)

    def test_negative_page_defaults_to_page1(self):
        _, stats = song_search({"page": "-5"})
        self.assertEqual(stats["page"], 1)

    def test_list_value_for_page_is_handled(self):
        _, stats = song_search({"page": ["2", "3"]})
        self.assertIsInstance(stats["page"], int)
        # clean_query_params はリストの先頭要素 "2" を使用する
        self.assertEqual(stats["page"], 2)


class SongSearchFilterTest(TestCase):
    """song_search() のフィルタリングテスト"""

    def setUp(self):
        self.target = Song.objects.create(title="検索対象曲タイトル")
        self.other = Song.objects.create(title="関係ない曲")

    def test_keyword_filter_narrows_results(self):
        qs, stats = song_search({"keyword": "検索対象"})
        titles = [s.title for s in qs]
        self.assertIn("検索対象曲タイトル", titles)
        self.assertNotIn("関係ない曲", titles)
        self.assertEqual(stats["count"], 1)

    def test_title_filter_narrows_results(self):
        qs, stats = song_search({"title": "検索対象"})
        self.assertEqual(stats["count"], 1)

    def test_is_deleted_filter(self):
        deleted = Song.objects.create(title="削除済み曲", is_deleted=True)
        _, stats = song_search({"is_deleted": "true"})
        self.assertEqual(stats["count"], 1)


class SongSearchSortWithFilterTest(TestCase):
    """sort と他フィルターを組み合わせた場合のソート順テスト（distinct適用後も維持されることを確認）"""

    def setUp(self):
        self.song_a = Song.objects.create(title="Aaa共通ワード")
        self.song_b = Song.objects.create(title="Bbb共通ワード")
        self.song_c = Song.objects.create(title="Ccc共通ワード")

    def test_keyword_with_sort_title_asc(self):
        qs, _ = song_search({"keyword": "共通ワード", "sort": "title", "size": "100"})
        titles = [s.title for s in qs]
        self.assertEqual(titles, ["Aaa共通ワード", "Bbb共通ワード", "Ccc共通ワード"])

    def test_keyword_with_sort_title_desc(self):
        qs, _ = song_search({"keyword": "共通ワード", "sort": "-title", "size": "100"})
        titles = [s.title for s in qs]
        self.assertEqual(titles, ["Ccc共通ワード", "Bbb共通ワード", "Aaa共通ワード"])

    def test_keyword_with_sort_id_asc(self):
        qs, _ = song_search({"keyword": "共通ワード", "sort": "id", "size": "100"})
        ids = [s.id for s in qs]
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, sorted(ids))

    def test_keyword_with_sort_id_desc(self):
        qs, _ = song_search({"keyword": "共通ワード", "sort": "-id", "size": "100"})
        ids = [s.id for s in qs]
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_title_filter_with_sort_title_asc(self):
        qs, _ = song_search({"title": "共通ワード", "sort": "title", "size": "100"})
        titles = [s.title for s in qs]
        self.assertEqual(titles, ["Aaa共通ワード", "Bbb共通ワード", "Ccc共通ワード"])

    def test_title_filter_with_sort_title_desc(self):
        qs, _ = song_search({"title": "共通ワード", "sort": "-title", "size": "100"})
        titles = [s.title for s in qs]
        self.assertEqual(titles, ["Ccc共通ワード", "Bbb共通ワード", "Aaa共通ワード"])


class SongSearchSortViewWithFilterTest(TestCase):
    """sort=view / sort=-view とフィルターの組み合わせテスト"""

    def setUp(self):
        # YouTube URL を持ち view 値が異なる3曲を作成（sort=view は YouTube フィルターと view>=1 を自動適用）
        for title, view, url_id in [
            ("共通ワードA", 300, "viewsorttest01"),
            ("共通ワードB", 100, "viewsorttest02"),
            ("共通ワードC", 200, "viewsorttest03"),
        ]:
            song = Song.objects.create(title=title, view=view)
            link = SongLink.objects.create(url=f"https://youtu.be/{url_id}")
            link.songs.add(song)

    def test_keyword_with_sort_view_asc(self):
        qs, _ = song_search({"keyword": "共通ワード", "sort": "view", "size": "100"})
        views = [s.view for s in qs]
        self.assertEqual(views, [100, 200, 300])

    def test_keyword_with_sort_view_desc(self):
        qs, _ = song_search({"keyword": "共通ワード", "sort": "-view", "size": "100"})
        views = [s.view for s in qs]
        self.assertEqual(views, [300, 200, 100])


class SongSearchSortWithAuthorFilterTest(TestCase):
    """author フィルターと sort の組み合わせテスト（author も distinct() を引き起こす）"""

    def setUp(self):
        author = Author.objects.create(name="共通作者")
        self.song_a = Song.objects.create(title="Aaa曲")
        self.song_b = Song.objects.create(title="Bbb曲")
        self.song_c = Song.objects.create(title="Ccc曲")
        for song in [self.song_a, self.song_b, self.song_c]:
            song.authors.add(author)

    def test_author_filter_with_sort_title_asc(self):
        qs, _ = song_search({"author": "共通作者", "sort": "title", "size": "100"})
        titles = [s.title for s in qs]
        self.assertEqual(titles, ["Aaa曲", "Bbb曲", "Ccc曲"])

    def test_author_filter_with_sort_title_desc(self):
        qs, _ = song_search({"author": "共通作者", "sort": "-title", "size": "100"})
        titles = [s.title for s in qs]
        self.assertEqual(titles, ["Ccc曲", "Bbb曲", "Aaa曲"])


class SongSearchValidationErrorTest(TestCase):
    """song_search() のバリデーションエラーテスト"""

    def test_invalid_sort_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            song_search({"sort": "invalid_field_xyz"})

    def test_zero_view_gte_raises_validation_error(self):
        # バリデーターは1以上を要求するため、0はエラーになる
        with self.assertRaises(ValidationError):
            song_search({"view_gte": "0"})

    def test_zero_like_gte_raises_validation_error(self):
        # バリデーターは1以上を要求するため、0はエラーになる
        with self.assertRaises(ValidationError):
            song_search({"like_gte": "0"})

    def test_title_too_long_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            song_search({"title": "あ" * 501})


class SongSearchAutoYoutubeFilterDuplicateTest(TestCase):
    """auto YouTube フィルター適用時に複数リンクを持つ曲が重複しないことを検証"""

    def setUp(self):
        from datetime import datetime, timezone
        self.song_a = Song.objects.create(
            title="YouTube曲A（リンク2本）",
            upload_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        self.song_b = Song.objects.create(
            title="YouTube曲B（リンク1本）",
            upload_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        # song_a に YouTube リンクを2本追加（重複の原因となるケース）
        link1 = SongLink.objects.create(url="https://youtu.be/aaa111")
        link1.songs.add(self.song_a)
        link2 = SongLink.objects.create(url="https://youtu.be/aaa222")
        link2.songs.add(self.song_a)
        # song_b に YouTube リンクを1本追加
        link3 = SongLink.objects.create(url="https://youtu.be/bbb111")
        link3.songs.add(self.song_b)

    def test_sort_upload_time_no_duplicate(self):
        """sort=upload_time のみ指定時、複数 YouTube リンクを持つ曲が重複しない"""
        _, stats = song_search({"sort": "upload_time", "size": "100"})
        self.assertEqual(stats["count"], 2)

    def test_sort_upload_time_same_count_as_explicit_mediatypes(self):
        """sort=upload_time と sort=upload_time&mediatypes=youtube の件数が一致する"""
        _, stats_auto = song_search({"sort": "upload_time", "size": "100"})
        _, stats_explicit = song_search({"sort": "upload_time", "mediatypes": "youtube", "size": "100"})
        self.assertEqual(stats_auto["count"], stats_explicit["count"])
