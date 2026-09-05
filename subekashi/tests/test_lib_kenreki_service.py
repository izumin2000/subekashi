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
        self.assertIsNone(result["overflow_color"])
        self.assertIsNone(result["overflow_ratio"])
        self.assertIsNone(result["overflow_upper_bound"])

    def test_matches_compute_song_points(self):
        result = compute_kenreki(20, 2)
        self.assertEqual(result["points"], 4)

    def test_single_song_cannot_reach_max_keys_alone(self):
        # 1曲だけでは(view/likeとも全閾値到達=43pt)MAX_KEYS(88)に届かない
        # 鍵歴が複数曲の総和で伸びていく設計であることの裏付け
        result = compute_kenreki(10 ** 12, 10 ** 12)
        self.assertEqual(result["points"], MAX_TOTAL_POINTS)
        self.assertLess(result["points"], MAX_KEYS)
        self.assertIsNone(result["overflow_color"])

    def test_overflow_lower_bound_always_present(self):
        result = compute_kenreki(0, 0)
        self.assertEqual(result["overflow_lower_bound"], MAX_KEYS)


class ComputeKenrekiForSongsTest(TestCase):
    def test_empty_list_returns_zero(self):
        result = compute_kenreki_for_songs([])
        self.assertEqual(result["points"], 0)

    def test_single_song_matches_compute_kenreki(self):
        self.assertEqual(compute_kenreki_for_songs([(20, 2)]), compute_kenreki(20, 2))

    def test_sums_points_across_multiple_songs(self):
        # 各曲view=1は1段階目のみ到達(1pt)。3曲で合計3pt
        result = compute_kenreki_for_songs([(1, 0), (1, 0), (1, 0)])
        self.assertEqual(result["points"], 3)

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
        # 全閾値到達の曲(43pt)を2曲 -> 86pt（MAX_KEYS未満で色分岐なし）
        result = compute_kenreki_for_songs([(10 ** 12, 10 ** 12)] * 2)
        self.assertEqual(result["points"], 86)
        self.assertIsNone(result["overflow_color"])
        self.assertIsNone(result["overflow_ratio"])

    def test_at_or_above_max_keys_overflows(self):
        # 全閾値到達の曲(43pt)を3曲 -> 129pt（MAX_KEYS以上で色分岐開始）
        result = compute_kenreki_for_songs([(10 ** 12, 10 ** 12)] * 3)
        self.assertEqual(result["points"], 129)
        self.assertGreater(result["points"], MAX_KEYS)
        self.assertIsNotNone(result["overflow_color"])
        self.assertEqual(result["overflow_upper_bound"], MAX_POSSIBLE_KEY_COUNT)


class BuildKeyboardGeometryTest(TestCase):
    # key_countは白鍵の本数（度数）ではなく、黒鍵も含めた鍵の総数として扱う
    # （コードレビュー指摘対応: 以前はkey_countがそのまま白鍵の本数だったため、
    # 鍵盤数が1増えても黒鍵は無視され白鍵だけが増えていた。ラ(A)から始まる
    # 12半音の繰り返しをkey_count個分たどり、白鍵・黒鍵それぞれの本数を数える）
    def test_zero_keys_has_no_black_keys(self):
        geometry = build_keyboard_geometry(0)
        self.assertEqual(geometry["white_key_count"], 0)
        self.assertEqual(geometry["black_keys"], [])
        self.assertEqual(geometry["width"], 0)

    def test_first_key_is_white(self):
        # ラ(A)から始まるため、1鍵目は必ず白鍵
        geometry = build_keyboard_geometry(1)
        self.assertEqual(geometry["white_key_count"], 1)
        self.assertEqual(geometry["black_keys"], [])

    def test_second_key_adds_a_black_key_not_a_white_key(self):
        # ラ(A)の次はラ#(A#、黒鍵)。度数(白鍵)ではなく実際の鍵盤数が増える
        geometry = build_keyboard_geometry(2)
        self.assertEqual(geometry["white_key_count"], 1)
        self.assertEqual(len(geometry["black_keys"]), 1)

    def test_one_full_octave_has_five_black_keys(self):
        # 12半音(1オクターブ)分で白鍵7本・黒鍵5本（標準的な鍵盤配列と一致）
        geometry = build_keyboard_geometry(12)
        self.assertEqual(geometry["white_key_count"], 7)
        self.assertEqual(len(geometry["black_keys"]), 5)

    def test_black_key_color_applied_to_all_black_keys(self):
        geometry = build_keyboard_geometry(12, black_key_color="hsl(120, 75%, 45%)")
        self.assertTrue(all(bk["color"] == "hsl(120, 75%, 45%)" for bk in geometry["black_keys"]))

    def test_width_matches_white_key_count_when_ending_on_white_key(self):
        # key_count=8はミ(E, 白鍵)で終わる -> 白鍵5本分の幅のみ
        geometry = build_keyboard_geometry(8)
        self.assertEqual(geometry["white_key_count"], 5)
        self.assertEqual(geometry["width"], 5 * 12)

    def test_width_includes_overhang_when_ending_on_black_key(self):
        # key_count=2はラ#(A#、黒鍵)で終わる -> 白鍵1本分の幅+黒鍵のはみ出し分
        geometry = build_keyboard_geometry(2)
        self.assertEqual(geometry["width"], 1 * 12 + 8 // 2)

    def test_white_keys_is_iterable_of_white_key_count_length(self):
        geometry = build_keyboard_geometry(12)
        self.assertEqual(len(list(geometry["white_keys"])), geometry["white_key_count"])
