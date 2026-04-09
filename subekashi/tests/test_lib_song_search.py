"""
lib/song_search.py のテスト

song_search() のページネーション・統計情報・バリデーションエラー処理を検証する。
"""
import math
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from subekashi.models import Song
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
