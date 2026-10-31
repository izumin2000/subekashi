"""
ミドルウェアのテスト

RatelimitMiddleware・CacheControlMiddleware・ContentSecurityPolicyMiddleware・BannedEditorMiddleware の動作を検証する。
"""
import json
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qsl, quote, urlparse, urlsplit
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django_ratelimit.exceptions import Ratelimited
from subekashi.middleware.banned_editor import BannedEditorMiddleware
from subekashi.middleware.rate_limit import RatelimitMiddleware
from subekashi.middleware.cache import CacheControlMiddleware
from subekashi.middleware.csp import ContentSecurityPolicyMiddleware
from subekashi.lib.embed import get_embed
from subekashi.lib.security import encrypt
from subekashi.models import Ad, Ai, Author, AuthorAlias, Contact, Editor, History, Song, SongLink
from subekashi.constants.constants import BANNED_ERROR, SHORT_TERM_COOKIE_AGE, LONG_TERM_COOKIE_AGE


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
class BannedEditorMiddlewareTest(TestCase):
    """Editor.is_bannedがTrueの編集者は、ページの読み取り以外のリクエストができない（#1281）

    以前はban.pyのBAN_LISTにあるIPのサイト全体へのアクセスを500にしていたが、
    閲覧はできるままにして、GET・HEAD・OPTIONS以外のリクエストを止める
    """

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.editor = Editor.objects.create(ip=encrypt("127.0.0.1"), is_banned=True)
        self.author = Author.objects.create(name="BANテスト作者")
        self.song = Song.objects.create(title="BANテスト曲")
        self.song.authors.add(self.author)
        self.removed_song = Song.objects.create(title="BANテスト削除済みの曲", is_removed=True)
        self.alias = AuthorAlias.objects.create(name="BANテスト別名", author=self.author, alias_type="past")
        self.ai = Ai.objects.create(lyrics="BANテスト歌詞", score=0, genetype=Ai.GENETYPE_JANOME)
        self.ad = Ad.objects.create(url="https://youtu.be/bannedad0001")

        # ミドルウェアが止められなかったときに、実際のDiscordに送信しないようにする
        patcher = patch("subekashi.lib.discord.requests.post")
        self.mock_discord_post = patcher.start()
        self.addCleanup(patcher.stop)

        self.song_new_url = reverse("subekashi:song_new")
        self.song_edit_url = reverse("subekashi:song_edit", args=[self.song.id])
        self.aliases_url = reverse("subekashi:author_aliases", args=[self.author.id])

    def snapshot(self):
        return (
            list(Song.all_objects.order_by("pk").values_list("pk", "title", "is_removed")),
            list(Author.objects.order_by("pk").values_list("pk", "name")),
            list(AuthorAlias.objects.order_by("pk").values_list("pk", "name")),
            list(Ai.objects.order_by("pk").values_list("pk", "score")),
            list(Ad.objects.order_by("pk").values_list("pk", "click", "dup")),
            History.objects.count(),
            Contact.objects.count(),
            SongLink.objects.count(),
            Editor.objects.count(),
        )

    def referer(self, path):
        return f"http://testserver{path}"

    # 送信したフォームがあるページ → 送信先
    def form_requests(self):
        return [
            ("曲の登録", self.song_new_url, self.song_new_url, {"url": "", "authors": "BAN新規作者", "title": "BAN新規曲"}),
            ("曲の編集", self.song_edit_url, self.song_edit_url, {"title": "BAN編集後の曲", "authors": "BANテスト作者", "url": ""}),
            (
                "曲の削除", self.song_edit_url, reverse("subekashi:song_delete", args=[self.song.id]),
                {"reason": "BAN削除理由"},
            ),
            (
                "曲の削除の取り消し", reverse("subekashi:song", args=[self.removed_song.id]),
                reverse("subekashi:song_restore", args=[self.removed_song.id]), {"reason": "BAN取り消し理由"},
            ),
            (
                "別名の追加", reverse("subekashi:author_alias_new", args=[self.author.id]),
                reverse("subekashi:author_alias_new", args=[self.author.id]), {"name": "BAN新規別名", "alias_type": "past"},
            ),
            (
                "別名の編集", reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
                reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
                {"name": "BAN編集後の別名", "alias_type": "past"},
            ),
            (
                "別名の削除", reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id]),
                reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id]), {},
            ),
            (
                "名義の統一", reverse("subekashi:author_unify_name_confirm", args=[self.author.id]),
                reverse("subekashi:author_unify_name_set", args=[self.author.id]), {"name": "BANテスト別名"},
            ),
            (
                "お問い合わせ", reverse("subekashi:contact"), reverse("subekashi:contact"),
                {"category": "提案", "detail": "BAN問い合わせ"},
            ),
            (
                "宣伝", reverse("subekashi:ad"), reverse("subekashi:ad"),
                {"url1": "https://youtu.be/bannedad0002", "ad1": ""},
            ),
        ]

    def test_form_post_redirects_back_to_the_form_page_with_toast(self):
        for name, page_url, post_url, data in self.form_requests():
            with self.subTest(name=name):
                before = self.snapshot()
                response = self.client.post(post_url, data, HTTP_REFERER=self.referer(page_url))
                self.assertEqual(response.status_code, 303)
                self.assertEqual(response["Location"], f"{page_url}?toast=banned")
                self.assertEqual(self.snapshot(), before)
        self.mock_discord_post.assert_not_called()

    def test_redirected_page_can_be_opened(self):
        response = self.client.post(
            self.song_new_url, {"url": "", "authors": "BAN新規作者", "title": "BAN新規曲"},
            HTTP_REFERER=self.referer(self.song_new_url), follow=True,
        )
        self.assertEqual(response.redirect_chain, [(f"{self.song_new_url}?toast=banned", 303)])
        self.assertEqual(response.status_code, 200)

    def test_redirect_keeps_query_of_referer_except_toast(self):
        """名義の統一の確認ページのように、クエリがないと開けないページに戻せるようにする。別のトーストを出すクエリは外す"""
        confirm_url = reverse("subekashi:author_unify_name_confirm", args=[self.author.id])
        response = self.client.post(
            reverse("subekashi:author_unify_name_set", args=[self.author.id]), {"name": "BANテスト別名"},
            HTTP_REFERER=self.referer(f"{confirm_url}?name=BANテスト別名&toast=unified&name_unified=1&empty=#top"),
        )
        self.assertEqual(response.status_code, 303)
        location = urlsplit(response["Location"])
        self.assertEqual(location.path, confirm_url)
        self.assertEqual(parse_qsl(location.query, keep_blank_values=True), [("name", "BANテスト別名"), ("empty", ""), ("toast", "banned")])
        self.assertEqual(location.fragment, "")

    def test_redirect_to_unify_confirm_page_can_be_opened(self):
        confirm_url = reverse("subekashi:author_unify_name_confirm", args=[self.author.id])
        response = self.client.post(
            reverse("subekashi:author_unify_name_set", args=[self.author.id]), {"name": "BANテスト別名"},
            HTTP_REFERER=self.referer(f"{confirm_url}?name={quote('BANテスト別名')}"), follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(urlsplit(response.redirect_chain[-1][0]).path, confirm_url)

    def test_form_post_without_referer_shows_500_page(self):
        for name, _, post_url, data in self.form_requests():
            with self.subTest(name=name):
                before = self.snapshot()
                response = self.client.post(post_url, data)
                self.assertEqual(response.status_code, 500)
                self.assertTemplateUsed(response, "subekashi/500.html")
                self.assertEqual(self.snapshot(), before)
        self.mock_discord_post.assert_not_called()

    def test_referer_of_other_site_is_not_used(self):
        for referer in [
            "https://example.com/songs/new/",
            "http://testserver.example.com/songs/new/",
            "http://testserver@example.com/songs/new/",
            "//example.com/songs/new/",
            "javascript:alert(1)",
        ]:
            with self.subTest(referer=referer):
                response = self.client.post(self.song_new_url, {"title": "BAN新規曲"}, HTTP_REFERER=referer)
                self.assertEqual(response.status_code, 500)
                self.assertTemplateUsed(response, "subekashi/500.html")

    def test_referer_of_admin_site_is_not_used(self):
        response = self.client.post(
            self.song_new_url, {"title": "BAN新規曲"}, HTTP_REFERER=self.referer("/admin/subekashi/song/"),
        )
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, "subekashi/500.html")

    def test_admin_site_post_is_blocked(self):
        response = self.client.post("/admin/login/", {"username": "admin", "password": "password"})
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, "subekashi/500.html")

    def api_requests(self):
        json_type = "application/json"
        return [
            ("単語の入れ替え", "post", "/api/ai/swap/", {"base_id": self.ai.id, "token_index": 0, "candidate": "あ"}, json_type),
            ("作成歌詞の評価", "put", f"/api/ai/{self.ai.id}/", {"score": 5}, json_type),
            ("作成歌詞の評価（PATCH）", "patch", f"/api/ai/{self.ai.id}/", {"score": 5}, json_type),
            ("宣伝のクリック", "put", f"/api/ad/{self.ad.id}/", {"click": 5}, json_type),
            ("設定の保存", "post", "/api/setting/save/", {"cookies": {"theme": "dark"}}, json_type),
            ("公開の設定", "put", "/api/editor/is_open", {"ip": "a" * 30, "is_open": False}, json_type),
            ("ニュースの登録", "post", "/api/news/", {"article_id": "ban-news", "title": "BANニュース"}, json_type),
            ("曲の削除（API）", "delete", f"/api/song/{self.song.id}/", None, json_type),
            ("曲の作成（API）", "post", "/api/song/", {"title": "BAN API曲"}, json_type),
            ("お問い合わせ（API）", "post", "/api/contact/", {"category": "提案", "detail": "BAN"}, json_type),
        ]

    def test_api_request_other_than_get_returns_403(self):
        for name, method, url, data, content_type in self.api_requests():
            with self.subTest(name=name):
                before = self.snapshot()
                kwargs = {"content_type": content_type}
                if data is not None:
                    kwargs["data"] = json.dumps(data)
                response = getattr(self.client, method)(url, **kwargs)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {"detail": BANNED_ERROR})
                self.assertEqual(len(response.cookies), 0)
                self.assertEqual(self.snapshot(), before)
        self.mock_discord_post.assert_not_called()

    def test_read_requests_are_allowed(self):
        pages = [
            reverse("subekashi:top"),
            reverse("subekashi:song", args=[self.song.id]),
            self.song_new_url,
            self.song_edit_url,
            self.aliases_url,
            reverse("subekashi:contact"),
            reverse("subekashi:ad"),
        ]
        for url in pages:
            for method in ("get", "head"):
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 200)

    def test_api_get_and_options_are_allowed(self):
        self.assertEqual(self.client.get(f"/api/song/{self.song.id}/").status_code, 200)
        self.assertEqual(self.client.options("/api/song/").status_code, 200)

    def test_search_post_is_allowed(self):
        """/songs/ へのPOSTは、検索条件のCookieを保存して検索結果のページを返すだけ（DBに保存しない）"""
        response = self.client.post(reverse("subekashi:songs"), {"categorys": "song"})
        self.assertEqual(response.status_code, 200)

    def test_unbanned_editor_can_post(self):
        self.editor.is_banned = False
        self.editor.save()
        response = self.client.post(self.song_new_url, {"url": "", "authors": "BAN解除作者", "title": "BAN解除曲"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Song.objects.filter(title="BAN解除曲").exists())

    def test_ban_of_another_editor_does_not_block(self):
        self.editor.ip = encrypt("203.0.113.1")
        self.editor.save()
        response = self.client.post(self.song_new_url, {"url": "", "authors": "別の編集者作者", "title": "別の編集者曲"})
        self.assertEqual(response.status_code, 302)

    def test_ip_without_editor_is_not_banned_and_no_editor_is_created(self):
        get_response = MagicMock(return_value=HttpResponse("OK"))
        middleware = BannedEditorMiddleware(get_response)
        count = Editor.objects.count()

        response = middleware(self.factory.post("/songs/new/", REMOTE_ADDR="203.0.113.9"))

        self.assertEqual(response.content, b"OK")
        get_response.assert_called_once()
        self.assertEqual(Editor.objects.count(), count)

    def test_view_is_not_called_when_blocked(self):
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                get_response = MagicMock()
                middleware = BannedEditorMiddleware(get_response)
                request = getattr(self.factory, method)(
                    "/songs/new/", REMOTE_ADDR="127.0.0.1", HTTP_REFERER=self.referer("/songs/new/"),
                )
                response = middleware(request)
                get_response.assert_not_called()
                self.assertEqual(response.status_code, 303)

    def test_view_is_called_for_read_methods(self):
        for method in ("get", "head", "options"):
            with self.subTest(method=method):
                get_response = MagicMock(return_value=HttpResponse("OK"))
                middleware = BannedEditorMiddleware(get_response)
                request = getattr(self.factory, method)("/songs/new/", REMOTE_ADDR="127.0.0.1")
                self.assertEqual(middleware(request).content, b"OK")
                get_response.assert_called_once()

    def test_x_real_ip_of_banned_editor_is_blocked(self):
        self.editor.ip = encrypt("203.0.113.1")
        self.editor.save()
        response = self.client.post(
            self.song_new_url, {"title": "BAN新規曲"}, HTTP_X_REAL_IP="203.0.113.1", HTTP_REFERER=self.referer(self.song_new_url),
        )
        self.assertEqual(response.status_code, 303)

    def test_x_forwarded_for_does_not_bypass_ban(self):
        """X-Forwarded-Forは自由に付けられるため、BANされたIPがこれを付けても回避できない（#1189）"""
        response = self.client.post(
            self.song_new_url, {"title": "BAN新規曲"}, HTTP_X_FORWARDED_FOR="203.0.113.1", HTTP_REFERER=self.referer(self.song_new_url),
        )
        self.assertEqual(response.status_code, 303)

    def test_x_forwarded_for_of_banned_ip_does_not_block_others(self):
        self.editor.ip = encrypt("203.0.113.1")
        self.editor.save()
        response = self.client.post(
            self.song_new_url, {"url": "", "authors": "XFF作者", "title": "XFF曲"}, HTTP_X_FORWARDED_FOR="203.0.113.1",
        )
        self.assertEqual(response.status_code, 302)
