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
        self.assertIsNone(result["overflow_upper_bound"])

    def test_combines_view_and_like_points(self):
        # view=20 -> 3pt, like=2 -> 1+2=3pt, 合計6pt / 2pt = 3本
        result = compute_kenreki(20, 2)
        self.assertEqual(result["points"], 6)
        self.assertEqual(result["key_count"], 3)

    def test_key_count_just_below_max_keys_does_not_overflow(self):
        # view 18段階目(500万)+like 2段階目(2) = 171+3 = 174pt -> 87鍵（MAX_KEYS未満で色分岐なし）
        result = compute_kenreki(5_000_000, 2)
        self.assertEqual(result["points"], 174)
        self.assertEqual(result["key_count"], 87)
        self.assertIsNone(result["overflow_color"])
        self.assertIsNone(result["overflow_ratio"])

    def test_key_count_at_max_keys_starts_overflow_color_at_red(self):
        # view 18段階目(500万)+like 3段階目(5) = 171+6 = 177pt -> ちょうど88鍵(MAX_KEYS)到達
        # コードレビュー指摘対応: MAX_KEYS以上は鍵盤数をカンストさせずそのまま表示し、
        # 色だけを付ける（以前はkey_countを100でmin()してしまっていた）
        result = compute_kenreki(5_000_000, 5)
        self.assertEqual(result["points"], 177)
        self.assertEqual(result["key_count"], MAX_KEYS)
        self.assertEqual(result["overflow_color"], "hsl(0, 75%, 45%)")
        self.assertEqual(result["overflow_ratio"], 0.0)
        self.assertEqual(result["overflow_upper_bound"], MAX_POSSIBLE_KEY_COUNT)

    def test_key_count_exceeds_max_keys_without_capping(self):
        # view 19段階目(1000万)=190pt -> 95鍵。MAX_KEYS(88)を超えてもカンストせず95のまま表示する
        result = compute_kenreki(10_000_000, 0)
        self.assertEqual(result["points"], 190)
        self.assertEqual(result["key_count"], 95)
        self.assertGreater(result["key_count"], MAX_KEYS)
        self.assertIsNotNone(result["overflow_color"])

    def test_reaching_every_threshold_does_not_reach_full_purple(self):
        # MAX_POSSIBLE_KEY_COUNT(1000)は現行の閾値表で理論上到達しうる最大鍵盤数(242)より
        # 大きい値のため、全閾値に到達しても紫(hue=270)には届かない（伸びしろとして意図的）
        result = compute_kenreki(10 ** 12, 10 ** 12)
        self.assertEqual(result["points"], MAX_TOTAL_POINTS)
        self.assertEqual(result["key_count"], MAX_TOTAL_POINTS // 2)
        self.assertLess(result["overflow_ratio"], 1.0)
        self.assertNotEqual(result["overflow_color"], "hsl(270, 75%, 45%)")

    def test_overflow_lower_bound_always_present(self):
        result = compute_kenreki(0, 0)
        self.assertEqual(result["overflow_lower_bound"], MAX_KEYS)

    def test_overflow_upper_bound_is_fixed_constant(self):
        result = compute_kenreki(10_000_000, 0)
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
