"""
ミドルウェアのテスト

RatelimitMiddleware・CacheControlMiddleware・ContentSecurityPolicyMiddleware・RestrictIPMiddleware の動作を検証する。
"""
import json
from unittest.mock import MagicMock
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django_ratelimit.exceptions import Ratelimited
from subekashi.middleware.rate_limit import RatelimitMiddleware
from subekashi.middleware.cache import CacheControlMiddleware
from subekashi.middleware.csp import ContentSecurityPolicyMiddleware
from subekashi.middleware.restrict_ip import RestrictIPMiddleware
from subekashi.constants.constants import SHORT_TERM_COOKIE_AGE, LONG_TERM_COOKIE_AGE


class RatelimitMiddlewareTest(SimpleTestCase):
    """RatelimitMiddleware のテスト"""

    def setUp(self):
        self.factory = RequestFactory()

    def _make_middleware(self, get_response):
        return RatelimitMiddleware(get_response)

    def test_normal_request_passes_through(self):
        expected_response = HttpResponse("OK")
        middleware = self._make_middleware(lambda req: expected_response)
        request = self.factory.get("/")
        response = middleware(request)
        self.assertEqual(response, expected_response)

    def test_ratelimited_returns_429(self):
        def raise_ratelimited(req):
            raise Ratelimited()

        middleware = self._make_middleware(raise_ratelimited)
        request = self.factory.get("/")
        response = middleware(request)
        self.assertEqual(response.status_code, 429)

    def test_ratelimited_response_is_json(self):
        def raise_ratelimited(req):
            raise Ratelimited()

        middleware = self._make_middleware(raise_ratelimited)
        request = self.factory.get("/")
        response = middleware(request)
        self.assertIsInstance(response, JsonResponse)

    def test_ratelimited_response_contains_error_key(self):
        def raise_ratelimited(req):
            raise Ratelimited()

        middleware = self._make_middleware(raise_ratelimited)
        request = self.factory.get("/")
        response = middleware(request)
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Rate limit exceeded")


@override_settings(
    STATIC_URL="/static/",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
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
    """RestrictIPMiddleware のテスト（X-Forwarded-For の先頭と X-Real-IP の不一致の記録、#1189）"""

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
