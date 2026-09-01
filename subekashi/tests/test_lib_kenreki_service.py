"""
lib/kenreki_service.py のテスト

authorごとの統計ページに表示する「鍵歴」（実績に応じて伸びる鍵盤）の算出ロジックを対象とする。
"""
from django.test import TestCase
from subekashi.lib.kenreki_service import (
    LIKE_THRESHOLDS,
    MAX_KEYS,
    MAX_POSSIBLE_KEY_COUNT,
    MAX_TOTAL_POINTS,
    VIEW_THRESHOLDS,
    build_keyboard_geometry,
    compute_kenreki,
    compute_kenreki_for_songs,
    compute_song_points,
    compute_threshold_points,
)


class ComputeThresholdPointsTest(TestCase):
    # ptは到達した段階数そのもの（三角数ではない、単純なカウント）
    def test_value_below_first_threshold_returns_zero(self):
        self.assertEqual(compute_threshold_points(0, VIEW_THRESHOLDS), 0)

    def test_reaching_first_threshold_only(self):
        self.assertEqual(compute_threshold_points(1, VIEW_THRESHOLDS), 1)

    def test_reaching_multiple_thresholds(self):
        # 55は1・20・50の3段階に到達（次の100には未到達）
        self.assertEqual(compute_threshold_points(55, VIEW_THRESHOLDS), 3)

    def test_value_between_thresholds_counts_reached_only(self):
        # 49は1・20の2段階のみ到達（50には未到達）
        self.assertEqual(compute_threshold_points(49, VIEW_THRESHOLDS), 2)

    def test_reaching_all_thresholds(self):
        self.assertEqual(compute_threshold_points(10 ** 12, VIEW_THRESHOLDS), len(VIEW_THRESHOLDS))


class ComputeSongPointsTest(TestCase):
    def test_combines_view_and_like_points(self):
        # view=20は1・20の2段階(2pt)、like=2は1・2の2段階(2pt) -> 合計4pt
        self.assertEqual(compute_song_points(20, 2), 4)

    def test_zero_view_and_like_returns_zero(self):
        self.assertEqual(compute_song_points(0, 0), 0)


class ComputeKenrekiTest(TestCase):
    def test_zero_view_and_like_returns_zero(self):
        result = compute_kenreki(0, 0)
        self.assertEqual(result["points"], 0)
        self.assertEqual(result["key_count"], 0)
        self.assertIsNone(result["overflow_color"])
        self.assertIsNone(result["overflow_ratio"])
        self.assertIsNone(result["overflow_upper_bound"])

    def test_matches_compute_song_points(self):
        result = compute_kenreki(20, 2)
        self.assertEqual(result["points"], 4)
        self.assertEqual(result["key_count"], 2)

    def test_single_song_cannot_reach_max_keys_alone(self):
        # 1曲だけでは(view/likeとも全閾値到達=43pt->21鍵)MAX_KEYS(88)に届かない
        # 鍵歴が複数曲の総和で伸びていく設計であることの裏付け
        result = compute_kenreki(10 ** 12, 10 ** 12)
        self.assertEqual(result["points"], MAX_TOTAL_POINTS)
        self.assertLess(result["key_count"], MAX_KEYS)
        self.assertIsNone(result["overflow_color"])

    def test_overflow_lower_bound_always_present(self):
        result = compute_kenreki(0, 0)
        self.assertEqual(result["overflow_lower_bound"], MAX_KEYS)


class ComputeKenrekiForSongsTest(TestCase):
    def test_empty_list_returns_zero(self):
        result = compute_kenreki_for_songs([])
        self.assertEqual(result["points"], 0)
        self.assertEqual(result["key_count"], 0)

    def test_single_song_matches_compute_kenreki(self):
        self.assertEqual(compute_kenreki_for_songs([(20, 2)]), compute_kenreki(20, 2))

    def test_sums_points_across_multiple_songs(self):
        # 各曲view=1は1段階目のみ到達(1pt)。3曲で合計3pt -> 1本(3//2)
        result = compute_kenreki_for_songs([(1, 0), (1, 0), (1, 0)])
        self.assertEqual(result["points"], 3)
        self.assertEqual(result["key_count"], 1)

    def test_many_small_songs_can_outscore_one_song_with_the_same_total_view(self):
        # 鍵歴はSongごとに算出してから合計する仕様のため、同じ合計viewでも
        # 曲数が多いほど有利になる（1曲でview=10より、view=1の曲が10曲の方がpt合計が高い）
        many_small_songs = [(1, 0)] * 10  # 各曲1段階目のみ到達(1pt) x10 = 10pt
        one_big_song = [(10, 0)]  # 10は2段階目(20)未満のため1段階目のみ(1pt)

        many_result = compute_kenreki_for_songs(many_small_songs)
        one_result = compute_kenreki_for_songs(one_big_song)

        self.assertEqual(many_result["points"], 10)
        self.assertEqual(one_result["points"], 1)
        self.assertGreater(many_result["points"], one_result["points"])

    def test_below_max_keys_does_not_overflow(self):
        # 全閾値到達の曲(43pt)を4曲 -> 172pt -> 86鍵（MAX_KEYS未満で色分岐なし）
        result = compute_kenreki_for_songs([(10 ** 12, 10 ** 12)] * 4)
        self.assertEqual(result["points"], 172)
        self.assertEqual(result["key_count"], 86)
        self.assertIsNone(result["overflow_color"])
        self.assertIsNone(result["overflow_ratio"])

    def test_at_or_above_max_keys_overflows(self):
        # 全閾値到達の曲(43pt)を5曲 -> 215pt -> 107鍵（MAX_KEYS以上で色分岐開始）
        result = compute_kenreki_for_songs([(10 ** 12, 10 ** 12)] * 5)
        self.assertEqual(result["points"], 215)
        self.assertEqual(result["key_count"], 107)
        self.assertGreater(result["key_count"], MAX_KEYS)
        self.assertIsNotNone(result["overflow_color"])
        self.assertEqual(result["overflow_upper_bound"], MAX_POSSIBLE_KEY_COUNT)


class BuildKeyboardGeometryTest(TestCase):
    def test_zero_keys_has_no_black_keys(self):
        geometry = build_keyboard_geometry(0)
        self.assertEqual(geometry["white_key_count"], 0)
        self.assertEqual(geometry["black_keys"], [])
        self.assertEqual(geometry["width"], 0)

    def test_single_white_key_has_no_trailing_black_key(self):
        geometry = build_keyboard_geometry(1)
        self.assertEqual(geometry["black_keys"], [])

    def test_one_octave_has_five_black_keys(self):
        # 白鍵7本（C~B）につき黒鍵は5本（E-F、B-C間には黒鍵が無い標準的な鍵盤配列）
        geometry = build_keyboard_geometry(7)
        self.assertEqual(len(geometry["black_keys"]), 5)

    def test_black_key_color_applied_to_all_black_keys(self):
        geometry = build_keyboard_geometry(7, black_key_color="hsl(120, 75%, 45%)")
        self.assertTrue(all(bk["color"] == "hsl(120, 75%, 45%)" for bk in geometry["black_keys"]))

    def test_width_matches_white_key_count(self):
        geometry = build_keyboard_geometry(10)
        self.assertEqual(geometry["width"], 10 * 12)

    def test_white_keys_is_iterable_of_key_count_length(self):
        geometry = build_keyboard_geometry(10)
        self.assertEqual(len(list(geometry["white_keys"])), 10)
