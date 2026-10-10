"""
ミドルウェアのテスト

RatelimitMiddleware・CacheControlMiddleware・ContentSecurityPolicyMiddleware・RestrictIPMiddleware の動作を検証する。
"""
import json
from unittest.mock import MagicMock, patch
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django_ratelimit.exceptions import Ratelimited
from subekashi.middleware.rate_limit import RatelimitMiddleware
from subekashi.middleware.cache import CacheControlMiddleware
from subekashi.middleware.csp import ContentSecurityPolicyMiddleware
from subekashi.middleware.restrict_ip import RestrictIPMiddleware
from subekashi.constants.constants import SHORT_TERM_COOKIE_AGE, LONG_TERM_COOKIE_AGE


STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class RatelimitMiddlewareTest(SimpleTestCase):
    """RatelimitMiddleware のテスト"""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RatelimitMiddleware(lambda req: HttpResponse("OK"))

    def _process_ratelimited(self):
        return self.middleware.process_exception(self.factory.get("/"), Ratelimited())

    def test_normal_request_passes_through(self):
        expected_response = HttpResponse("OK")
        middleware = RatelimitMiddleware(lambda req: expected_response)
        request = self.factory.get("/")
        response = middleware(request)
        self.assertEqual(response, expected_response)

    def test_ratelimited_returns_429(self):
        response = self._process_ratelimited()
        self.assertEqual(response.status_code, 429)

    def test_ratelimited_response_is_json(self):
        response = self._process_ratelimited()
        self.assertIsInstance(response, JsonResponse)

    def test_ratelimited_response_contains_error_key(self):
        response = self._process_ratelimited()
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Rate limit exceeded")

    def test_ratelimited_response_has_retry_after(self):
        response = self._process_ratelimited()
        self.assertEqual(response["Retry-After"], "1")

    def test_ratelimited_response_is_not_cached(self):
        # CacheControlMiddlewareにpublicのCache-Controlを付けさせない
        response = self._process_ratelimited()
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_other_permission_denied_is_not_handled(self):
        response = self.middleware.process_exception(self.factory.get("/"), PermissionDenied())
        self.assertIsNone(response)


@override_settings(STORAGES=STATIC_STORAGE)
@patch("django_ratelimit.core.time")
class RatelimitMiddlewareClientTest(TestCase):
    """@ratelimit(block=True) のビューにClientでリクエストし、制限を超えると429になることのテスト（#1187）

    RatelimitedはPermissionDeniedのサブクラスのため、ミドルウェアの__call__で捕まえようとしても届く前に403になる。
    ミドルウェアにRatelimitedを直接渡すテストでは検出できないため、実際にリクエストして確認する。
    1秒の区切りをまたいでカウントがリセットされないよう、django_ratelimitの時刻を固定する。
    """

    def setUp(self):
        cache.clear()

    def _assert_third_request_is_limited(self, url):
        for _ in range(2):
            self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {"error": "Rate limit exceeded"})
        self.assertEqual(response["Retry-After"], "1")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_song_cards_returns_429_when_limited(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        self._assert_third_request_is_limited(reverse("subekashi:song_cards"))

    def test_song_guessers_returns_429_when_limited(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        self._assert_third_request_is_limited(reverse("subekashi:song_guessers") + "?guesser=曲")

    def test_limit_resets_in_next_second(self, mock_time):
        url = reverse("subekashi:song_cards")
        mock_time.time.return_value = 1_800_000_000
        for _ in range(3):
            self.client.get(url)

        mock_time.time.return_value = 1_800_000_001

        self.assertEqual(self.client.get(url).status_code, 200)


@override_settings(STATIC_URL="/static/", STORAGES=STATIC_STORAGE)
class CacheControlMiddlewareTest(SimpleTestCase):
    """CacheControlMiddleware のテスト"""

    def setUp(self):
        self.factory = RequestFactory()

    def _apply_middleware(self, path, existing_cache_control=None):
        response = HttpResponse("OK")
        if existing_cache_control:
            response["Cache-Control"] = existing_cache_control
        request = self.factory.get(path)
        # MiddlewareMixin は get_response=None を拒否するためダミーを渡す
        middleware = CacheControlMiddleware(lambda req: HttpResponse())
        return middleware.process_response(request, response)

    def test_non_static_path_gets_short_term_cache(self):
        response = self._apply_middleware("/songs/")
        self.assertIn(f"max-age={SHORT_TERM_COOKIE_AGE}", response["Cache-Control"])

    def test_static_path_gets_long_term_cache(self):
        response = self._apply_middleware("/static/subekashi/css/style.css")
        self.assertIn(f"max-age={LONG_TERM_COOKIE_AGE}", response["Cache-Control"])

    def test_cache_control_already_set_is_not_overwritten(self):
        existing = "no-cache"
        response = self._apply_middleware("/songs/", existing_cache_control=existing)
        self.assertEqual(response["Cache-Control"], existing)

    def test_pragma_header_is_set(self):
        response = self._apply_middleware("/songs/")
        self.assertEqual(response["Pragma"], "cache")

    def test_expires_header_is_set(self):
        response = self._apply_middleware("/songs/")
        self.assertIn("Expires", response)

    def test_cache_control_is_public(self):
        response = self._apply_middleware("/songs/")
        self.assertIn("public", response["Cache-Control"])


class ContentSecurityPolicyMiddlewareTest(SimpleTestCase):
    """ContentSecurityPolicyMiddleware のテスト"""

    def setUp(self):
        self.factory = RequestFactory()

    def _call(self, response):
        request = self.factory.get("/")
        middleware = ContentSecurityPolicyMiddleware(lambda req: response)
        return request, middleware(request)

    def _directives(self, response):
        directives = {}
        for directive in response["Content-Security-Policy"].split(";"):
            name, *sources = directive.split()
            directives[name] = sources
        return directives

    def test_html_response_has_csp_with_request_nonce(self):
        request, response = self._call(HttpResponse("OK"))
        self.assertIn(f"'nonce-{request.csp_nonce}'", self._directives(response)["script-src"])

    def test_nonce_differs_per_request(self):
        first_request, _ = self._call(HttpResponse("OK"))
        second_request, _ = self._call(HttpResponse("OK"))
        self.assertNotEqual(first_request.csp_nonce, second_request.csp_nonce)

    def test_non_html_response_has_no_csp(self):
        _, response = self._call(JsonResponse({"result": []}))
        self.assertNotIn("Content-Security-Policy", response)

    def test_existing_csp_is_not_overwritten(self):
        existing = "default-src 'none'"
        original = HttpResponse("OK")
        original["Content-Security-Policy"] = existing
        _, response = self._call(original)
        self.assertEqual(response["Content-Security-Policy"], existing)

    @override_settings(DEBUG=True)
    def test_server_error_in_debug_has_no_csp(self):
        # DEBUG時のDjangoのエラーページはインラインスクリプトを使用している
        _, response = self._call(HttpResponse("Error", status=500))
        self.assertNotIn("Content-Security-Policy", response)

    @override_settings(DEBUG=False)
    def test_server_error_in_production_has_csp(self):
        _, response = self._call(HttpResponse("Error", status=500))
        self.assertIn("Content-Security-Policy", response)

    def test_inline_script_is_not_allowed_without_nonce(self):
        _, response = self._call(HttpResponse("OK"))
        script_src = self._directives(response)["script-src"]
        self.assertNotIn("'unsafe-inline'", script_src)
        self.assertNotIn("'unsafe-eval'", script_src)
        self.assertNotIn("*", script_src)

    def test_restrictive_directives(self):
        _, response = self._call(HttpResponse("OK"))
        directives = self._directives(response)
        self.assertEqual(directives["default-src"], ["'self'"])
        self.assertEqual(directives["object-src"], ["'none'"])
        self.assertEqual(directives["base-uri"], ["'self'"])
        self.assertEqual(directives["form-action"], ["'self'"])
        self.assertEqual(directives["frame-ancestors"], ["'none'"])


class RestrictIPMiddlewareTest(SimpleTestCase):
    """RestrictIPMiddleware のテスト（X-Forwarded-For の先頭と X-Real-IP の不一致の記録 #1189、確認用のパスへのリクエストの IP の記録 #1191）"""

    def setUp(self):
        self.factory = RequestFactory()

    def _call(self, path="/songs/1/edit", **headers):
        middleware = RestrictIPMiddleware(lambda req: HttpResponse("OK"))
        middleware.BAN_LIST = []
        request = self.factory.post(path, **headers)
        return middleware(request)

    def test_mismatch_is_logged_without_ip(self):
        with self.assertLogs("subekashi.lib.ip", level="WARNING") as logs:
            response = self._call(
                HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.1",
                HTTP_X_REAL_IP="203.0.113.1",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(logs.records), 1)
        message = logs.records[0].getMessage()
        self.assertIn("POST '/songs/1/edit'", message)
        self.assertIn("X-Forwarded-For の IP の数: 2", message)
        self.assertNotIn("198.51.100.1", message)
        self.assertNotIn("203.0.113.1", message)

    def test_newline_in_path_is_escaped(self):
        with self.assertLogs("subekashi.lib.ip", level="WARNING") as logs:
            self._call(
                path="/songs/%0d%0aX-Forwarded-For の先頭と X-Real-IP が一致しません",
                HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.1",
                HTTP_X_REAL_IP="203.0.113.1",
            )
        message = logs.records[0].getMessage()
        self.assertNotIn("\n", message)
        self.assertNotIn("\r", message)
        self.assertIn("/songs/\\r\\nX-Forwarded-For", message)

    def test_match_is_not_logged(self):
        with self.assertNoLogs("subekashi.lib.ip", level="WARNING"):
            self._call(HTTP_X_FORWARDED_FOR="203.0.113.1", HTTP_X_REAL_IP="203.0.113.1")

    def test_match_with_proxy_addresses_is_not_logged(self):
        with self.assertNoLogs("subekashi.lib.ip", level="WARNING"):
            self._call(HTTP_X_FORWARDED_FOR="203.0.113.1, 10.0.0.1", HTTP_X_REAL_IP="203.0.113.1")

    def test_without_real_ip_is_not_logged(self):
        with self.assertNoLogs("subekashi.lib.ip", level="WARNING"):
            self._call(HTTP_X_FORWARDED_FOR="198.51.100.1")

    def test_without_forwarded_for_is_not_logged(self):
        with self.assertNoLogs("subekashi.lib.ip", level="WARNING"):
            self._call(HTTP_X_REAL_IP="203.0.113.1")

    def assertNoIP(self, logs, *ips):
        for record in logs.records:
            for ip in ips:
                self.assertNotIn(ip, record.getMessage())

    def test_client_ip_check_behind_load_balancer(self):
        # 本番の前提どおり、ロードバランサーがX-Real-IPを付け直し、X-Forwarded-Forの末尾にクライアントのIPを追加した場合
        with self.assertLogs("subekashi.lib.ip", level="WARNING") as logs:
            response = self._call(
                path="/x-real-ip-check-1",
                REMOTE_ADDR="10.0.0.1",
                HTTP_X_FORWARDED_FOR="198.51.100.1, 8.8.8.8",
                HTTP_X_REAL_IP="8.8.8.8",
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "IP の確認（POST '/x-real-ip-check-1'、REMOTE_ADDR: グローバルでない、X-Real-IP: グローバル、"
            "REMOTE_ADDR と X-Real-IP が一致: False、X-Forwarded-For の IP の数: 2、"
            "X-Real-IP と X-Forwarded-For の先頭が一致: False、末尾が一致: True）",
            [record.getMessage() for record in logs.records],
        )
        self.assertNoIP(logs, "10.0.0.1", "198.51.100.1", "8.8.8.8")

    def test_client_ip_check_with_x_real_ip_from_client(self):
        # クライアントが送ったX-Real-IPがそのまま届いた場合
        with self.assertLogs("subekashi.lib.ip", level="WARNING") as logs:
            self._call(
                path="/x-real-ip-check-2",
                REMOTE_ADDR="10.0.0.1",
                HTTP_X_FORWARDED_FOR="198.51.100.1",
                HTTP_X_REAL_IP="198.51.100.1",
            )
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            [
                "IP の確認（POST '/x-real-ip-check-2'、REMOTE_ADDR: グローバルでない、X-Real-IP: グローバルでない、"
                "REMOTE_ADDR と X-Real-IP が一致: False、X-Forwarded-For の IP の数: 1、"
                "X-Real-IP と X-Forwarded-For の先頭が一致: True、末尾が一致: True）",
            ],
        )
        self.assertNoIP(logs, "10.0.0.1", "198.51.100.1")

    def test_client_ip_check_without_load_balancer(self):
        # REMOTE_ADDRがクライアントのIPになっている場合
        with self.assertLogs("subekashi.lib.ip", level="WARNING") as logs:
            self._call(path="/x-real-ip-check-3", REMOTE_ADDR="8.8.8.8", HTTP_X_REAL_IP="8.8.8.8")
        self.assertEqual(
            [record.getMessage() for record in logs.records],
            [
                "IP の確認（POST '/x-real-ip-check-3'、REMOTE_ADDR: グローバル、X-Real-IP: グローバル、"
                "REMOTE_ADDR と X-Real-IP が一致: True、X-Forwarded-For の IP の数: 0、"
                "X-Real-IP と X-Forwarded-For の先頭が一致: False、末尾が一致: False）",
            ],
        )
        self.assertNoIP(logs, "8.8.8.8")

    def test_client_ip_check_without_valid_x_real_ip(self):
        for headers, expected in [
            ({}, "X-Real-IP: なし"),
            ({"HTTP_X_REAL_IP": "not-an-ip"}, "X-Real-IP: IPでない"),
        ]:
            with self.subTest(expected=expected):
                with self.assertLogs("subekashi.lib.ip", level="WARNING") as logs:
                    self._call(path="/x-real-ip-check-4", REMOTE_ADDR="10.0.0.1", **headers)
                message = logs.records[0].getMessage()
                self.assertIn(expected, message)
                self.assertIn("REMOTE_ADDR と X-Real-IP が一致: False", message)

    def test_client_ip_check_newline_in_path_is_escaped(self):
        with self.assertLogs("subekashi.lib.ip", level="WARNING") as logs:
            self._call(path="/x-real-ip-check-%0d%0aIP の確認", REMOTE_ADDR="10.0.0.1")
        message = logs.records[0].getMessage()
        self.assertNotIn("\n", message)
        self.assertNotIn("\r", message)
        self.assertIn("'/x-real-ip-check-\\r\\nIP の確認'", message)

    def test_client_ip_check_is_not_logged_for_other_paths(self):
        with self.assertNoLogs("subekashi.lib.ip", level="WARNING"):
            self._call(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="8.8.8.8", HTTP_X_REAL_IP="8.8.8.8")
