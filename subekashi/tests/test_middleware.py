"""
ミドルウェアのテスト

RatelimitMiddleware・CacheControlMiddleware・ContentSecurityPolicyMiddleware・RestrictIPMiddleware の動作を検証する。
"""
import json
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django_ratelimit.exceptions import Ratelimited
from subekashi.middleware.rate_limit import RatelimitMiddleware
from subekashi.middleware.cache import CacheControlMiddleware
from subekashi.middleware.csp import ContentSecurityPolicyMiddleware
from subekashi.lib.embed import get_embed
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

    def test_embed_origins_are_allowed_in_frame_src(self):
        # 曲ページの埋め込みプレイヤー（#1254）のiframeのoriginは、frame-srcに無いとCSPでブロックされる
        urls = [
            "https://youtu.be/dQw4w9WgXcQ",
            "https://nicovideo.jp/watch/sm1",
            "https://soundcloud.com/artist/track-name",
            "https://soundcloud.com/artist/sets/album-name",
            "https://bilibili.com/video/BV1qV411J7Kq",
            "https://drive.google.com/file/d/1aB-cD_eF2gH/view",
            "https://scratch.mit.edu/projects/123456789",
        ]
        _, response = self._call(HttpResponse("OK"))
        frame_src = self._directives(response)["frame-src"]
        for url in urls:
            with self.subTest(url=url):
                parsed_src = urlparse(get_embed(url)["src"])
                self.assertIn(f"{parsed_src.scheme}://{parsed_src.netloc}", frame_src)

    def test_restrictive_directives(self):
        _, response = self._call(HttpResponse("OK"))
        directives = self._directives(response)
        self.assertEqual(directives["default-src"], ["'self'"])
        self.assertEqual(directives["object-src"], ["'none'"])
        self.assertEqual(directives["base-uri"], ["'self'"])
        self.assertEqual(directives["form-action"], ["'self'"])
        self.assertEqual(directives["frame-ancestors"], ["'none'"])


@override_settings(STORAGES=STATIC_STORAGE)
class RestrictIPMiddlewareTest(TestCase):
    """RestrictIPMiddleware のテスト（BAN の判定に X-Real-IP を使う #1189）"""

    def setUp(self):
        self.factory = RequestFactory()

    def _call(self, remote_addr="10.0.0.1", **headers):
        middleware = RestrictIPMiddleware(lambda req: HttpResponse("OK"))
        middleware.BAN_LIST = ["203.0.113.1"]
        request = self.factory.get("/", REMOTE_ADDR=remote_addr, **headers)
        return middleware(request)

    def test_banned_x_real_ip_is_restricted(self):
        self.assertEqual(self._call(HTTP_X_REAL_IP="203.0.113.1").status_code, 500)

    def test_not_banned_x_real_ip_is_not_restricted(self):
        self.assertEqual(self._call(HTTP_X_REAL_IP="203.0.113.2").status_code, 200)

    def test_x_forwarded_for_does_not_bypass_ban(self):
        # BANされた利用者がX-Forwarded-Forで別のIPを名乗っても回避できない
        response = self._call(HTTP_X_REAL_IP="203.0.113.1", HTTP_X_FORWARDED_FOR="198.51.100.1")
        self.assertEqual(response.status_code, 500)

    def test_x_forwarded_for_of_banned_ip_is_not_restricted(self):
        # X-Forwarded-ForでBANされたIPを名乗っても、別の利用者は制限されない
        response = self._call(HTTP_X_REAL_IP="198.51.100.1", HTTP_X_FORWARDED_FOR="203.0.113.1")
        self.assertEqual(response.status_code, 200)

    def test_banned_remote_addr_without_x_real_ip_is_restricted(self):
        self.assertEqual(self._call(remote_addr="203.0.113.1").status_code, 500)
