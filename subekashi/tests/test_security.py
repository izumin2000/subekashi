"""
ZAP診断に基づくセキュリティ対策（#1126）のテスト

CSP・CORS・CSRFトークンの扱い・サブリソース整合性（SRI）を検証する。
"""
import re
from pathlib import Path
from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from subekashi.models import Ai, Song


STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# 開始タグ内のonclick等のイベントハンドラ属性（タグが複数行にまたがる場合も検出する）
INLINE_EVENT_HANDLER_PATTERN = re.compile(r"<[a-zA-Z][^>]*\son[a-z]+\s*=", re.IGNORECASE)
SCRIPT_TAG_PATTERN = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)
CSRF_TOKEN_PATTERN = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')


def get_nonce(response):
    match = re.search(r"'nonce-([^']+)'", response["Content-Security-Policy"])
    return match.group(1)


@override_settings(STORAGES=STATIC_STORAGE)
class ContentSecurityPolicyIntegrationTest(TestCase):
    """各ページにCSPが付与され、インラインスクリプトにnonceが付いていることのテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="CSPテスト曲", lyrics="歌詞")

    def _pages(self):
        return [
            reverse("subekashi:top"),
            reverse("subekashi:songs"),
            reverse("subekashi:song", args=[self.song.id]),
            reverse("subekashi:song_new"),
            reverse("subekashi:song_edit", args=[self.song.id]),
            reverse("subekashi:setting"),
            reverse("subekashi:ai"),
            reverse("subekashi:ai_result"),
            reverse("subekashi:contact"),
            reverse("subekashi:ad"),
            reverse("subekashi:stats"),
            reverse("article:articles"),
        ]

    def test_html_pages_have_csp_header(self):
        for url in self._pages():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn("Content-Security-Policy", response)

    def test_inline_scripts_have_nonce_matching_header(self):
        for url in self._pages():
            with self.subTest(url=url):
                response = self.client.get(url)
                nonce = get_nonce(response)
                for attrs in SCRIPT_TAG_PATTERN.findall(response.content.decode()):
                    # src付きの外部スクリプトとjson_scriptのデータブロックはnonce不要
                    if "src=" in attrs or 'type="application/json"' in attrs:
                        continue
                    self.assertIn(f'nonce="{nonce}"', attrs)

    def test_rendered_pages_have_no_inline_event_handlers(self):
        for url in self._pages():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIsNone(INLINE_EVENT_HANDLER_PATTERN.search(response.content.decode()))

    def test_api_json_response_has_no_csp_header(self):
        response = self.client.get(reverse("subekashi:song-detail", args=[self.song.id]), {"format": "json"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Content-Security-Policy", response)


class InlineEventHandlerSourceTest(TestCase):
    """CSPでインラインのイベントハンドラ属性を許可していないため、テンプレート・JSで使用していないことのテスト"""

    def _source_files(self):
        base_dir = Path(settings.BASE_DIR)
        for app in ("subekashi", "article"):
            yield from (base_dir / app / "templates").rglob("*.html")
            yield from (base_dir / app / "static").rglob("*.js")

    def test_no_inline_event_handler_attributes(self):
        for path in self._source_files():
            with self.subTest(path=str(path)):
                content = path.read_text(encoding="utf-8")
                self.assertIsNone(INLINE_EVENT_HANDLER_PATTERN.search(content))


@override_settings(STORAGES=STATIC_STORAGE)
class CorsTest(TestCase):
    """CORSヘッダーがAPIのみに付与され、認証情報付きリクエストを許可しないことのテスト"""

    ORIGIN = "https://example.com"

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="CORSテスト曲")

    def test_api_allows_any_origin(self):
        response = self.client.get(reverse("subekashi:song-list"), {"format": "json"}, HTTP_ORIGIN=self.ORIGIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")

    def test_api_does_not_allow_credentials(self):
        response = self.client.get(reverse("subekashi:song-list"), {"format": "json"}, HTTP_ORIGIN=self.ORIGIN)
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_api_preflight_is_allowed(self):
        response = self.client.options(
            reverse("subekashi:song-list"),
            HTTP_ORIGIN=self.ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")

    def test_html_page_has_no_cors_headers(self):
        for url in [reverse("subekashi:top"), reverse("subekashi:songs"), reverse("subekashi:song", args=[self.song.id])]:
            with self.subTest(url=url):
                response = self.client.get(url, HTTP_ORIGIN=self.ORIGIN)
                self.assertNotIn("Access-Control-Allow-Origin", response)
                self.assertNotIn("Access-Control-Allow-Credentials", response)


@override_settings(STORAGES=STATIC_STORAGE)
class CsrfTokenTest(TestCase):
    """csrftokenクッキーをHttpOnlyにし、JSはページ内のトークンを使うことのテスト"""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_csrf_cookie_is_httponly(self):
        response = self.client.get(reverse("subekashi:song_new"))
        self.assertTrue(response.cookies["csrftoken"]["httponly"])

    def test_pages_using_get_csrf_have_csrf_token(self):
        # base.jsのgetCSRF()を呼ぶページには{% csrf_token %}が必要
        for url in [reverse("subekashi:top"), reverse("subekashi:songs"), reverse("subekashi:setting"), reverse("subekashi:ai_result")]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRegex(response.content.decode(), CSRF_TOKEN_PATTERN)

    def test_save_setting_succeeds_with_token_in_page(self):
        response = self.client.get(reverse("subekashi:setting"))
        token = CSRF_TOKEN_PATTERN.search(response.content.decode()).group(1)

        response = self.client.post(
            reverse("subekashi:save_settings"),
            data='{"cookies": {"brlyrics": "pack"}}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["brlyrics"].value, "pack")

    def test_save_setting_fails_without_token(self):
        self.client.get(reverse("subekashi:setting"))

        response = self.client.post(
            reverse("subekashi:save_settings"),
            data='{"cookies": {"brlyrics": "pack"}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_ai_get_form_has_no_csrf_token(self):
        # GETフォームにcsrf_tokenがあるとトークンがURLに含まれてしまう
        response = self.client.get(reverse("subekashi:ai"))
        self.assertNotContains(response, "csrfmiddlewaretoken")

    def test_ai_result_has_csrf_token_for_score(self):
        Ai.objects.create(lyrics="りんご", score=0, genetype="janome")
        response = self.client.get(reverse("subekashi:ai_result"))
        self.assertContains(response, 'data-score="1"')
        self.assertRegex(response.content.decode(), CSRF_TOKEN_PATTERN)


@override_settings(STORAGES=STATIC_STORAGE)
class SubresourceIntegrityTest(TestCase):
    """外部CDNから読み込むスタイルシートにintegrity属性が付いていることのテスト"""

    def test_font_awesome_has_integrity(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(
            response,
            'href="https://use.fontawesome.com/releases/v5.15.4/css/all.css" '
            'integrity="sha384-DyZ88mC6Up2uqS4h/KRgHuoeGwBcD4Ng9SiP4dIRy0EXTlnuz47vAwmeGwVChigm" crossorigin="anonymous"',
        )
