"""
lib/song_filterset.py のテスト

作者ページの並び替え（order_by_sort_with_missing_last、#606）を対象とする。
SongFilter自体は曲の検索APIのテスト（test_api.py）で検証している。
"""
from datetime import datetime, timezone as dt_timezone
from django.test import TestCase
from subekashi.lib.query_utils import YOUTUBE_SORTS
from subekashi.lib.song_filterset import order_by_sort_with_missing_last
from subekashi.models import Author, Song


class OrderBySortWithMissingLastTest(TestCase):
    """order_by_sort_with_missing_last() のテスト（#606）"""

    def setUp(self):
        self.author = Author.objects.create(name="並び替えテスト作者")

    def _create_song(self, title, **fields):
        song = Song.objects.create(title=title, **fields)
        song.authors.add(self.author)
        return song

    def _titles(self, sort):
        queryset = order_by_sort_with_missing_last(Song.get_for_author(self.author.id), sort)
        return list(queryset.values_list("title", flat=True))

    def test_upload_time_sort_puts_songs_without_upload_time_last(self):
        # 検索と異なりupload_timeが無い曲も除外せず、昇順・降順のどちらでも末尾に並べる
        self._create_song("投稿日なし")
        self._create_song("2020年", upload_time=datetime(2020, 1, 1, tzinfo=dt_timezone.utc))
        self._create_song("2024年", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))

        self.assertEqual(self._titles("upload_time"), ["2020年", "2024年", "投稿日なし"])
        self.assertEqual(self._titles("-upload_time"), ["2024年", "2020年", "投稿日なし"])

    def test_view_sort_puts_songs_without_view_last(self):
        # 検索の自動フィルタ（view >= 1）に合わせ、viewが0の曲もNULLの曲と同様に末尾に並べる
        self._create_song("再生回数なし")
        self._create_song("再生回数0", view=0)
        self._create_song("再生回数10", view=10)
        self._create_song("再生回数100", view=100)

        self.assertEqual(self._titles("view")[:2], ["再生回数10", "再生回数100"])
        self.assertEqual(self._titles("-view")[:2], ["再生回数100", "再生回数10"])
        self.assertCountEqual(self._titles("view")[2:], ["再生回数なし", "再生回数0"])
        self.assertCountEqual(self._titles("-view")[2:], ["再生回数なし", "再生回数0"])

    def test_like_sort_puts_songs_without_like_last(self):
        self._create_song("高評価数なし")
        self._create_song("高評価数0", like=0)
        self._create_song("高評価数5", like=5)
        self._create_song("高評価数50", like=50)

        self.assertEqual(self._titles("like")[:2], ["高評価数5", "高評価数50"])
        self.assertEqual(self._titles("-like")[:2], ["高評価数50", "高評価数5"])
        self.assertCountEqual(self._titles("like")[2:], ["高評価数なし", "高評価数0"])

    def test_songs_without_youtube_data_are_ordered_by_newest_registration(self):
        first = self._create_song("先に登録")
        second = self._create_song("後に登録")

        for sort in YOUTUBE_SORTS:
            with self.subTest(sort=sort):
                self.assertEqual(self._titles(sort), [second.title, first.title])

    def test_same_value_songs_are_ordered_by_newest_registration(self):
        self._create_song("同じ再生回数1", view=10)
        self._create_song("同じ再生回数2", view=10)

        self.assertEqual(self._titles("-view"), ["同じ再生回数2", "同じ再生回数1"])
        self.assertEqual(self._titles("view"), ["同じ再生回数2", "同じ再生回数1"])

    def test_non_youtube_sort_is_same_as_search(self):
        # YouTube以外の並び替えは曲の検索と同じ（order_by_sort）
        self._create_song("登録1")
        self._create_song("登録2")
        self._create_song("登録3")

        self.assertEqual(self._titles("id"), ["登録1", "登録2", "登録3"])
        self.assertEqual(self._titles("-id"), ["登録3", "登録2", "登録1"])

    def test_imitated_count_sort(self):
        original = self._create_song("模倣元")
        imitation = self._create_song("模倣曲")
        imitation.imitates.add(original)

        self.assertEqual(self._titles("-imitated_count"), ["模倣元", "模倣曲"])
        self.assertEqual(self._titles("-imitate_count"), ["模倣曲", "模倣元"])

    def test_random_sort_returns_all_songs(self):
        for i in range(3):
            self._create_song(f"ランダム{i}")

        self.assertCountEqual(self._titles("random"), ["ランダム0", "ランダム1", "ランダム2"])
