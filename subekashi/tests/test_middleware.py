"""
ミドルウェアのテスト

RatelimitMiddleware・CacheControlMiddleware・ContentSecurityPolicyMiddleware の動作を検証する。
"""
import json
from unittest.mock import MagicMock
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django_ratelimit.exceptions import Ratelimited
from subekashi.middleware.rate_limit import RatelimitMiddleware
from subekashi.middleware.cache import CacheControlMiddleware
from subekashi.middleware.csp import ContentSecurityPolicyMiddleware
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
