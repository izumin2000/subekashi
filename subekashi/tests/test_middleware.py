"""
ミドルウェアのテスト

RatelimitMiddleware・CacheControlMiddleware の動作を検証する。
"""
from unittest.mock import MagicMock
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django_ratelimit.exceptions import Ratelimited
from subekashi.middleware.rate_limit import RatelimitMiddleware
from subekashi.middleware.cache import CacheControlMiddleware
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
        import json

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
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
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
