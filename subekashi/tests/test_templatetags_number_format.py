"""
templatetags/number_format.py のテスト
"""
from django.test import SimpleTestCase
from subekashi.templatetags.number_format import intcomma


class IntcommaTest(SimpleTestCase):
    def test_thousands_get_comma_separated(self):
        self.assertEqual(intcomma(1234567), "1,234,567")

    def test_small_number_has_no_comma(self):
        self.assertEqual(intcomma(123), "123")

    def test_zero(self):
        self.assertEqual(intcomma(0), "0")
