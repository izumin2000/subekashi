"""
lib/kenreki_service.py のテスト

authorごとの統計ページに表示する「鍵歴」（実績に応じて伸びる鍵盤）の算出ロジックを対象とする。
"""
from django.test import TestCase
from subekashi.lib.kenreki_service import (
    KENREKI_CAP_POINTS,
    LIKE_THRESHOLDS,
    MAX_TOTAL_POINTS,
    VIEW_THRESHOLDS,
    build_keyboard_geometry,
    compute_kenreki,
    compute_threshold_points,
)


class ComputeThresholdPointsTest(TestCase):
    def test_value_below_first_threshold_returns_zero(self):
        self.assertEqual(compute_threshold_points(0, VIEW_THRESHOLDS), 0)

    def test_reaching_first_threshold_only(self):
        self.assertEqual(compute_threshold_points(1, VIEW_THRESHOLDS), 1)

    def test_reaching_second_threshold_sums_triangular(self):
        # 1段階目+2段階目 = 1+2 = 3pt
        self.assertEqual(compute_threshold_points(20, VIEW_THRESHOLDS), 3)

    def test_value_between_thresholds_counts_lower_stages_only(self):
        # 20以上50未満は1〜2段階目のみ到達
        self.assertEqual(compute_threshold_points(49, VIEW_THRESHOLDS), 3)

    def test_reaching_all_thresholds(self):
        n = len(VIEW_THRESHOLDS)
        self.assertEqual(compute_threshold_points(10 ** 12, VIEW_THRESHOLDS), n * (n + 1) // 2)


class ComputeKenrekiTest(TestCase):
    def test_zero_view_and_like_returns_zero(self):
        result = compute_kenreki(0, 0)
        self.assertEqual(result["points"], 0)
        self.assertEqual(result["key_count"], 0)
        self.assertIsNone(result["overflow_color"])
        self.assertIsNone(result["overflow_ratio"])

    def test_combines_view_and_like_points(self):
        # view=20 -> 3pt, like=2 -> 1+2=3pt, 合計6pt / 2pt = 3本
        result = compute_kenreki(20, 2)
        self.assertEqual(result["points"], 6)
        self.assertEqual(result["key_count"], 3)

    def test_points_exactly_at_cap_does_not_overflow(self):
        # view 19段階目(1000万)=190pt + like 4段階目(10)=10pt = ちょうど200pt(cap)
        # 上限到達(100本)だが、cap超過ではないため色分岐は発生しない
        result = compute_kenreki(10_000_000, 10)
        self.assertEqual(result["points"], KENREKI_CAP_POINTS)
        self.assertEqual(result["key_count"], 100)
        self.assertIsNone(result["overflow_color"])
        self.assertIsNone(result["overflow_ratio"])

    def test_points_above_cap_starts_overflow_color_near_red(self):
        # view 20段階目(2000万)=210pt > 200pt(cap) だが超過幅は小さいため赤に近い色になる
        result = compute_kenreki(20_000_000, 0)
        self.assertEqual(result["points"], 210)
        self.assertEqual(result["key_count"], 100)
        self.assertIsNotNone(result["overflow_color"])
        self.assertTrue(result["overflow_color"].startswith("hsl(10,"))
        self.assertAlmostEqual(result["overflow_ratio"], 10 / 284)

    def test_max_possible_points_reaches_full_purple(self):
        result = compute_kenreki(10 ** 12, 10 ** 12)
        self.assertEqual(result["points"], MAX_TOTAL_POINTS)
        self.assertEqual(result["overflow_color"], "hsl(270, 75%, 45%)")
        self.assertEqual(result["overflow_ratio"], 1.0)

    def test_key_count_capped_at_100(self):
        result = compute_kenreki(10 ** 12, 10 ** 12)
        self.assertLessEqual(result["key_count"], 100)


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
