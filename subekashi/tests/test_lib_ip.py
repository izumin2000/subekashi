"""
lib/ip.py のテスト

get_client_ip(): レート制限で使うクライアントのIP（settings.RATELIMIT_IP_META_KEY、#1188）。
PythonAnywhereではREMOTE_ADDRがロードバランサーのIPになるため、ロードバランサーが付けるX-Real-IPを使う。
"""
from django.test import RequestFactory, SimpleTestCase
from subekashi.lib.ip import get_client_ip


class GetClientIpTest(SimpleTestCase):
    """get_client_ip() のテスト"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_uses_x_real_ip(self):
        request = self.factory.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="203.0.113.1")
        self.assertEqual(get_client_ip(request), "203.0.113.1")

    def test_falls_back_to_remote_addr_without_x_real_ip(self):
        request = self.factory.get("/", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    def test_falls_back_to_remote_addr_with_empty_x_real_ip(self):
        request = self.factory.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="")
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    def test_falls_back_to_remote_addr_with_invalid_x_real_ip(self):
        # IPでない値はdjango_ratelimitが解析できず500になるため使わない
        for value in ["not-an-ip", "203.0.113.1, 198.51.100.1", "203.0.113.1/24"]:
            with self.subTest(value=value):
                request = self.factory.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP=value)
                self.assertEqual(get_client_ip(request), "10.0.0.1")

    def test_uses_ipv6_x_real_ip(self):
        request = self.factory.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="2001:db8::1")
        self.assertEqual(get_client_ip(request), "2001:db8::1")

    def test_raises_without_remote_addr(self):
        # django_ratelimitの既定と同じく、REMOTE_ADDRは必ずある前提にし、Noneを返さない
        request = self.factory.get("/")
        del request.META["REMOTE_ADDR"]
        with self.assertRaises(KeyError):
            get_client_ip(request)

    def test_does_not_use_x_forwarded_for(self):
        # X-Forwarded-Forはクライアントが自由に付けられるため使わない
        request = self.factory.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="198.51.100.1")
        self.assertEqual(get_client_ip(request), "10.0.0.1")
