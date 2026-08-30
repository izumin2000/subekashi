"""
lib/stats_service.py のテスト

統計ページ(総合/authorごと)・stats管理コマンドが共通で使う集計ロジックを対象とする。
"""
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch
from django.test import RequestFactory, TestCase
from django.utils import timezone
from subekashi.models import Author, Song
from subekashi.lib.stats_service import (
    apply_songrange_filter,
    apply_upload_time_filter,
    compute_collaborator_count,
    compute_common_stats,
    compute_total_imitates,
    compute_unique_author_count,
    compute_unique_collaborator_count,
    filter_monthly_series_by_year_month,
    get_month_choices,
    get_song_ids,
    get_songrange_availability,
    get_year_choices,
    month_start,
    next_year_month,
    now_local,
    parse_int_or_none,
    resolve_songrange,
    resolve_year_month,
    with_monthly_deltas,
)


class ParseIntOrNoneTest(TestCase):
    def test_valid_int_string(self):
        self.assertEqual(parse_int_or_none("2024"), 2024)

    def test_non_numeric_string_returns_none(self):
        self.assertIsNone(parse_int_or_none("abc"))

    def test_float_string_returns_none(self):
        self.assertIsNone(parse_int_or_none("1.5"))

    def test_none_input_returns_none(self):
        self.assertIsNone(parse_int_or_none(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_int_or_none(""))


class NowLocalTest(TestCase):
    def test_returns_aware_datetime_close_to_now(self):
        before = timezone.now()
        result = now_local()
        after = timezone.now()

        self.assertTrue(timezone.is_aware(result))
        self.assertGreaterEqual(result, before)
        self.assertLessEqual(result, after)


class ApplySongrangeFilterTest(TestCase):
    def setUp(self):
        self.subeana_song = Song.objects.create(title="すべあな曲", is_subeana=True)
        self.xx_song = Song.objects.create(title="界隈外曲", is_subeana=False)

    def test_all_returns_everything(self):
        result = apply_songrange_filter(Song.objects.all(), "all")
        self.assertEqual(result.count(), 2)

    def test_subeana_filters_true_only(self):
        result = apply_songrange_filter(Song.objects.all(), "subeana")
        self.assertEqual(list(result), [self.subeana_song])

    def test_xx_filters_false_only(self):
        result = apply_songrange_filter(Song.objects.all(), "xx")
        self.assertEqual(list(result), [self.xx_song])


class GetSongrangeAvailabilityTest(TestCase):
    def test_both_exist(self):
        Song.objects.create(title="すべあな曲", is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)
        self.assertEqual(get_songrange_availability(Song.objects.all()), (True, True))

    def test_only_subeana_exists(self):
        Song.objects.create(title="すべあな曲", is_subeana=True)
        self.assertEqual(get_songrange_availability(Song.objects.all()), (True, False))

    def test_only_xx_exists(self):
        Song.objects.create(title="界隈外曲", is_subeana=False)
        self.assertEqual(get_songrange_availability(Song.objects.all()), (False, True))

    def test_neither_exists(self):
        self.assertEqual(get_songrange_availability(Song.objects.all()), (False, False))


class GetSongIdsTest(TestCase):
    def test_returns_id_list(self):
        song = Song.objects.create(title="曲")
        self.assertEqual(get_song_ids(Song.objects.all()), [song.id])

    def test_empty_queryset_returns_empty_list(self):
        self.assertEqual(get_song_ids(Song.objects.none()), [])


class ResolveSongrangeTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_defaults_to_all_when_both_exist(self):
        Song.objects.create(title="すべあな曲", is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)
        request = self.factory.get("/stats/")

        songrange, show_all_songrange = resolve_songrange(request, Song.objects.all())

        self.assertEqual(songrange, "all")
        self.assertTrue(show_all_songrange)

    def test_invalid_value_falls_back_to_all(self):
        Song.objects.create(title="すべあな曲", is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)
        request = self.factory.get("/stats/", {"songrange": "invalid"})

        songrange, _ = resolve_songrange(request, Song.objects.all())

        self.assertEqual(songrange, "all")

    def test_forced_to_existing_songrange_when_only_one_exists(self):
        Song.objects.create(title="すべあな曲", is_subeana=True)
        request = self.factory.get("/stats/")

        songrange, show_all_songrange = resolve_songrange(request, Song.objects.all())

        self.assertEqual(songrange, "subeana")
        self.assertFalse(show_all_songrange)

    def test_explicit_value_overridden_when_only_one_exists(self):
        Song.objects.create(title="すべあな曲", is_subeana=True)
        request = self.factory.get("/stats/", {"songrange": "xx"})

        songrange, _ = resolve_songrange(request, Song.objects.all())

        self.assertEqual(songrange, "subeana")


class ResolveYearMonthTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_defaults_to_all(self):
        request = self.factory.get("/stats/")

        year, month, year_choices, month_choices = resolve_year_month(request)

        self.assertEqual(year, "all")
        self.assertEqual(month, "all")
        self.assertEqual(year_choices, [])
        self.assertEqual(month_choices, list(range(1, 13)))

    def test_valid_year_normalizes_zero_padded_input(self):
        Song.objects.create(title="曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))
        request = self.factory.get("/stats/", {"year": "02024"})

        year, _, _, _ = resolve_year_month(request)

        self.assertEqual(year, "2024")

    def test_non_numeric_year_falls_back_to_all(self):
        request = self.factory.get("/stats/", {"year": "abc"})

        year, _, _, _ = resolve_year_month(request)

        self.assertEqual(year, "all")

    def test_year_choices_scoped_to_given_queryset(self):
        # year_choice_qsを渡すと、その範囲（authorの曲・選択中のsongrange等）で
        # 実際に選択可能な年のみに絞り込める（コードレビュー指摘対応）
        Song.objects.create(title="対象外の曲", upload_time=datetime(2020, 1, 1, tzinfo=dt_timezone.utc))
        target_song = Song.objects.create(title="対象の曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))
        request = self.factory.get("/stats/")

        _, _, year_choices, _ = resolve_year_month(request, Song.objects.filter(pk=target_song.pk))

        self.assertNotIn(2020, year_choices)
        self.assertIn(2024, year_choices)


class ApplyUploadTimeFilterTest(TestCase):
    def setUp(self):
        self.song_2024_01 = Song.objects.create(title="2024年1月", upload_time=datetime(2024, 1, 15, tzinfo=dt_timezone.utc))
        self.song_2024_06 = Song.objects.create(title="2024年6月", upload_time=datetime(2024, 6, 15, tzinfo=dt_timezone.utc))
        self.song_2025_01 = Song.objects.create(title="2025年1月", upload_time=datetime(2025, 1, 15, tzinfo=dt_timezone.utc))
        self.song_no_upload = Song.objects.create(title="upload_timeなし", upload_time=None)

    def test_year_all_returns_everything(self):
        result = apply_upload_time_filter(Song.objects.all(), "all", "all")
        self.assertEqual(result.count(), 4)

    def test_year_only_filters_by_year(self):
        result = apply_upload_time_filter(Song.objects.all(), "2024", "all")
        self.assertEqual(set(result), {self.song_2024_01, self.song_2024_06})

    def test_year_and_month_filters_by_both(self):
        result = apply_upload_time_filter(Song.objects.all(), "2024", "6")
        self.assertEqual(list(result), [self.song_2024_06])

    def test_month_only_filters_across_all_years(self):
        # yearが"all"でもmonthは独立して絞り込める（#334）
        result = apply_upload_time_filter(Song.objects.all(), "all", "1")
        self.assertEqual(set(result), {self.song_2024_01, self.song_2025_01})

    def test_upload_time_none_excluded_when_year_specified(self):
        result = apply_upload_time_filter(Song.objects.all(), "2024", "all")
        self.assertNotIn(self.song_no_upload, result)

    def test_upload_time_none_excluded_when_only_month_specified(self):
        result = apply_upload_time_filter(Song.objects.all(), "all", "1")
        self.assertNotIn(self.song_no_upload, result)


class ComputeCommonStatsTest(TestCase):
    def test_empty_queryset(self):
        stats = compute_common_stats(get_song_ids(Song.objects.none()))
        self.assertEqual(stats, {
            "song_count": 0,
            "total_view": 0,
            "total_like": 0,
            "total_authors": 0,
            "total_imitateds": 0,
        })

    def test_sums_view_and_like_treating_null_as_zero(self):
        Song.objects.create(title="曲1", view=100, like=10)
        Song.objects.create(title="曲2", view=None, like=None)

        stats = compute_common_stats(get_song_ids(Song.objects.all()))

        self.assertEqual(stats["song_count"], 2)
        self.assertEqual(stats["total_view"], 100)
        self.assertEqual(stats["total_like"], 10)

    def test_total_authors_counts_unique_authors_across_songs(self):
        # 同じ作者が複数曲に関わっていても重複せず1人として数える
        author_a = Author.objects.create(name="作者A")
        author_b = Author.objects.create(name="作者B")
        song = Song.objects.create(title="共作曲")
        song.authors.add(author_a, author_b)
        Song.objects.create(title="単独曲").authors.add(author_a)

        stats = compute_common_stats(get_song_ids(Song.objects.all()))

        self.assertEqual(stats["total_authors"], 2)

    def test_total_imitateds_counts_songs_that_imitate_this_song(self):
        original = Song.objects.create(title="原曲")
        imitate_1 = Song.objects.create(title="模倣曲1")
        imitate_2 = Song.objects.create(title="模倣曲2")
        imitate_1.imitates.add(original)
        imitate_2.imitates.add(original)

        stats = compute_common_stats(get_song_ids(Song.objects.filter(pk=original.pk)))

        self.assertEqual(stats["total_imitateds"], 2)

    def test_authors_and_imitateds_do_not_inflate_each_other(self):
        # 複数作者(ユニーク集計)かつ複数の模倣曲(Count集計)を同時に持つ曲で、
        # 異なる集計方法の値が互いに水増しされないことを確認する回帰テスト
        author_a = Author.objects.create(name="作者A")
        author_b = Author.objects.create(name="作者B")
        original = Song.objects.create(title="原曲")
        original.authors.add(author_a, author_b)
        Song.objects.create(title="模倣曲1").imitates.add(original)
        Song.objects.create(title="模倣曲2").imitates.add(original)
        Song.objects.create(title="模倣曲3").imitates.add(original)

        stats = compute_common_stats(get_song_ids(Song.objects.filter(pk=original.pk)))

        self.assertEqual(stats["total_authors"], 2)
        self.assertEqual(stats["total_imitateds"], 3)


class ComputeUniqueAuthorCountTest(TestCase):
    def test_shared_author_counted_once(self):
        author = Author.objects.create(name="共通作者")
        Song.objects.create(title="曲1").authors.add(author)
        Song.objects.create(title="曲2").authors.add(author)

        self.assertEqual(compute_unique_author_count(get_song_ids(Song.objects.all())), 1)

    def test_empty_queryset_returns_zero(self):
        self.assertEqual(compute_unique_author_count(get_song_ids(Song.objects.none())), 0)


class ComputeTotalImitatesTest(TestCase):
    def test_counts_songs_this_song_imitates(self):
        original_1 = Song.objects.create(title="原曲1")
        original_2 = Song.objects.create(title="原曲2")
        imitate = Song.objects.create(title="模倣曲")
        imitate.imitates.add(original_1, original_2)

        self.assertEqual(compute_total_imitates(get_song_ids(Song.objects.filter(pk=imitate.pk))), 2)


class ComputeCollaboratorCountTest(TestCase):
    def setUp(self):
        self.author_x = Author.objects.create(name="本人X")
        self.author_a = Author.objects.create(name="共作者A")
        self.author_b = Author.objects.create(name="共作者B")

        self.song_with_two_others = Song.objects.create(title="曲1")
        self.song_with_two_others.authors.add(self.author_x, self.author_a, self.author_b)

        self.song_solo = Song.objects.create(title="曲2")
        self.song_solo.authors.add(self.author_x)

        self.song_with_one_other = Song.objects.create(title="曲3")
        self.song_with_one_other.authors.add(self.author_x, self.author_a)

        self.song_ids = get_song_ids(Song.objects.filter(authors__id=self.author_x.id).distinct())

    def test_sums_other_authors_per_song_excluding_self(self):
        self.assertEqual(compute_collaborator_count(self.song_ids, self.author_x.id), 3)

    def test_solo_songs_only_returns_zero(self):
        song_ids = get_song_ids(Song.objects.filter(pk=self.song_solo.pk))
        self.assertEqual(compute_collaborator_count(song_ids, self.author_x.id), 0)

    def test_unique_counts_distinct_others_excluding_self(self):
        self.assertEqual(compute_unique_collaborator_count(self.song_ids, self.author_x.id), 2)

    def test_unique_solo_songs_only_returns_zero(self):
        song_ids = get_song_ids(Song.objects.filter(pk=self.song_solo.pk))
        self.assertEqual(compute_unique_collaborator_count(song_ids, self.author_x.id), 0)


class GetYearChoicesTest(TestCase):
    def test_no_songs_returns_empty_list(self):
        self.assertEqual(get_year_choices(), [])

    def test_songs_without_upload_time_are_ignored(self):
        Song.objects.create(title="upload_timeなし", upload_time=None)
        self.assertEqual(get_year_choices(), [])

    def test_returns_range_from_min_upload_time_year_to_current_year(self):
        Song.objects.create(title="古い曲", upload_time=datetime(2020, 1, 1, tzinfo=dt_timezone.utc))
        Song.objects.create(title="新しい曲", upload_time=timezone.now())

        current_year = now_local().year
        self.assertEqual(get_year_choices(), list(range(2020, current_year + 1)))

    def test_scoped_to_given_qs_ignores_songs_outside_it(self):
        # qsを渡すとその範囲のみで年を判定する（コードレビュー指摘対応）
        Song.objects.create(title="範囲外の古い曲", upload_time=datetime(2018, 1, 1, tzinfo=dt_timezone.utc))
        target = Song.objects.create(title="対象の曲", upload_time=datetime(2022, 1, 1, tzinfo=dt_timezone.utc))

        current_year = now_local().year
        result = get_year_choices(Song.objects.filter(pk=target.pk))

        self.assertEqual(result, list(range(2022, current_year + 1)))

    def test_min_upload_time_year_uses_local_timezone_not_utc(self):
        # UTC 2019-12-31 20:00 = JST 2020-01-01 05:00（コードレビュー指摘対応の回帰テスト）
        # ローカルタイムゾーンに変換せずupload_time.yearを直接使うと2019年始まりになってしまう
        Song.objects.create(title="曲", upload_time=datetime(2019, 12, 31, 20, 0, tzinfo=dt_timezone.utc))

        current_year = now_local().year
        self.assertEqual(get_year_choices(), list(range(2020, current_year + 1)))

    @patch("subekashi.lib.stats_service.now_local")
    def test_current_year_end_uses_now_local_not_raw_utc(self, mock_now_local):
        # timezone.now()の生の.yearをそのまま使うとUTC/JSTの境界でズレるバグの
        # 再発防止（コードレビュー指摘対応）。now_local()を経由することを確認する
        mock_now_local.return_value = timezone.make_aware(datetime(2027, 1, 1, 0, 30))
        Song.objects.create(title="曲", upload_time=timezone.make_aware(datetime(2020, 6, 1)))

        self.assertEqual(get_year_choices(), list(range(2020, 2028)))
        mock_now_local.assert_called()


class GetMonthChoicesTest(TestCase):
    def test_current_year_limits_to_current_month(self):
        current_year = now_local().year
        current_month = now_local().month
        self.assertEqual(get_month_choices(current_year, current_year), list(range(1, current_month + 1)))

    def test_past_year_returns_all_twelve_months(self):
        current_year = now_local().year
        self.assertEqual(get_month_choices(current_year - 1, current_year), list(range(1, 13)))

    @patch("subekashi.lib.stats_service.now_local")
    def test_current_year_cutoff_uses_now_local_not_raw_utc(self, mock_now_local):
        # timezone.now()の生の.monthをそのまま使うとUTC/JSTの境界でズレるバグの
        # 再発防止（コードレビュー指摘対応）
        mock_now_local.return_value = timezone.make_aware(datetime(2027, 1, 1, 0, 30))

        self.assertEqual(get_month_choices(2027, 2027), [1])
        mock_now_local.assert_called()


class NextYearMonthTest(TestCase):
    def test_normal_month_increments(self):
        self.assertEqual(next_year_month(2026, 3), (2026, 4))

    def test_december_rolls_over_to_next_year(self):
        self.assertEqual(next_year_month(2026, 12), (2027, 1))


class MonthStartTest(TestCase):
    def test_returns_aware_datetime_for_first_of_month(self):
        result = month_start(2026, 3)
        self.assertTrue(timezone.is_aware(result))
        local = timezone.localtime(result)
        self.assertEqual((local.year, local.month, local.day), (2026, 3, 1))


class WithMonthlyDeltasTest(TestCase):
    def test_first_row_delta_equals_cumulative_value(self):
        rows = [{"year": 2026, "month": 1, "song_count": 5, "total_view": 10, "total_like": 1, "total_authors": 2, "total_imitateds": 0}]
        result = with_monthly_deltas(rows)
        self.assertEqual(result[0]["song_count_delta"], 5)
        self.assertEqual(result[0]["total_view_delta"], 10)

    def test_subsequent_row_delta_is_difference_from_previous(self):
        rows = [
            {"year": 2026, "month": 1, "song_count": 5, "total_view": 10, "total_like": 1, "total_authors": 2, "total_imitateds": 0},
            {"year": 2026, "month": 2, "song_count": 8, "total_view": 25, "total_like": 3, "total_authors": 2, "total_imitateds": 1},
        ]
        result = with_monthly_deltas(rows)
        self.assertEqual(result[1]["song_count_delta"], 3)
        self.assertEqual(result[1]["total_view_delta"], 15)
        self.assertEqual(result[1]["total_authors_delta"], 0)

    def test_original_cumulative_values_are_preserved(self):
        rows = [{"year": 2026, "month": 1, "song_count": 5, "total_view": 10, "total_like": 1, "total_authors": 2, "total_imitateds": 0}]
        result = with_monthly_deltas(rows)
        self.assertEqual(result[0]["song_count"], 5)

    def test_empty_list_returns_empty_list(self):
        self.assertEqual(with_monthly_deltas([]), [])


class FilterMonthlySeriesByYearMonthTest(TestCase):
    def setUp(self):
        self.rows = [
            {"year": 2024, "month": 12},
            {"year": 2025, "month": 1},
            {"year": 2025, "month": 6},
        ]

    def test_year_all_returns_everything(self):
        self.assertEqual(filter_monthly_series_by_year_month(self.rows, "all", "all"), self.rows)

    def test_year_only_filters_by_year(self):
        result = filter_monthly_series_by_year_month(self.rows, "2025", "all")
        self.assertEqual(result, [{"year": 2025, "month": 1}, {"year": 2025, "month": 6}])

    def test_year_and_month_filters_by_both(self):
        result = filter_monthly_series_by_year_month(self.rows, "2025", "6")
        self.assertEqual(result, [{"year": 2025, "month": 6}])
