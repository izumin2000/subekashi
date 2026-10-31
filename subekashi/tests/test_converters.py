"""
SQLiteIntConverter のテスト

巨大な整数を含むURLアクセス時に OverflowError ではなく 404 になることを検証する。
"""
from django.test import TestCase, Client, override_settings

from subekashi.converters import SQLiteIntConverter, parse_sqlite_id
from subekashi.models import Song


STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

SQLITE_INT_MAX = 9223372036854775807
SQLITE_INT_MIN = -9223372036854775808


class SQLiteIntConverterTest(TestCase):
    """SQLiteIntConverter.to_python() のテスト"""

    def setUp(self):
        self.converter = SQLiteIntConverter()

    def test_normal_value_returns_int(self):
        self.assertEqual(self.converter.to_python("123"), 123)

    def test_max_value_is_accepted(self):
        self.assertEqual(self.converter.to_python(str(SQLITE_INT_MAX)), SQLITE_INT_MAX)

    def test_over_max_value_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.converter.to_python(str(SQLITE_INT_MAX + 1))

    def test_huge_value_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.converter.to_python("9" * 30)

    def test_to_url_returns_str(self):
        self.assertEqual(self.converter.to_url(123), "123")


class ParseSqliteIdTest(TestCase):
    """parse_sqlite_id() のテスト（#1290）"""

    def test_normal_value_returns_int(self):
        self.assertEqual(parse_sqlite_id("123"), 123)

    def test_zero_is_accepted(self):
        self.assertEqual(parse_sqlite_id("0"), 0)

    def test_max_value_is_accepted(self):
        self.assertEqual(parse_sqlite_id(str(SQLITE_INT_MAX)), SQLITE_INT_MAX)

    def test_over_max_value_returns_none(self):
        self.assertIsNone(parse_sqlite_id(str(SQLITE_INT_MAX + 1)))

    def test_too_many_digits_returns_none(self):
        # Python 3.11以降のint()の桁数の上限（4300桁）を超える文字列でも例外にならない
        self.assertIsNone(parse_sqlite_id("9" * 30))
        self.assertIsNone(parse_sqlite_id("1" * 5000))

    def test_non_digit_values_return_none(self):
        for value in ["", " ", "abc", "-1", "+1", "1.5", "1e3", " 12", "12 "]:
            with self.subTest(value=value):
                self.assertIsNone(parse_sqlite_id(value))

    def test_non_ascii_digits_return_none(self):
        # "²"はisdigit()がTrueになるがint()で変換できず、"１２"は全角の数字
        for value in ["²", "１２"]:
            with self.subTest(value=value):
                self.assertIsNone(parse_sqlite_id(value))


@override_settings(STORAGES=STATIC_STORAGE)
class SQLiteIntConverterUrlTest(TestCase):
    """巨大な整数を含むURLアクセス時の挙動テスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="URLテスト曲")

    def test_normal_song_id_returns_200(self):
        response = self.client.get(f"/songs/{self.song.id}/")
        self.assertEqual(response.status_code, 200)

    def test_huge_song_id_returns_404(self):
        response = self.client.get(f"/songs/{SQLITE_INT_MAX + 1}/")
        self.assertEqual(response.status_code, 404)

    def test_extremely_huge_song_id_returns_404(self):
        response = self.client.get(f"/songs/{'9' * 30}/")
        self.assertEqual(response.status_code, 404)
