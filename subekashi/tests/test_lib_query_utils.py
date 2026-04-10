"""
lib/query_utils.py のテスト

クエリパラメータのクリーンアップとフィルタ/ソート判定のユーティリティ関数を対象とする。
DB不要のため SimpleTestCase を使用する。
"""
from django.test import SimpleTestCase
from subekashi.lib.query_utils import (
    clean_query_params,
    has_view_filter_or_sort,
    has_like_filter_or_sort,
)


class CleanQueryParamsTest(SimpleTestCase):
    """clean_query_params() のテスト"""

    def test_plain_dict_is_unchanged(self):
        params = {"key": "value", "other": "data"}
        result = clean_query_params(params)
        self.assertEqual(result, {"key": "value", "other": "data"})

    def test_list_value_returns_first_element(self):
        params = {"key": ["first", "second", "third"]}
        result = clean_query_params(params)
        self.assertEqual(result["key"], "first")

    def test_single_element_list_returns_element(self):
        params = {"key": ["only"]}
        result = clean_query_params(params)
        self.assertEqual(result["key"], "only")

    def test_empty_list_is_unchanged(self):
        params = {"key": []}
        result = clean_query_params(params)
        self.assertEqual(result["key"], [])

    def test_mixed_types_are_processed_correctly(self):
        params = {"a": "plain", "b": ["list_first", "list_second"]}
        result = clean_query_params(params)
        self.assertEqual(result["a"], "plain")
        self.assertEqual(result["b"], "list_first")

    def test_empty_dict_returns_empty_dict(self):
        result = clean_query_params({})
        self.assertEqual(result, {})

    def test_all_keys_are_preserved(self):
        params = {"x": "1", "y": ["2"], "z": "3"}
        result = clean_query_params(params)
        self.assertIn("x", result)
        self.assertIn("y", result)
        self.assertIn("z", result)


class HasViewFilterOrSortTest(SimpleTestCase):
    """has_view_filter_or_sort() のテスト"""

    def test_view_lte_key_returns_true(self):
        self.assertTrue(has_view_filter_or_sort({"view_lte": "100"}))

    def test_sort_view_returns_true(self):
        self.assertTrue(has_view_filter_or_sort({"sort": "view"}))

    def test_sort_minus_view_returns_true(self):
        self.assertTrue(has_view_filter_or_sort({"sort": "-view"}))

    def test_other_sort_returns_false(self):
        self.assertFalse(has_view_filter_or_sort({"sort": "title"}))

    def test_empty_dict_returns_false(self):
        self.assertFalse(has_view_filter_or_sort({}))

    def test_unrelated_key_returns_false(self):
        self.assertFalse(has_view_filter_or_sort({"keyword": "test"}))

    def test_view_lte_combined_with_other_keys(self):
        self.assertTrue(has_view_filter_or_sort({"view_lte": "50", "keyword": "abc"}))


class HasLikeFilterOrSortTest(SimpleTestCase):
    """has_like_filter_or_sort() のテスト"""

    def test_like_lte_key_returns_true(self):
        self.assertTrue(has_like_filter_or_sort({"like_lte": "50"}))

    def test_sort_like_returns_true(self):
        self.assertTrue(has_like_filter_or_sort({"sort": "like"}))

    def test_sort_minus_like_returns_true(self):
        self.assertTrue(has_like_filter_or_sort({"sort": "-like"}))

    def test_other_sort_returns_false(self):
        self.assertFalse(has_like_filter_or_sort({"sort": "title"}))

    def test_empty_dict_returns_false(self):
        self.assertFalse(has_like_filter_or_sort({}))

    def test_view_related_key_returns_false(self):
        self.assertFalse(has_like_filter_or_sort({"view_lte": "100", "sort": "view"}))

    def test_like_lte_combined_with_other_keys(self):
        self.assertTrue(has_like_filter_or_sort({"like_lte": "10", "sort": "id"}))
