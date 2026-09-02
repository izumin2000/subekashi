"""
ビューの HTTP レスポンステスト

各ページの基本的なアクセス可否・ステータスコード・リダイレクト先を検証する。
ManifestStaticFilesStorage はテストに不要なため StaticFilesStorage に差し替える。
"""
import re
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch, MagicMock
from django.db import connection
from django.test import TestCase, Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from article.models import Article
from subekashi.forms import AuthorAliasForm
from subekashi.models import Ad, Ai, Author, AuthorAlias, AuthorLink, Contact, Editor, History, Song, Stats, Word
from subekashi.models.author import TransitiveAlias


STATIC_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class TopViewTest(TestCase):
    """TopView (/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertEqual(response.status_code, 200)

    def test_created_lyrics_shows_high_scored_janome(self):
        Ai.objects.create(lyrics="作成された歌詞サンプル", score=5, genetype="janome")

        response = self.client.get(reverse("subekashi:top"))

        self.assertContains(response, "作成された歌詞サンプル")

    def test_created_lyrics_excludes_legacy_model_genetype(self):
        # レガシーのGPTインポート（genetype="model"）は廃止されたため、
        # スコア5であっても「作成された歌詞」には表示されない
        Ai.objects.create(lyrics="レガシー歌詞", score=5, genetype="model")

        response = self.client.get(reverse("subekashi:top"))

        self.assertNotContains(response, "レガシー歌詞")

    def test_news_tag_article_has_no_link(self):
        """tag=newsかつhandle_as_news=Falseの記事はリンクされずタイトルのみ表示される"""
        Article.objects.create(
            article_id="news-1", title="通常ニュース", tag="news",
            post_time=timezone.now(), is_open=True,
        )
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, "<span>通常ニュース</span>")

    def test_release_tag_article_has_link(self):
        """tag=releaseの記事はDefaultArticleViewへのリンクでタイトル全体がくくられる"""
        article = Article.objects.create(
            article_id="release-1", title="リリース記事", tag="release",
            post_time=timezone.now(), is_open=True,
        )
        response = self.client.get(reverse("subekashi:top"))
        url = reverse("article:default_article", args=[article.article_id])
        self.assertContains(response, f"<span><a href='{url}'>リリース記事</a></span>")

    def test_handle_as_news_article_has_link(self):
        """handle_as_news=Trueの記事はtagに関わらずDefaultArticleViewへのリンクでタイトル全体がくくられる"""
        article = Article.objects.create(
            article_id="blog-as-news", title="ニュース扱いブログ", tag="blog",
            post_time=timezone.now(), is_open=True, handle_as_news=True,
        )
        response = self.client.get(reverse("subekashi:top"))
        url = reverse("article:default_article", args=[article.article_id])
        self.assertContains(response, f"<span><a href='{url}'>ニュース扱いブログ</a></span>")

    def test_news_tag_with_handle_as_news_has_link(self):
        """tag=newsでもhandle_as_news=Trueならリンクされる"""
        article = Article.objects.create(
            article_id="news-as-news", title="扱い指定ニュース", tag="news",
            post_time=timezone.now(), is_open=True, handle_as_news=True,
        )
        response = self.client.get(reverse("subekashi:top"))
        url = reverse("article:default_article", args=[article.article_id])
        self.assertContains(response, f"<span><a href='{url}'>扱い指定ニュース</a></span>")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongsViewTest(TestCase):
    """SongsView (/songs/) のテスト"""

    def setUp(self):
        self.client = Client()
        Song.objects.create(title="検索テスト曲", lyrics="歌詞")

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(response.status_code, 200)

    def test_keyword_search_returns_200(self):
        response = self.client.get(reverse("subekashi:songs"), {"keyword": "テスト"})
        self.assertEqual(response.status_code, 200)

    def test_invalid_page_returns_200(self):
        response = self.client.get(reverse("subekashi:songs"), {"page": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_pagination_params_return_200(self):
        response = self.client.get(reverse("subekashi:songs"), {"page": "1", "size": "10"})
        self.assertEqual(response.status_code, 200)

    def test_bool_query_param_true_uppercase_sets_context(self):
        """is_draft=True (大文字) でチェックボックスが有効になること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "True"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_draft"])

    def test_bool_query_param_1_sets_context(self):
        """is_draft=1 でチェックボックスが有効になること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_draft"])

    def test_bool_query_param_false_uppercase_sets_context(self):
        """is_draft=False (大文字) でチェックボックスが無効になること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "False"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_draft"])

    def test_is_joke_true_sets_jokerange_only(self):
        """is_joke=True でjokerangeがonlyになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "True"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "only")

    def test_is_joke_only_sets_jokerange_only(self):
        """is_joke=only でjokerangeがonlyになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "only"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "only")

    def test_is_joke_false_sets_jokerange_off(self):
        """is_joke=False でjokerangeがoffになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "False"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "off")

    def test_is_joke_off_sets_jokerange_off(self):
        """is_joke=off でjokerangeがoffになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "off"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "off")

    def test_is_joke_all_sets_jokerange_on(self):
        """is_joke=all でjokerangeがonになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "all"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "on")

    def test_is_joke_on_sets_jokerange_on(self):
        """is_joke=on でjokerangeがonになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "on"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "on")

    def test_bool_query_params_all_fields(self):
        """is_original/is_inst/is_questionable でもTrue/Falseが正しく変換されること"""
        for field in ["is_original", "is_inst", "is_questionable"]:
            with self.subTest(field=field):
                response = self.client.get(reverse("subekashi:songs"), {field: "True"})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context[field])

    def test_is_subeana_query_param_does_not_overwrite_saved_songrange_cookie(self):
        """曲詳細ページのタグリンク(is_subeana)経由の絞り込みでsearch_songrange cookieが上書きされないこと"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_songrange"] = "subeana"
        response = self.client.get(reverse("subekashi:songs"), {"is_subeana": "xx"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["songrange"], "xx")
        self.assertNotIn("search_songrange", response.cookies)

    def test_is_joke_query_param_does_not_overwrite_saved_jokerange_cookie(self):
        """曲詳細ページのタグリンク(is_joke)経由の絞り込みでsearch_jokerange cookieが上書きされないこと"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_jokerange"] = "on"
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "only"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "only")
        self.assertNotIn("search_jokerange", response.cookies)

    def test_songrange_query_param_still_saves_cookie(self):
        """検索フォーム経由(songrange)の変更は引き続きcookieに保存されること"""
        self.client.cookies["is_saved_select"] = "on"
        response = self.client.get(reverse("subekashi:songs"), {"songrange": "xx"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["search_songrange"].value, "xx")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongViewTest(TestCase):
    """SongView (/songs/<id>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="詳細テスト曲", lyrics="歌詞")

    def test_existing_song_returns_200(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_song_title_appears_in_response(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, "詳細テスト曲")

    def test_questionable_tag_appears_when_is_questionable(self):
        self.song.is_questionable = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, "界隈曲?")

    def test_questionable_tag_not_shown_by_default(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertNotContains(response, "界隈曲?")

    def test_noindex_not_shown_by_default(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertNotContains(response, 'name="robots"')

    def test_noindex_shown_when_is_questionable(self):
        self.song.is_questionable = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')

    def test_noindex_shown_when_is_limited(self):
        self.song.is_limited = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongNewViewTest(TestCase):
    """SongNewView (/songs/new/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_new"))
        self.assertEqual(response.status_code, 200)

    def test_post_non_youtube_url_returns_error(self):
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://example.com/video", "authors": "テスト作者", "title": "テスト曲"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("YouTube", response.context["error"])

    def test_post_empty_authors_returns_error(self):
        # URL なし・作者空白 → 作者バリデーションエラー
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "  ", "title": "テスト曲"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("作者", response.context["error"])

    def test_post_empty_title_returns_error(self):
        # URL なし・作者あり・タイトル空白 → タイトルバリデーションエラー
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "テスト作者", "title": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("タイトル", response.context["error"])

    def test_post_title_over_max_length_returns_error(self):
        # #1085: SongNewViewはフォームを経由せずtitleを保存するため、
        # 直接バリデーションが必要（MySQL移行時のData too long for column対策）
        max_length = Song._meta.get_field("title").max_length
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "テスト作者", "title": "あ" * (max_length + 1)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("タイトル", response.context["error"])
        self.assertFalse(Song.objects.filter(title__startswith="あ" * 10).exists())

    def test_post_author_name_over_max_length_returns_error(self):
        # #1085: MySQL移行時のData too long for column対策
        max_length = Author._meta.get_field("name").max_length
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "い" * (max_length + 1), "title": "長い作者名テスト曲"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("作者名", response.context["error"])
        self.assertFalse(Song.objects.filter(title="長い作者名テスト曲").exists())

    def test_post_questionable_forces_original_false(self):
        # is-questionable時、オリジナル模倣はユーザーの入力値に関わらず強制的にFalseになる
        response = self.client.post(
            reverse("subekashi:song_new"),
            {
                "url": "",
                "authors": "界隈曲テスト作者",
                "title": "界隈曲テスト曲",
                "is-questionable-manual": "on",
                "is-original-manual": "on",
                "is-subeana-manual": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        song = Song.objects.get(title="界隈曲テスト曲")
        self.assertTrue(song.is_questionable)
        self.assertFalse(song.is_original)
        self.assertTrue(song.is_subeana)

    def test_post_with_past_alias_author_name_normalizes_and_flags_toast(self):
        # 入力した作者名がpast別名と一致する場合、一番有名な名義に正規化されて
        # 保存される。redirect先のURLにその旨を伝えるtoast用のフラグが付与される
        primary_author = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=primary_author, alias_type="past")

        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "以前の名義", "title": "正規化テスト曲"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("primary_name_normalized=1", response.url)
        song = Song.objects.get(title="正規化テスト曲")
        self.assertIn(primary_author, song.authors.all())

    def test_post_without_normalization_does_not_flag_toast(self):
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "正規化されない作者", "title": "通常テスト曲"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("primary_name_normalized", response.url)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongEditViewTest(TestCase):
    """SongEditView (/songs/<id>/edit/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="編集テスト曲")

    def test_existing_song_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_edit", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song_edit", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_post_author_name_over_max_length_returns_error(self):
        # #1085: MySQL移行時のData too long for column対策
        max_length = Author._meta.get_field("name").max_length
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "う" * (max_length + 1), "url": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("作者名", response.context["error"])

    def test_post_author_name_error_escapes_html_in_response(self):
        # コードレビュー指摘対応（反射型XSS）: song_edit.html側は{{ error|safe }}で
        # オートエスケープが無効化されているため、エラーメッセージに含まれる作者名は
        # view側で明示的にエスケープされていないと、HTMLタグを注入できてしまう
        max_length = Author._meta.get_field("name").max_length
        malicious_name = "<script>alert(1)</script>" * (max_length // 20 + 1)
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": malicious_name, "url": ""},
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)

    def test_post_untrusted_url_error_escapes_html_in_response(self):
        # コードレビュー指摘対応（反射型XSS）: 「信頼されていないURL」エラーは
        # cleaned_url_itemをそのままHTMLとして埋め込んでいたため、URLにHTMLタグを
        # 含めるとscriptタグを注入できてしまっていた
        malicious_url = "https://example.com/<script>alert(1)</script>"
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "テスト作者", "url": malicious_url},
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)

    def test_post_reject_list_error_escapes_html_in_response(self):
        # コードレビュー指摘対応（反射型XSS）: check_reject_list()が返すエラーメッセージには
        # author.nameがそのまま含まれるため、HTMLタグを含む名前がREJECT_LISTに一致した
        # 場合にview側でエスケープしていないとXSSになりうる
        malicious_name = "<script>alert(1)</script>"
        mock_reject_module = MagicMock()
        mock_reject_module.REJECT_LIST = [malicious_name]
        with patch.dict("sys.modules", {"subekashi.constants.dynamic.reject": mock_reject_module}):
            response = self.client.post(
                reverse("subekashi:song_edit", args=[self.song.id]),
                {"title": "編集テスト曲", "authors": malicious_name, "url": ""},
            )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)

    def test_post_questionable_forces_lyrics_and_imitate_blank(self):
        # is_questionable時、歌詞・模倣・下書きはユーザー入力に関わらず空/OFFになる
        imitate_target = Song.objects.create(title="模倣元テスト曲")
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "",
                "imitate": str(imitate_target.id),
                "lyrics": "本来は保存されないはずの歌詞",
                "is_questionable": True,
                "is_draft": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.song.refresh_from_db()
        self.assertTrue(self.song.is_questionable)
        self.assertEqual(self.song.lyrics, "")
        self.assertFalse(self.song.is_draft)
        self.assertNotIn(imitate_target, self.song.imitates.all())

    def test_post_questionable_honors_deleted_joke_inst_subeana_but_forces_original_false(self):
        # is_questionable時、非公開/削除済み・ネタ曲・インスト・すべあな界隈曲の入力値は保存されるが、
        # オリジナル模倣は入力値に関わらず強制的にFalseになる
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "",
                "imitate": "",
                "lyrics": "",
                "is_questionable": True,
                "is_original": True,
                "is_deleted": True,
                "is_joke": True,
                "is_inst": True,
                "is_subeana": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.song.refresh_from_db()
        self.assertTrue(self.song.is_questionable)
        self.assertFalse(self.song.is_original)
        self.assertTrue(self.song.is_deleted)
        self.assertTrue(self.song.is_joke)
        self.assertTrue(self.song.is_inst)
        self.assertTrue(self.song.is_subeana)

    def test_post_with_past_alias_author_name_normalizes_and_flags_toast(self):
        primary_author = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=primary_author, alias_type="past")

        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "以前の名義", "url": "", "imitate": "", "lyrics": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("primary_name_normalized=1", response.url)
        self.song.refresh_from_db()
        self.assertIn(primary_author, self.song.authors.all())

    def test_post_without_normalization_does_not_flag_toast(self):
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "正規化されない作者", "url": "", "imitate": "", "lyrics": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("primary_name_normalized", response.url)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongHistoryViewTest(TestCase):
    """SongHistoryView (/songs/<id>/history/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="履歴テスト曲")

    def test_existing_song_returns_200(self):
        response = self.client.get(reverse("subekashi:song_history", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song_history", args=[99999]))
        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongDeleteViewTest(TestCase):
    """SongDeleteView (/songs/<id>/delete/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="削除申請テスト曲")

    def test_existing_song_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_delete", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song_delete", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_post_valid_reason_redirects(self):
        # SEND_DISCORD=False のため send_discord は即 True を返す
        response = self.client.post(
            reverse("subekashi:song_delete", args=[self.song.id]),
            {"reason": "削除理由テスト"},
        )
        self.assertRedirects(
            response,
            f"/songs/{self.song.id}?toast=delete",
            fetch_redirect_response=False,
        )

    def test_post_empty_reason_returns_error(self):
        response = self.client.post(
            reverse("subekashi:song_delete", args=[self.song.id]),
            {"reason": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class EditorViewTest(TestCase):
    """EditorView (/editor/<id>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.editor = Editor.objects.create(ip="127.0.0.4", is_open=True)

    def test_existing_editor_returns_200(self):
        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]))
        self.assertEqual(response.status_code, 200)

    def test_author_history_links_to_author_page_not_deleted_message(self):
        author = Author.objects.create(name="編集者履歴テスト作者")
        History.create_for_author(
            author=author, title="別名を追加", history_type="edit", changes=None, editor=self.editor,
        )

        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]))

        self.assertContains(response, "編集者履歴テスト作者")
        self.assertNotContains(response, "この曲は削除されました")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorViewTest(TestCase):
    """AuthorView (/authors/<id>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="ビューテスト作者")
        song = Song.objects.create(title="作者ビューテスト曲")
        song.authors.add(self.author)

    def test_existing_author_returns_200(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(reverse("subekashi:author", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_author_name_appears_in_response(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "ビューテスト作者")

    def test_alias_link_present_without_count_when_no_aliases(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertNotContains(response, "件の別名")

    def test_alias_link_has_icon(self):
        # 別名ボタンにfa-people-arrowsアイコンを表示する（#1024）
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "fa-people-arrows")

    def test_alias_count_shown_when_forward_alias_exists(self):
        AuthorAlias.objects.create(name="件数テスト別名", author=self.author, alias_type="past")
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "1件の別名")

    def test_alias_count_includes_reverse_aliases(self):
        target = Author.objects.create(name="件数逆方向対象")
        AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "1件の別名")

    def test_alias_count_reflects_transitive_count(self):
        # 件数表示はget_transitive_aliases()（#1005）の件数に合わせる（#1007）。
        # 自分から見て1ホップ(past)先の別名がさらに別名(spell)を持つ場合、
        # 2ホップ先の別名も件数に含まれる
        middle = Author.objects.create(name="件数中継作者")
        AuthorAlias.objects.create(name=middle.name, author=self.author, alias_type="past")
        AuthorAlias.objects.create(name="件数先端別名", author=middle, alias_type="spell")

        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))

        self.assertContains(response, "2件の別名")

    def test_stats_link_present(self):
        # 統計ページへのdummybuttonが別名ボタンの右に追加される（#334）
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, reverse("subekashi:author_stats", args=[self.author.id]))

    def test_stats_link_has_icon(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "fa-chart-line")

    def test_stats_summary_shows_kenreki(self):
        # view=1234は1,20,50,100,200,500,1000の7段階に到達 -> 7pt -> 7//2=3鍵
        Song.objects.filter(title="作者ビューテスト曲").update(view=1234)
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, 'id="author-stats-summary"')
        self.assertEqual(response.context["kenreki"]["key_count"], 3)

    def test_stats_summary_hidden_when_author_has_no_songs(self):
        no_song_author = Author.objects.create(name="曲の無い作者")
        response = self.client.get(reverse("subekashi:author", args=[no_song_author.id]))
        self.assertIsNone(response.context["kenreki"])
        self.assertNotContains(response, 'id="author-stats-summary"')


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class StatsViewTest(TestCase):
    """StatsView (/stats/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:stats"))
        self.assertEqual(response.status_code, 200)

    def test_no_songs_hides_all_stat_items(self):
        response = self.client.get(reverse("subekashi:stats"))
        self.assertNotContains(response, "stat-item")

    def test_zero_metric_still_shown_when_songs_exist(self):
        # 曲が1件以上あれば、他の指標(総高評価数等)がたまたま0でも
        # 「データなし」ではなく実際の値として表示する（コードレビュー指摘対応の仕様変更）
        Song.objects.create(title="曲", view=100, like=0)

        response = self.client.get(reverse("subekashi:stats"))

        stats_items = {item["label"]: item["value"] for item in response.context["stats_items"]}
        self.assertEqual(stats_items["総高評価数"], 0)
        self.assertContains(response, "stat-item")

    @staticmethod
    def _song_count(response):
        return next(item["value"] for item in response.context["stats_items"] if item["label"] == "曲数")

    def test_song_count_reflects_songrange_filter(self):
        Song.objects.create(title="すべあな曲", is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)

        response_all = self.client.get(reverse("subekashi:stats"), {"songrange": "all"})
        response_subeana = self.client.get(reverse("subekashi:stats"), {"songrange": "subeana"})

        self.assertEqual(self._song_count(response_all), 2)
        self.assertEqual(self._song_count(response_subeana), 1)

    def test_year_filter_narrows_results(self):
        Song.objects.create(title="2024年曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))
        Song.objects.create(title="2025年曲", upload_time=datetime(2025, 1, 1, tzinfo=dt_timezone.utc))

        response = self.client.get(reverse("subekashi:stats"), {"year": "2024"})

        self.assertEqual(self._song_count(response), 1)

    def test_unknown_songrange_falls_back_to_all(self):
        Song.objects.create(title="曲")
        response = self.client.get(reverse("subekashi:stats"), {"songrange": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._song_count(response), 1)

    def test_month_filter_narrows_results_across_years_without_year_filter(self):
        Song.objects.create(title="2024年1月曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))
        Song.objects.create(title="2025年6月曲", upload_time=datetime(2025, 6, 1, tzinfo=dt_timezone.utc))

        response = self.client.get(reverse("subekashi:stats"), {"month": "1"})

        self.assertEqual(self._song_count(response), 1)

    def test_month_select_shown_even_when_year_is_all(self):
        response = self.client.get(reverse("subekashi:stats"))
        self.assertContains(response, 'id="stats-month"')

    def test_non_numeric_year_falls_back_to_all_instead_of_500(self):
        Song.objects.create(title="曲")
        response = self.client.get(reverse("subekashi:stats"), {"year": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], "all")

    def test_non_numeric_month_falls_back_to_all_instead_of_500(self):
        Song.objects.create(title="曲")
        response = self.client.get(reverse("subekashi:stats"), {"month": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["month"], "all")

    def test_float_like_month_falls_back_to_all_instead_of_500(self):
        Song.objects.create(title="曲")
        response = self.client.get(reverse("subekashi:stats"), {"month": "1.5"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["month"], "all")

    def test_menu_contains_stats_link(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, reverse("subekashi:stats"))

    def test_songrange_radio_group_shown_when_both_songranges_exist(self):
        Song.objects.create(title="すべあな曲", is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)

        response = self.client.get(reverse("subekashi:stats"))

        self.assertContains(response, 'id="songrange-all"')
        self.assertContains(response, 'id="songrange-subeana"')
        self.assertContains(response, 'id="songrange-xx"')

    def test_year_choices_scoped_to_selected_songrange(self):
        # songrange=subeanaを選んでいる間は、xx曲しか無い年を選択肢に出さない
        # （0件になり得る組み合わせを避けるため、コードレビュー指摘対応）
        Song.objects.create(title="xx曲(2020年)", is_subeana=False, upload_time=datetime(2020, 1, 1, tzinfo=dt_timezone.utc))
        Song.objects.create(title="すべあな曲(2024年)", is_subeana=True, upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))

        response = self.client.get(reverse("subekashi:stats"), {"songrange": "subeana"})

        self.assertNotIn(2020, response.context["year_choices"])
        self.assertIn(2024, response.context["year_choices"])

    def test_songrange_radio_group_hidden_when_only_one_songrange_exists(self):
        # is_subeana=Falseの曲が無い場合、選んでも意味のある違いが出ないため
        # ラジオグループ自体（全て/すべあな界隈曲のみ/以外の3つとも）を非表示にする。
        # songrangeはcontext上では"subeana"に解決される
        Song.objects.create(title="すべあな曲", is_subeana=True)

        response = self.client.get(reverse("subekashi:stats"))

        self.assertEqual(response.context["songrange"], "subeana")
        self.assertNotContains(response, 'id="songrange-all"')
        self.assertNotContains(response, 'id="songrange-subeana"')
        self.assertNotContains(response, 'id="songrange-xx"')

    def test_explicit_songrange_is_overridden_when_only_one_songrange_exists(self):
        # 選択肢が非表示のカテゴリを?songrange=xxのように明示指定しても、
        # 常に0件になる意味の無い絞り込みを許さず実在する方に強制する（レビュー指摘対応）
        Song.objects.create(title="すべあな曲", is_subeana=True)

        response = self.client.get(reverse("subekashi:stats"), {"songrange": "xx"})

        self.assertEqual(response.context["songrange"], "subeana")
        self.assertEqual(self._song_count(response), 1)

    def test_zero_padded_year_is_normalized_for_select_state(self):
        # URL直打ちのゼロ埋め等でも、テンプレート上の選択状態比較に使う
        # context["year"]は正規化された文字列になる（レビュー指摘対応）
        Song.objects.create(title="曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))

        response = self.client.get(reverse("subekashi:stats"), {"year": "02024"})

        self.assertEqual(response.context["year"], "2024")
        self.assertContains(response, 'value="2024" selected')

    def test_monthly_stats_reflects_songrange_filter(self):
        # グラフがsongrangeフィルターの影響を受けるようにした仕様変更の回帰テスト
        Stats.objects.create(year=2024, month=1, songrange="all", song_count=10)
        Stats.objects.create(year=2024, month=1, songrange="subeana", song_count=6)
        Stats.objects.create(year=2024, month=1, songrange="xx", song_count=4)
        Song.objects.create(title="すべあな曲", is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)

        response = self.client.get(reverse("subekashi:stats"), {"songrange": "subeana"})

        monthly_stats = response.context["monthly_stats"]
        self.assertEqual(len(monthly_stats), 1)
        self.assertEqual(monthly_stats[0]["song_count"], 6)

    def test_monthly_stats_reflects_year_filter(self):
        Stats.objects.create(year=2024, month=1, songrange="all", song_count=5)
        Stats.objects.create(year=2025, month=1, songrange="all", song_count=9)
        # is_subeana両方の曲を用意し、songrangeが"all"以外に自動解決されないようにする
        Song.objects.create(title="曲", upload_time=datetime(2024, 6, 1, tzinfo=dt_timezone.utc), is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)

        response = self.client.get(reverse("subekashi:stats"), {"year": "2024"})

        monthly_stats = response.context["monthly_stats"]
        self.assertEqual(len(monthly_stats), 1)
        self.assertEqual(monthly_stats[0]["year"], 2024)

    def test_monthly_stats_reflects_month_only_filter_without_year(self):
        # ?month=1のようにyearを指定せずmonthだけ選んだ場合も、統計カードと
        # 同様にグラフ側も年をまたいだ該当月だけに絞り込む
        # （コードレビュー指摘対応: 以前はyear="all"だとmonth条件が無視され、
        # カードとグラフの表示内容が食い違っていたバグの回帰テスト）
        Stats.objects.create(year=2024, month=1, songrange="all", song_count=3)
        Stats.objects.create(year=2024, month=6, songrange="all", song_count=5)
        Stats.objects.create(year=2025, month=1, songrange="all", song_count=8)
        Song.objects.create(title="曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc), is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)

        response = self.client.get(reverse("subekashi:stats"), {"month": "1"})

        monthly_stats = response.context["monthly_stats"]
        self.assertEqual({(row["year"], row["month"]) for row in monthly_stats}, {(2024, 1), (2025, 1)})

    def test_monthly_stats_includes_delta_computed_from_full_history_before_year_filter(self):
        # 累積値の差分は絞り込み前の全期間から計算されるため、yearで絞り込んでも
        # 前月との差分が正しく計算される（"月ごと"モード用、レビュー指摘対応）
        Stats.objects.create(year=2024, month=12, songrange="all", song_count=5)
        Stats.objects.create(year=2025, month=1, songrange="all", song_count=8)
        Song.objects.create(title="曲", upload_time=datetime(2025, 1, 1, tzinfo=dt_timezone.utc), is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)

        response = self.client.get(reverse("subekashi:stats"), {"year": "2025"})

        monthly_stats = response.context["monthly_stats"]
        self.assertEqual(len(monthly_stats), 1)
        self.assertEqual(monthly_stats[0]["song_count_delta"], 3)

    def test_kenreki_hidden_when_no_songs(self):
        response = self.client.get(reverse("subekashi:stats"))
        self.assertIsNone(response.context["kenreki"])

    def test_kenreki_present_and_has_no_keyboard_visual(self):
        # 総合統計ページの鍵歴はstat-itemのみで、鍵盤ビジュアル(kenreki-keyboard-scroll)は表示しない
        Song.objects.create(title="曲", view=20, like=2)

        response = self.client.get(reverse("subekashi:stats"))

        self.assertEqual(response.context["kenreki"]["key_count"], 2)
        self.assertNotContains(response, "kenreki-keyboard-scroll")

    def test_kenreki_reflects_songrange_year_month_filters(self):
        # 総合統計ページの鍵歴は他の統計項目と同様、絞り込みの影響を受ける
        # （authorページの鍵歴は全期間の累積実績で絞り込みの影響を受けないのとは異なる仕様）
        Song.objects.create(title="2024年の曲", view=20, like=2, upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))
        Song.objects.create(title="2025年の曲", view=1000, like=0, upload_time=datetime(2025, 1, 1, tzinfo=dt_timezone.utc))

        unfiltered = self.client.get(reverse("subekashi:stats"))
        filtered_2024 = self.client.get(reverse("subekashi:stats"), {"year": "2024"})

        # 全期間: 2024年の曲(view=20:2段階=2pt, like=2:2段階=2pt=4pt) + 2025年の曲(view=1000:7段階=7pt) = 11pt -> 5鍵
        # （鍵歴はSongごとに算出して合計するため、集計後のview=1020に対する閾値判定ではない）
        self.assertEqual(unfiltered.context["kenreki"]["key_count"], 5)
        # 2024年のみ: view=20(2段階=2pt)+like=2(2段階=2pt)=4pt -> 2鍵
        self.assertEqual(filtered_2024.context["kenreki"]["key_count"], 2)

    def test_kenreki_stat_value_never_colored_even_when_overflowing(self):
        # 総合統計ページの鍵歴はstat-valueの着色をしない（authorページとの仕様差、コードレビュー指摘対応）
        # view/likeはMySQLのIntegerField（INT、上限约21億）の範囲内に収める必要があるため、
        # 段階数を十分に振り切れる大きさとして2*10**9を使う（#593、MySQL移行時に10**12だと
        # Out of range value for columnエラーになることを確認済み）
        for i in range(5):
            Song.objects.create(title=f"曲{i}", view=2 * 10 ** 9, like=2 * 10 ** 9)

        response = self.client.get(reverse("subekashi:stats"))

        self.assertGreaterEqual(response.context["kenreki"]["key_count"], 88)
        self.assertIsNone(response.context["kenreki"]["overflow_color"])
        self.assertNotContains(response, "style=\"color: hsl(")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorStatsViewTest(TestCase):
    """AuthorStatsView (/authors/<id>/stats/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="統計テスト作者")

    def test_existing_author_returns_200(self):
        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(reverse("subekashi:author_stats", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_non_numeric_year_falls_back_to_all_instead_of_500(self):
        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]), {"year": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["year"], "all")

    def test_non_numeric_month_falls_back_to_all_instead_of_500(self):
        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]), {"month": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["month"], "all")

    def test_only_counts_songs_of_this_author(self):
        other_author = Author.objects.create(name="別の作者")
        Song.objects.create(title="他author曲").authors.add(other_author)
        Song.objects.create(title="この作者の曲").authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        song_count = next(item["value"] for item in response.context["stats_items"] if item["label"] == "曲数")
        self.assertEqual(song_count, 1)

    def test_collaborator_counts_exclude_self(self):
        other_author = Author.objects.create(name="共作者")
        song = Song.objects.create(title="共作曲")
        song.authors.add(self.author, other_author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        stats_items = {item["label"]: item["value"] for item in response.context["stats_items"]}
        self.assertEqual(stats_items["合作人数(重複あり)"], 1)
        self.assertEqual(stats_items["合作人数(重複なし)"], 1)
        self.assertNotIn("総作者数", stats_items)

    def test_songrange_radio_group_hidden_when_author_has_only_one_songrange(self):
        # サイト全体にはxx曲が存在しても、この作者自身にはsubeana曲しかないため
        # ラジオグループ自体（全て/すべあな界隈曲のみ/以外の3つとも）が不要
        Song.objects.create(title="すべあな曲", is_subeana=True).authors.add(self.author)
        Song.objects.create(title="他作者の界隈外曲", is_subeana=False)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        self.assertNotContains(response, 'id="songrange-all"')
        self.assertNotContains(response, 'id="songrange-subeana"')
        self.assertNotContains(response, 'id="songrange-xx"')
        self.assertEqual(response.context["songrange"], "subeana")

    def test_year_choices_scoped_to_this_author_only(self):
        # サイト全体には別年の曲があっても、この作者自身が投稿していない年は
        # 選択肢に出さない（コードレビュー指摘対応）
        other_author = Author.objects.create(name="別の作者")
        Song.objects.create(title="他authorの曲", upload_time=datetime(2020, 1, 1, tzinfo=dt_timezone.utc)).authors.add(other_author)
        Song.objects.create(title="この作者の曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc)).authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        self.assertNotIn(2020, response.context["year_choices"])
        self.assertIn(2024, response.context["year_choices"])

    def test_month_choices_scoped_to_this_author_only(self):
        # この作者が実際に投稿していない月は選択肢に出さない
        # （選んでも0件になる組み合わせを避けるため、コードレビュー指摘対応）
        other_author = Author.objects.create(name="別の作者")
        Song.objects.create(title="他authorの3月の曲", upload_time=datetime(2024, 3, 1, tzinfo=dt_timezone.utc)).authors.add(other_author)
        Song.objects.create(title="この作者の6月の曲", upload_time=datetime(2024, 6, 1, tzinfo=dt_timezone.utc)).authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]), {"year": "2024"})

        self.assertEqual(response.context["month_choices"], [6])

    def test_year_choices_exclude_gap_years_with_no_songs(self):
        # 2020年・2024年にしか投稿が無い場合、間の2021〜2023年は選択肢に出ない
        # （最古年〜今年の連続レンジではなく実データに基づく、コードレビュー指摘対応）
        Song.objects.create(title="2020年の曲", upload_time=datetime(2020, 1, 1, tzinfo=dt_timezone.utc)).authors.add(self.author)
        Song.objects.create(title="2024年の曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc)).authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        self.assertEqual(response.context["year_choices"], [2020, 2024])

    def test_month_resets_to_all_when_new_year_has_no_data_for_that_month(self):
        # 年を変更した際、切り替え先の年にその月のデータが無ければmonthは
        # "all"に自動的にフォールバックする（不正な組み合わせのまま残らない）
        Song.objects.create(title="2024年6月の曲", upload_time=datetime(2024, 6, 1, tzinfo=dt_timezone.utc)).authors.add(self.author)
        Song.objects.create(title="2025年3月の曲", upload_time=datetime(2025, 3, 1, tzinfo=dt_timezone.utc)).authors.add(self.author)

        # 2024年・6月を選んでいた状態から、年だけ2025年に切り替えたケースを想定
        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]), {"year": "2025", "month": "6"})

        self.assertEqual(response.context["year"], "2025")
        self.assertEqual(response.context["month"], "all")

    def test_does_not_issue_unused_total_authors_query(self):
        # コードレビュー指摘対応: 画面に表示しないtotal_authors算出のための
        # 追加クエリ（Author起点のcompute_unique_author_count）が発行されないこと
        # の回帰防止テスト。クエリ数が増えた場合はこの値を更新しつつ、原因を確認すること
        # （鍵歴算出用のcompute_view_like_totals分1クエリを含む）
        Song.objects.create(title="曲").authors.add(self.author)

        with self.assertNumQueries(11):
            self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

    def test_kenreki_hidden_when_author_has_no_songs(self):
        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))
        self.assertIsNone(response.context["kenreki"])

    def test_kenreki_present_when_author_has_songs(self):
        Song.objects.create(title="曲", view=1, like=0).authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        self.assertIsNotNone(response.context["kenreki"])
        self.assertEqual(response.context["kenreki"]["key_count"], 0)

    def test_kenreki_key_count_reflects_total_view_and_like(self):
        # view=20(2段階=2pt)+like=2(2段階=2pt)=合計4pt / 2pt = 2鍵
        Song.objects.create(title="曲", view=20, like=2).authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        self.assertEqual(response.context["kenreki"]["key_count"], 2)

    def test_kenreki_not_affected_by_songrange_year_month_filters(self):
        # 鍵歴はauthorの全期間・全songrangeの累積実績（絞り込みの影響を受けない）
        Song.objects.create(
            title="2020年のsubeana曲", view=1000, like=0, is_subeana=True,
            upload_time=datetime(2020, 1, 1, tzinfo=dt_timezone.utc),
        ).authors.add(self.author)

        unfiltered = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))
        filtered = self.client.get(
            reverse("subekashi:author_stats", args=[self.author.id]),
            {"songrange": "xx", "year": "2024"},
        )

        self.assertEqual(unfiltered.context["kenreki"]["key_count"], filtered.context["kenreki"]["key_count"])
        self.assertGreater(filtered.context["kenreki"]["key_count"], 0)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasesViewTest(TestCase):
    """AuthorAliasesView (/authors/<id>/aliases) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="別名一覧テスト作者")

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_no_aliases_returns_200(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "別名が見つかりませんでした")

    def test_author_page_link_is_present(self):
        # 別名一覧画面から作者自身のページへ遷移できるボタンを表示する（#1024）。
        # reverse("subekashi:author", ...)は"/authors/<id>/aliases/..."等の他リンクの
        # プレフィックスとしても部分一致してしまうため、ボタンのラベルで判定する
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        author_url = reverse("subekashi:author", args=[self.author.id])
        self.assertContains(response, f'href="{author_url}"')
        self.assertContains(response, "作者ページ")

    def test_author_page_link_is_leftmost_button(self):
        # 作者ページボタンは.dummybuttons内の一番左（DOM順で最初）に配置する（#1024）
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        content = response.content.decode()
        author_url = reverse("subekashi:author", args=[self.author.id])
        self.assertLess(content.index(f'href="{author_url}"'), content.index("再読み込み"))
        self.assertLess(content.index(f'href="{author_url}"'), content.index("別名を追加する"))

    def test_forward_alias_is_displayed_with_edit_delete_links(self):
        alias = AuthorAlias.objects.create(name="別名X", author=self.author, alias_type="spell")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "別名X")
        self.assertContains(response, reverse("subekashi:author_alias_edit", args=[self.author.id, alias.id]))
        self.assertContains(response, reverse("subekashi:author_alias_delete", args=[self.author.id, alias.id]))

    def test_forward_alias_without_existing_author_shows_no_nav_icon(self):
        # 編集可能な行（自分が直接保有する別名）で、別名自体に対応する実在Authorが
        # 存在しない場合、遷移アイコンは表示しない（フォールバック先が自分自身になり
        # 無意味なため、編集可能な行では所有者へのフォールバックを行わない設計）
        AuthorAlias.objects.create(name="実在しない別名Y", author=self.author, alias_type="spell")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "実在しない別名Y")
        self.assertNotContains(response, "fa-arrow-right")

    def test_reverse_alias_is_displayed_without_edit_delete_links(self):
        target = Author.objects.create(name="別名逆方向対象")
        alias = AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "別名逆方向対象")
        self.assertNotContains(response, reverse("subekashi:author_alias_edit", args=[self.author.id, alias.id]))
        self.assertNotContains(response, reverse("subekashi:author_alias_delete", args=[self.author.id, alias.id]))

    def test_reverse_alias_shows_nav_icon_even_when_owner_id_is_zero(self):
        # 遷移先author idが0の場合でもアイコンが表示されることを確認する
        # （テンプレート側が`{% if row.next_alias_author_id %}`のような真偽値判定だと
        # 0がfalsyになり表示されなくなる。`is not None`で判定する必要がある）
        # MySQLのAUTO_INCREMENT列はid=0の明示指定を自動採番と解釈するため、実際に
        # Author(id=0)をDBへ保存する形では検証できない。get_transitive_aliases()を
        # モックしてauthor_id=0のケースを作り、DBバックエンドに依存せず検証する
        # （#593、コードレビュー指摘対応）
        fake_source = MagicMock(id=999)
        fake_alias = TransitiveAlias(
            name="別名逆方向遷移対象ゼロ",
            alias_type="past",
            source=fake_source,
            is_reverse=True,
            is_direct=False,
            author_id=0,
        )
        with patch.object(Author, "get_transitive_aliases", return_value=[fake_alias]):
            response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[0]))

    def test_reverse_alias_shows_nav_icon_to_owning_authors_list(self):
        # 編集・削除できない逆方向の別名は、代わりにその別名を所有するauthor自身の
        # 一覧画面への遷移アイコン(fa-arrow-right)を表示する
        target = Author.objects.create(name="別名逆方向遷移対象")
        AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[target.id]))

    def test_forward_past_alias_shows_izen_no_meisho(self):
        # #1019: 正方向（自分がpastの別名を登録している側）は「以前の名称」のまま
        AuthorAlias.objects.create(name="以前の名称対象", author=self.author, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "以前の名称")
        self.assertNotContains(response, "その後の名称")

    def test_reverse_past_alias_shows_sonogo_no_meisho(self):
        # #1019: 逆方向（相手が自分をpastの別名として登録している側）は「その後の名称」と表示する
        target = Author.objects.create(name="その後の名称対象")
        AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "その後の名称")

    def test_past_alias_with_existing_author_links_to_channel(self):
        Author.objects.create(name="別名チャンネル対象")
        AuthorAlias.objects.create(name="別名チャンネル対象", author=self.author, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, reverse("subekashi:channel", args=["別名チャンネル対象"]))

    def test_past_alias_without_existing_author_does_not_link_to_channel(self):
        AuthorAlias.objects.create(name="実在しない別名", author=self.author, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "実在しない別名")
        self.assertNotContains(response, reverse("subekashi:channel", args=["実在しない別名"]))

    def test_non_linkable_alias_type_does_not_link_to_channel_even_if_author_exists(self):
        Author.objects.create(name="略称対象作者")
        AuthorAlias.objects.create(name="略称対象作者", author=self.author, alias_type="abbr")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertNotContains(response, reverse("subekashi:channel", args=["略称対象作者"]))

    def test_reload_button_present(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, "reloadPage()")
        self.assertContains(response, "fa-redo")

    def test_add_button_has_plus_icon(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, "fa-plus")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasesViewTransitiveResolutionTest(TestCase):
    """AuthorAliasesView の推移的関係解決の反映のテスト（#1007）

    #1003で確認された具体例（名義Aに別名義B・以前の名称C・以前の名称D・グループEを登録）を
    そのまま再現し、各authorの一覧画面が仕様表の通りになることを確認する。
    """

    def setUp(self):
        self.client = Client()
        self.a = Author.objects.create(name="view_tamura")
        self.b = Author.objects.create(name="view_inoue")
        self.c = Author.objects.create(name="view_kobayashi")
        self.d = Author.objects.create(name="view_yoshida")
        self.e = Author.objects.create(name="view_watanabe")
        self.alias_b = AuthorAlias.objects.create(name="view_inoue", author=self.a, alias_type="another")
        self.alias_c = AuthorAlias.objects.create(name="view_kobayashi", author=self.a, alias_type="past")
        self.alias_d = AuthorAlias.objects.create(name="view_yoshida", author=self.a, alias_type="past")
        self.alias_e = AuthorAlias.objects.create(name="view_watanabe", author=self.a, alias_type="group")

    def test_author_a_list_shows_four_direct_relations_all_editable(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.a.id]))

        self.assertContains(response, "view_inoue")
        self.assertContains(response, "別名義")
        self.assertContains(response, "view_kobayashi")
        self.assertContains(response, "view_yoshida")
        self.assertContains(response, "以前の名称")
        self.assertContains(response, "view_watanabe")
        self.assertContains(response, "所属グループ")
        # 4件とも自分が直接保有する別名のため、編集・削除リンクが4件分含まれる
        for alias in [self.alias_b, self.alias_c, self.alias_d, self.alias_e]:
            self.assertContains(response, reverse("subekashi:author_alias_edit", args=[self.a.id, alias.id]))
            self.assertContains(response, reverse("subekashi:author_alias_delete", args=[self.a.id, alias.id]))
        # 編集可能な行でも、別名自体(B/C/D/E)に対応する実在Authorへの遷移アイコンが表示される
        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.b.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.c.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.d.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.e.id]))

    def test_author_b_list_shows_only_a_another_does_not_bridge(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.b.id]))

        self.assertContains(response, "view_tamura")
        self.assertContains(response, "別名義")
        self.assertNotContains(response, "view_kobayashi")
        self.assertNotContains(response, "view_yoshida")
        self.assertNotContains(response, "view_watanabe")
        # 逆方向のため編集・削除リンクは含まれない
        self.assertNotContains(response, "fa-pen")
        # Aへの関係は直接（1ホップ）だが逆方向で編集できないため、Aの一覧への遷移アイコンが表示される
        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.a.id]))

    def test_author_c_list_shows_a_b_d_e_transitively_via_past(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.c.id]))

        self.assertContains(response, "view_tamura")
        self.assertContains(response, "view_inoue")
        self.assertContains(response, "view_yoshida")
        self.assertContains(response, "view_watanabe")
        self.assertContains(response, "所属グループ")
        # Aへの関係は逆方向のため「その後の名称」、Dへの関係は間接的だが正方向のため「以前の名称」のまま（#1019）
        self.assertContains(response, "その後の名称")
        self.assertContains(response, "以前の名称")
        # Aへの関係は逆方向、B/D/Eへの関係は間接的なため、いずれも編集・削除できない
        self.assertNotContains(response, "fa-pen")
        # 編集できない4件（A・B・D・E）全てに、それぞれの別名一覧への遷移アイコンが表示される
        # （ホップ数・方向を問わず、対応するAuthorが実在すれば表示する）
        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.a.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.b.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.d.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.e.id]))

    def test_author_c_list_query_count_is_bounded(self):
        # #1023: 遷移先author idの補完的な問い合わせが、クラスタ全体ではなく
        # 未解決の名前(B・E)のみを対象にした1クエリに収まっていることの回帰防止テスト。
        # クエリ数が増えた場合はこの値を更新しつつ、原因を確認すること
        # （10クエリ目は#1008で追加した一番有名な名義の候補一覧取得）
        with self.assertNumQueries(10):
            self.client.get(reverse("subekashi:author_aliases", args=[self.c.id]))

    def test_author_c_list_unresolved_query_scope_excludes_resolved_names(self):
        # #1023: 補完的な問い合わせのIN句が、get_transitive_aliases()側で既に
        # author_idを解決済みのA・D（別名一覧に4件とも表示されるが、A・Dはauthor_idが
        # 解決済みのため対象外になるはず）を含まず、未解決のB・Eのみに絞られていることを
        # 直接確認する（クエリ数だけではクラスタ全体を対象にする regression を検知できないため）
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("subekashi:author_aliases", args=[self.c.id]))

        # 識別子のクオート文字はDBバックエンドにより異なる（SQLite/PostgreSQLは"、MySQLは`）
        # ため、connection.ops.quote_name()で動的に生成して比較する（#593）
        qn = connection.ops.quote_name
        target_fragment = f'{qn("subekashi_author")}.{qn("name")} IN'
        unresolved_queries = [
            q for q in ctx.captured_queries
            if target_fragment in q["sql"]
        ]
        self.assertEqual(len(unresolved_queries), 1)
        sql = unresolved_queries[0]["sql"]
        self.assertIn("view_inoue", sql)
        self.assertIn("view_watanabe", sql)
        self.assertNotIn("view_tamura", sql)
        self.assertNotIn("view_yoshida", sql)

    def test_author_e_list_shows_only_a_group_does_not_bridge(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.e.id]))

        self.assertContains(response, "view_tamura")
        self.assertContains(response, "所属している名義")
        self.assertNotContains(response, "view_inoue")
        self.assertNotContains(response, "view_kobayashi")
        self.assertNotContains(response, "view_yoshida")
        self.assertNotContains(response, "fa-pen")
        # Aへの関係は直接（1ホップ）だが逆方向で編集できないため、Aの一覧への遷移アイコンが表示される
        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.a.id]))

    def test_alias_without_existing_author_falls_back_to_owner_nav_icon(self):
        # 別名自体(ghost)に対応する実在Authorが存在しない場合でも、編集できない行は
        # そのAuthorAlias自体を実際に所有しているauthor(p)のページへフォールバックする。
        # p→ghost(past、Authorなし)、p→r(past、rは実在) という構成でrの一覧を見ると、
        # pへの関係(直接・逆方向)もghostへの関係(間接)も、どちらもpのページへ遷移する
        p = Author.objects.create(name="view_nav_p")
        r = Author.objects.create(name="view_nav_r")
        AuthorAlias.objects.create(name="view_nav_ghost", author=p, alias_type="past")
        AuthorAlias.objects.create(name=r.name, author=p, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[r.id]))

        self.assertContains(response, "view_nav_ghost")
        self.assertContains(response, "view_nav_p")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[p.id]))
        # p自身の行、ghostのフォールバック行の2件分の遷移アイコンが表示される
        self.assertEqual(response.content.decode().count("fa-arrow-right"), 2)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasNewViewTest(TestCase):
    """AuthorAliasNewView (/authors/<id>/aliases/new) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="別名新規テスト作者")

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_alias_type_has_placeholder_option(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, '<option value="" selected disabled>選択してください</option>')

    def test_alias_type_options_have_description_attribute(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, 'data-description="以前使用されていた名称です。')

    def test_linkable_alias_types_mention_channel_link_in_description(self):
        # past/another/groupはchannelリンクが貼られる種別のため、説明文にその旨を含める
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        content = response.content.decode()
        past_option = content[content.index('value="past"'):content.index('</option>', content.index('value="past"'))]
        another_option = content[content.index('value="another"'):content.index('</option>', content.index('value="another"'))]
        group_option = content[content.index('value="group"'):content.index('</option>', content.index('value="group"'))]
        abbr_option = content[content.index('value="abbr"'):content.index('</option>', content.index('value="abbr"'))]
        self.assertIn("チャンネルページへのリンク", past_option)
        self.assertIn("チャンネルページへのリンク", another_option)
        self.assertIn("チャンネルページへのリンク", group_option)
        self.assertNotIn("チャンネルページへのリンク", abbr_option)

    def test_past_description_mentions_primary_name(self):
        # past種別の説明に、一番有名な名義として選択できる旨を含める（#1029）
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        content = response.content.decode()
        past_option = content[content.index('value="past"'):content.index('</option>', content.index('value="past"'))]
        self.assertIn("一番有名な名義", past_option)

    def test_group_option_is_available(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, 'value="group"')
        self.assertContains(response, "グループ</option>")

    def test_another_description_mentions_official_recognition(self):
        # 別名義は本人による公認が前提であることを説明文に明記する
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        content = response.content.decode()
        another_option = content[content.index('value="another"'):content.index('</option>', content.index('value="another"'))]
        self.assertIn("公認", another_option)

    def test_submit_button_initially_disabled(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, '<input type="submit" value="登録" disabled>')

    def test_alias_type_description_has_info_icon_between_form_and_button(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        content = response.content.decode()
        self.assertContains(response, "fas fa-info-circle info")
        self.assertContains(response, 'id="alias-type-description-text"')
        # 説明欄がフォームのフィールド群より後、送信ボタンより前にあることを確認する
        description_index = content.index('id="alias-type-description"')
        select_index = content.index('id="alias_type"')
        submit_index = content.index('<input type="submit"')
        self.assertLess(select_index, description_index)
        self.assertLess(description_index, submit_index)

    def test_includes_author_alias_form_js(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, "author_alias_form.js")

    def test_post_creates_alias_and_redirects_to_list(self):
        response = self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "新規別名A", "alias_type": "past"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=new"
        )
        self.assertTrue(AuthorAlias.objects.filter(name="新規別名A", author=self.author).exists())

    def test_post_creates_history(self):
        self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "新規別名B", "alias_type": "past"},
        )
        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "new")
        self.assertIn("新規別名B", history.title)

    def test_post_duplicate_name_shows_error_without_creating(self):
        AuthorAlias.objects.create(name="重複別名", author=self.author)
        response = self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "重複別名", "alias_type": "past"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuthorAlias.objects.filter(name="重複別名").count(), 1)

    def test_post_name_same_as_author_shows_error(self):
        response = self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": self.author.name, "alias_type": "past"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuthorAlias.objects.filter(name=self.author.name).exists())

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "通知別名", "alias_type": "past"},
        )
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("通知別名", content)
        self.assertIn(self.author.name, content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_rolls_back_alias_and_returns_500(self, mock_send_discord):
        mock_send_discord.return_value = False
        response = self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "通知失敗別名", "alias_type": "past"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertFalse(AuthorAlias.objects.filter(name="通知失敗別名").exists())
        # Discord通知前にはDBへ一切書き込まないため、孤立したHistoryも作成されない
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    def test_toctou_duplicate_name_shows_friendly_error_not_500(self):
        # フォームのclean_name()での重複チェックをすり抜けた場合でも、
        # DB制約(IntegrityError)を捕捉してフォームエラーに変換されることを確認する
        # unique_authoralias_name_except_groupは条件付きUniqueConstraintのため、
        # 未サポートのMySQLでは0049マイグレーションの生成列ワークアラウンドで
        # 同等のDB制約を代替している（#593）
        AuthorAlias.objects.create(name="競合別名", author=self.author)
        with patch.object(AuthorAliasForm, "clean_name", return_value="競合別名"):
            response = self.client.post(
                reverse("subekashi:author_alias_new", args=[self.author.id]),
                {"name": "競合別名", "alias_type": "past"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "その別名は既に登録されています。")
        self.assertEqual(AuthorAlias.objects.filter(name="競合別名").count(), 1)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasEditViewTest(TestCase):
    """AuthorAliasEditView (/authors/<id>/aliases/<alias_id>/edit) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="別名編集テスト作者")
        self.alias = AuthorAlias.objects.create(name="編集前別名", author=self.author, alias_type="past")

    def test_get_returns_200(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_current_alias_type_is_selected(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, 'value="past" data-description="以前使用されていた名称です。')
        self.assertContains(response, 'selected>以前の名称</option>')

    def test_back_to_alias_list_button_is_present(self):
        # 別名一覧画面へ戻るボタンを表示する（#1024）。
        # reverse("subekashi:author_aliases", ...)は、このページ自体のフォームaction
        # ("/authors/<id>/aliases/<alias_id>/edit/")のプレフィックスとしても部分一致
        # してしまうため、href属性値として厳密に一致するかで判定する
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        aliases_url = reverse("subekashi:author_aliases", args=[self.author.id])
        self.assertContains(response, f'href="{aliases_url}"')
        self.assertContains(response, "戻る")

    def test_submit_button_matches_confirm_screen_style(self):
        # 更新ボタンを一番有名な名義の変更確認画面と同様のdummybutton形式にする（#1024）
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, "更新する")
        self.assertContains(response, '<button type="submit" class="dummybutton black-dummybutton dummybutton-w140">')

    def test_alias_type_has_disabled_placeholder_option(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, '<option value="" disabled>選択してください</option>')

    def test_includes_author_alias_form_js(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, "author_alias_form.js")

    def test_nonexistent_alias_returns_404(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, 99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_alias_belonging_to_other_author_returns_404(self):
        other_author = Author.objects.create(name="別の作者")
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[other_author.id, self.alias.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_post_updates_alias_and_redirects_to_list(self):
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集後別名", "alias_type": "sns"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=edit"
        )
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.name, "編集後別名")
        self.assertEqual(self.alias.alias_type, "sns")

    def test_post_creates_history(self):
        self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集後別名2", "alias_type": "sns"},
        )
        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "edit")
        self.assertIn("編集前別名", history.title)

    def test_post_can_keep_own_name_unchanged(self):
        # 自分自身(編集対象)の現在の名前のまま更新しても重複エラーにならない
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集前別名", "alias_type": "sns"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=edit"
        )

    def test_post_duplicate_name_with_other_alias_shows_error(self):
        AuthorAlias.objects.create(name="他の別名", author=self.author)
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "他の別名", "alias_type": "past"},
        )
        self.assertEqual(response.status_code, 200)
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.name, "編集前別名")

    def test_post_without_actual_change_skips_history(self):
        # SongEditViewと同様、実質的な変更がない場合は履歴を作成しない
        before_count = History.get_for_author(self.author).count()
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集前別名", "alias_type": "past"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=edit"
        )
        self.assertEqual(History.get_for_author(self.author).count(), before_count)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_without_actual_change_does_not_send_discord(self, mock_send_discord):
        self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集前別名", "alias_type": "past"},
        )
        self.assertFalse(mock_send_discord.called)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_with_change_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集後通知別名", "alias_type": "sns"},
        )
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("編集後通知別名", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_returns_500(self, mock_send_discord):
        mock_send_discord.return_value = False
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集後失敗別名", "alias_type": "sns"},
        )
        self.assertEqual(response.status_code, 500)
        # Discord通知失敗時はDBへコミットしないため、editが実際には成功してしまわないこと・
        # 孤立したHistoryが残らないことを確認する
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.name, "編集前別名")
        self.assertEqual(self.alias.alias_type, "past")
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    def test_toctou_duplicate_name_shows_friendly_error_not_500(self):
        # unique_authoralias_name_except_groupは条件付きUniqueConstraintのため、
        # 未サポートのMySQLでは0049マイグレーションの生成列ワークアラウンドで
        # 同等のDB制約を代替している（#593）
        AuthorAlias.objects.create(name="編集競合別名", author=self.author)
        with patch.object(AuthorAliasForm, "clean_name", return_value="編集競合別名"):
            response = self.client.post(
                reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
                {"name": "編集競合別名", "alias_type": "past"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "その別名は既に登録されています。")
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.name, "編集前別名")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasDeleteViewTest(TestCase):
    """AuthorAliasDeleteView (/authors/<id>/aliases/<alias_id>/delete) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="別名削除テスト作者")
        self.alias = AuthorAlias.objects.create(name="削除対象別名", author=self.author, alias_type="past")

    def test_get_returns_200(self):
        response = self.client.get(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "削除対象別名")

    def test_cancel_and_delete_buttons_have_icons(self):
        response = self.client.get(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, "fa-times")
        self.assertContains(response, "fa-trash-alt")

    def test_nonexistent_alias_returns_404(self):
        response = self.client.get(
            reverse("subekashi:author_alias_delete", args=[self.author.id, 99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_post_deletes_alias_and_redirects_to_list(self):
        response = self.client.post(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=delete"
        )
        self.assertFalse(AuthorAlias.objects.filter(pk=self.alias.id).exists())

    def test_post_creates_history_and_preserves_author_link(self):
        self.client.post(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "delete")
        self.assertIn("削除対象別名", history.title)
        self.assertEqual(history.author, self.author)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self.client.post(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("削除対象別名", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_prevents_deletion(self, mock_send_discord):
        mock_send_discord.return_value = False
        response = self.client.post(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertEqual(response.status_code, 500)
        self.assertTrue(AuthorAlias.objects.filter(pk=self.alias.id).exists())
        self.assertEqual(History.get_for_author(self.author).count(), 0)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorPrimaryNameSetViewTest(TestCase):
    """AuthorPrimaryNameSetView (/authors/<id>/aliases/primary) のテスト（#1008）"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="現在の名義")
        self.past_alias = AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")

    def test_nonexistent_author_returns_404(self):
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[99999]), {"name": "以前の名義"}
        )
        self.assertEqual(response.status_code, 404)

    def test_selecting_current_name_is_noop_and_redirects(self):
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": self.author.name},
        )
        self.assertRedirects(response, reverse("subekashi:author_aliases", args=[self.author.id]))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")

    def test_selecting_past_alias_swaps_name_and_reregisters_old_name_as_past(self):
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "以前の名義")
        # 選ばれた側の別名行は消え、旧名が新たなpast別名として登録される
        self.assertFalse(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())
        new_alias = AuthorAlias.objects.get(name="現在の名義")
        self.assertEqual(new_alias.author, self.author)
        self.assertEqual(new_alias.alias_type, "past")

    def test_selecting_non_past_alias_type_is_rejected(self):
        AuthorAlias.objects.create(name="別名義候補", author=self.author, alias_type="another")
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "別名義候補"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")

    def test_selecting_name_conflicting_with_another_author_merges_and_deletes_it(self):
        # 選択した名義が既に別のAuthorとして登録されている場合、そのAuthorを
        # このauthorに統合（マージ）した上で名義を変更する（#1029）
        conflicting = Author.objects.create(name="以前の名義")
        song = Song.objects.create(title="conflicting側の曲")
        song.authors.add(conflicting)
        link = AuthorLink.objects.create(url="https://example.com/conflicting", author=conflicting)
        conflicting_alias = AuthorAlias.objects.create(name="conflictingの別名", author=conflicting, alias_type="another")

        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "以前の名義")
        self.assertFalse(Author.objects.filter(pk=conflicting.pk).exists())

        song.refresh_from_db()
        self.assertIn(self.author, song.authors.all())

        link.refresh_from_db()
        self.assertEqual(link.author_id, self.author.id)

        conflicting_alias.refresh_from_db()
        self.assertEqual(conflicting_alias.author_id, self.author.id)

        new_alias = AuthorAlias.objects.get(name="現在の名義")
        self.assertEqual(new_alias.author, self.author)
        self.assertEqual(new_alias.alias_type, "past")

    def test_merge_records_history_on_each_reassigned_song(self):
        # 統合によりauthorが変わる曲それぞれの編集履歴一覧にも記録する（#1034）。
        # conflicting_authorはname=new_nameで検索されるため、名前だけを編集前後に
        # 並べると常に同一文字列になり「何も変わっていないように」見えてしまう。
        # 実際に変わったのはAuthorの実体（id）であるため、idを含めて記録する
        conflicting = Author.objects.create(name="以前の名義")
        conflicting_id = conflicting.id
        song1 = Song.objects.create(title="統合対象曲1")
        song1.authors.add(conflicting)
        song2 = Song.objects.create(title="統合対象曲2")
        song2.authors.add(conflicting)
        unrelated_author = Author.objects.create(name="無関係な作者")
        unrelated_song = Song.objects.create(title="無関係な曲")
        unrelated_song.authors.add(unrelated_author)

        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        for song in (song1, song2):
            # 将来同様の重複バグが再発した際に検知できるよう、件数も明示的に確認する
            self.assertEqual(History.get_for_song(song).count(), 1)
            history = History.get_for_song(song).first()
            self.assertIsNotNone(history)
            self.assertEqual(history.history_type, "edit")
            self.assertEqual(history.title, "一番有名な名義の変更により作者を統合")
            merge_row = next((row for row in history.changes if row[0] == "作者"), None)
            self.assertIsNotNone(merge_row)
            self.assertEqual(merge_row[1], f"id={conflicting_id}, name=以前の名義")
            self.assertEqual(merge_row[2], f"id={self.author.id}, name=以前の名義")

        # このauthorとは無関係な曲の編集履歴は増えない
        self.assertEqual(History.get_for_song(unrelated_song).count(), 0)

    def test_rename_without_merge_records_history_on_existing_songs(self):
        # 衝突するAuthorが存在しない単純な名義変更でも、元々このauthorに
        # 紐づいている曲の編集履歴一覧に「作者の名義が変更された」旨を記録する（#1034）
        own_song = Song.objects.create(title="既存の曲")
        own_song.authors.add(self.author)

        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        # 将来同様の重複バグが再発した際に検知できるよう、件数も明示的に確認する
        self.assertEqual(History.get_for_song(own_song).count(), 1)
        history = History.get_for_song(own_song).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "edit")
        self.assertEqual(history.title, "一番有名な名義の変更により作者を変更")
        rename_row = next((row for row in history.changes if row[0] == "作者"), None)
        self.assertIsNotNone(rename_row)
        self.assertEqual(rename_row[1], "現在の名義")
        self.assertEqual(rename_row[2], "以前の名義")

    def test_merge_and_rename_histories_both_created_in_same_request(self):
        # マージ対象の曲（統合側）と、元々このauthorに紐づく別の曲（改名側）が
        # 同時に存在するケースで、1回のbulk_create()呼び出しで両方に正しく
        # 履歴が作成されることを確認する（#1034）
        conflicting = Author.objects.create(name="以前の名義")
        merged_song = Song.objects.create(title="統合対象曲")
        merged_song.authors.add(conflicting)
        own_song = Song.objects.create(title="元々このauthorの曲")
        own_song.authors.add(self.author)

        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        self.assertEqual(History.get_for_song(merged_song).count(), 1)
        self.assertEqual(History.get_for_song(merged_song).first().title, "一番有名な名義の変更により作者を統合")

        self.assertEqual(History.get_for_song(own_song).count(), 1)
        self.assertEqual(History.get_for_song(own_song).first().title, "一番有名な名義の変更により作者を変更")

    def test_song_shared_by_both_authors_before_merge_gets_only_one_history(self):
        # あるSongが統合前から既にself.authorとconflicting_author双方に紐づいて
        # いた場合、マージ側・名義変更側の両方から履歴が1件ずつ、計2件作成されて
        # しまわないよう重複を排除する（#1034）
        conflicting = Author.objects.create(name="以前の名義")
        shared_song = Song.objects.create(title="共著の曲")
        shared_song.authors.add(self.author, conflicting)

        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        self.assertEqual(History.get_for_song(shared_song).count(), 1)

    def test_merge_reuses_conflicting_authors_alias_matching_old_name(self):
        # conflicting_authorが既にold_nameと同名の別名を持っている場合、
        # マージ後にその別名をそのまま活かし、重複登録（IntegrityError）を起こさない。
        # 他のpast別名と同様に今後も選択候補になるよう、alias_typeは"past"へ揃える
        conflicting = Author.objects.create(name="以前の名義")
        existing_alias = AuthorAlias.objects.create(name="現在の名義", author=conflicting, alias_type="another")

        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "以前の名義")

        existing_alias.refresh_from_db()
        self.assertEqual(existing_alias.author_id, self.author.id)
        self.assertEqual(existing_alias.alias_type, "past")
        self.assertEqual(AuthorAlias.objects.filter(name="現在の名義").count(), 1)

    def test_merging_songs_query_count_does_not_scale_with_song_count(self):
        # conflicting_authorのSongをauthor.songs.add(*queryset)でまとめて付け替える
        # ことで、統合対象の曲数が増えてもクエリ数がほぼ変わらないことを確認する。
        # Editor.get_or_create_from_ip()はIPごとに最初の1回だけINSERTが発生するため、
        # 計測対象のリクエストより前にウォームアップしてクエリ数の比較に影響しないようにする
        warmup_author = Author.objects.create(name="ウォームアップ用作者")
        AuthorAlias.objects.create(name="ウォームアップ用別名", author=warmup_author, alias_type="past")
        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[warmup_author.id]),
            {"name": "ウォームアップ用別名"},
        )

        author_one_song = Author.objects.create(name="現在の名義A")
        AuthorAlias.objects.create(name="以前の名義A", author=author_one_song, alias_type="past")
        conflicting_one_song = Author.objects.create(name="以前の名義A")
        Song.objects.create(title="曲A").authors.add(conflicting_one_song)

        with CaptureQueriesContext(connection) as ctx_one_song:
            self.client.post(
                reverse("subekashi:author_primary_name_set", args=[author_one_song.id]),
                {"name": "以前の名義A"},
            )

        author_many_songs = Author.objects.create(name="現在の名義B")
        AuthorAlias.objects.create(name="以前の名義B", author=author_many_songs, alias_type="past")
        conflicting_many_songs = Author.objects.create(name="以前の名義B")
        for i in range(5):
            Song.objects.create(title=f"曲B{i}").authors.add(conflicting_many_songs)

        with CaptureQueriesContext(connection) as ctx_many_songs:
            self.client.post(
                reverse("subekashi:author_primary_name_set", args=[author_many_songs.id]),
                {"name": "以前の名義B"},
            )

        self.assertEqual(len(ctx_one_song.captured_queries), len(ctx_many_songs.captured_queries))


    def test_merge_records_history_with_merged_author_info(self):
        conflicting = Author.objects.create(name="以前の名義")
        conflicting_id = conflicting.id

        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        merge_row = next((row for row in history.changes if row[0] == "統合したAuthor"), None)
        self.assertIsNotNone(merge_row)
        self.assertIn(f"id={conflicting_id}", merge_row[1])

    def test_merge_does_not_modify_conflicting_authors_own_history(self):
        # マージ対象Authorの過去のHistoryは改変しない（Author自体はon_delete=SET_NULLで
        # authorがNULLになるだけで、Historyの内容自体は保持される）
        conflicting = Author.objects.create(name="以前の名義")
        other_editor = Editor.objects.create(ip="127.0.0.9")
        old_history = History.create_for_author(
            author=conflicting, title="別名を追加", history_type="edit", changes=None, editor=other_editor,
        )

        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        old_history.refresh_from_db()
        self.assertIsNone(old_history.author)
        self.assertEqual(old_history.title, "別名を追加")

    def test_post_creates_history_with_before_and_after_names(self):
        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "edit")
        self.assertIn("以前の名義", history.title)
        self.assertEqual(history.changes[1], ["一番有名な名義", "現在の名義", "以前の名義"])

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("現在の名義", content)
        self.assertIn("以前の名義", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_notification_mentions_merged_author(self, mock_send_discord):
        conflicting = Author.objects.create(name="以前の名義")
        mock_send_discord.return_value = True

        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        content = mock_send_discord.call_args[0][1]
        self.assertIn(f"Author(id={conflicting.id})", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_conflicting_author_deleted_concurrently_during_discord_wait_still_succeeds(self, mock_send_discord):
        # send_discord()の完了を待つ間に、統合対象のconflicting_authorが別のリクエストで
        # 削除されてしまうケース。マージ部分をスキップして通常の名義切り替えとして完了する
        conflicting = Author.objects.create(name="以前の名義")

        def delete_conflicting_then_succeed(url, content):
            conflicting.delete()
            return True

        mock_send_discord.side_effect = delete_conflicting_then_succeed

        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "以前の名義")

    @patch("subekashi.views.author_alias.send_discord")
    def test_unrelated_alias_matching_old_name_created_during_discord_wait_is_not_corrupted(self, mock_send_discord):
        # send_discord()の待機中に、マージ対象(conflicting_author)とは無関係な別authorが
        # old_nameと同名のAuthorAliasを新規作成してしまうケース（TOCTOU）。
        # マージにより付け替わったものと誤認して所有者チェックなしに再利用（alias_typeの
        # 書き換え）してしまうと、無関係な別authorのデータを破壊することになるため、
        # 安全側に倒して統合全体をロールバックすることを確認する
        conflicting = Author.objects.create(name="以前の名義")
        unrelated_author = Author.objects.create(name="無関係な作者")

        def create_unrelated_alias_then_succeed(url, content):
            AuthorAlias.objects.create(name="現在の名義", author=unrelated_author, alias_type="another")
            return True

        mock_send_discord.side_effect = create_unrelated_alias_then_succeed

        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        # マージ・名義変更ともにロールバックされる
        self.assertTrue(Author.objects.filter(pk=conflicting.pk).exists())
        # 無関係な別名は書き換えられない
        unrelated_alias = AuthorAlias.objects.get(name="現在の名義")
        self.assertEqual(unrelated_alias.author_id, unrelated_author.id)
        self.assertEqual(unrelated_alias.alias_type, "another")

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_prevents_name_change(self, mock_send_discord):
        mock_send_discord.return_value = False
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        self.assertEqual(response.status_code, 500)
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    @patch("subekashi.views.author_alias.send_discord")
    def test_alias_deleted_concurrently_during_discord_wait_redirects_with_error(self, mock_send_discord):
        # send_discord()（ネットワークI/O）の完了を待つ間に、別のリクエストが対象の
        # past別名を削除してしまうケースを、send_discordのside_effectで模擬する。
        # DoesNotExistが未処理の例外(500)にならず、他の異常系と同じくtoast=primary_error
        # へ穏当にリダイレクトされることを確認する
        def delete_alias_then_succeed(url, content):
            self.past_alias.delete()
            return True

        mock_send_discord.side_effect = delete_alias_then_succeed

        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    def test_old_name_conflicting_with_existing_alias_is_rejected_before_discord(self):
        # AuthorAlias.nameはグローバルにuniqueなため、旧名(old_name)が既に別のauthorの
        # 別名として登録されている場合、以前の名称として再登録できずIntegrityErrorになる。
        # これは同時実行のレースではなく既存データ次第で毎回決定的に失敗するため、
        # Discord通知を送る前に弾く（通知だけ成功してDBが更新されない不整合を避ける）
        other = Author.objects.create(name="別の作者")
        AuthorAlias.objects.create(name=self.author.name, author=other, alias_type="another")

        with patch("subekashi.views.author_alias.send_discord") as mock_send_discord:
            response = self.client.post(
                reverse("subekashi:author_primary_name_set", args=[self.author.id]),
                {"name": "以前の名義"},
            )
            self.assertFalse(mock_send_discord.called)

        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())

    def test_alias_list_page_shows_primary_name_form_when_past_alias_exists(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, 'id="primary-name-form"')
        self.assertContains(response, "一番有名な名義")

    def test_alias_list_page_hides_primary_name_form_when_no_past_alias(self):
        # フォーム本体（HTML要素）が描画されないことを確認する。判定用JS自体は
        # フォームの有無に関わらず読み込まれ、要素が存在しない場合は何もせず
        # no-opする実装のため、bareな文字列一致ではなくid属性の有無で判定する
        author = Author.objects.create(name="別名なし作者")
        response = self.client.get(reverse("subekashi:author_aliases", args=[author.id]))
        self.assertNotContains(response, 'id="primary-name-form"')

    def test_primary_name_submit_button_is_disabled_and_labeled_change(self):
        # 初期状態（現在の名義が選択されたまま）では変更不要なためボタンはdisabled、
        # ラベルは「変更する」（#1029）
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, 'id="primary-name-submit"')
        self.assertContains(response, "変更する")
        content = response.content.decode()
        submit_button = content[
            content.index('id="primary-name-submit"'):content.index("</button>", content.index('id="primary-name-submit"'))
        ]
        self.assertIn("disabled", submit_button)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorPrimaryNameConfirmViewTest(TestCase):
    """AuthorPrimaryNameConfirmView (/authors/<id>/aliases/primary/confirm) のテスト（#1029）

    衝突するAuthorが存在する場合に自動的にマージ・削除されてしまうことへの安全策として、
    実際の変更前に内容を確認できる画面を経由させるためのビュー。
    """
    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="現在の名義")
        self.past_alias = AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[99999]), {"name": "以前の名義"}
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_name_redirects_with_error(self):
        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "全く関係ない名前"}
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )

    def test_current_name_redirects_to_alias_list_without_confirmation(self):
        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": self.author.name}
        )
        self.assertRedirects(response, reverse("subekashi:author_aliases", args=[self.author.id]))

    def test_shows_confirmation_without_merge_warning_when_no_conflict(self):
        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "現在の名義")
        self.assertContains(response, "以前の名義")
        self.assertNotContains(response, "削除されます")

    def test_shows_merge_warning_when_conflicting_author_exists(self):
        conflicting = Author.objects.create(name="以前の名義")
        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"id={conflicting.id}")
        self.assertContains(response, "削除されます")

    def test_confirmation_page_does_not_modify_any_data(self):
        Author.objects.create(name="以前の名義")
        self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertEqual(Author.objects.count(), 2)

    def test_no_songs_falls_back_to_plain_message(self):
        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )
        self.assertContains(response, "名義を『以前の名義』に変更されます")

    def test_shows_affected_song_titles(self):
        song = Song.objects.create(title="変更対象の曲")
        song.authors.add(self.author)

        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )

        self.assertContains(response, "変更対象の曲")
        self.assertContains(response, "の名義を『以前の名義』に変更されます")

    def test_shows_conflicting_authors_song_titles_too(self):
        conflicting = Author.objects.create(name="以前の名義")
        conflicting_song = Song.objects.create(title="統合対象作者の曲")
        conflicting_song.authors.add(conflicting)

        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )

        self.assertContains(response, "統合対象作者の曲")

    def test_song_shared_by_both_authors_is_not_listed_twice(self):
        # 同じ曲がauthor・conflicting_author双方の共著になっている場合、
        # 曲タイトルが確認画面に重複して表示されないことを確認する
        conflicting = Author.objects.create(name="以前の名義")
        shared_song = Song.objects.create(title="共著の曲")
        shared_song.authors.add(self.author, conflicting)

        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )

        self.assertEqual(response.content.decode().count("共著の曲"), 1)

    def test_save_button_is_labeled_change_with_fixed_width(self):
        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )
        self.assertContains(response, "変更する")
        self.assertContains(response, "dummybutton-w140")
        self.assertNotContains(response, "保存する")

    def test_show_all_songs_button_hidden_when_ten_or_fewer_songs(self):
        # ボタンのid文字列自体はno-opなJS（要素が無ければ何もしない）内にも常に
        # 出現するため、実際のbutton要素・li要素のクラス属性の有無で判定する
        for i in range(10):
            Song.objects.create(title=f"曲{i}").authors.add(self.author)

        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )

        self.assertNotContains(response, 'id="primary-name-show-all-songs"')
        self.assertNotContains(response, 'class="primary-name-song-hidden"')

    def test_show_all_songs_button_shown_and_hides_songs_past_ten(self):
        for i in range(11):
            Song.objects.create(title=f"曲{i}").authors.add(self.author)

        response = self.client.get(
            reverse("subekashi:author_primary_name_confirm", args=[self.author.id]), {"name": "以前の名義"}
        )

        self.assertContains(response, 'id="primary-name-show-all-songs"')
        self.assertContains(response, "全て表示")
        self.assertEqual(response.content.decode().count('class="primary-name-song-hidden"'), 1)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class ChannelViewTest(TestCase):
    """ChannelView (/channel/<name>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="チャンネルリダイレクト作者")

    def test_existing_author_redirects(self):
        response = self.client.get(
            reverse("subekashi:channel", args=["チャンネルリダイレクト作者"])
        )
        self.assertEqual(response.status_code, 302)

    def test_redirect_destination_is_author_page(self):
        response = self.client.get(
            reverse("subekashi:channel", args=["チャンネルリダイレクト作者"])
        )
        expected_url = reverse("subekashi:author", args=[self.author.id])
        self.assertRedirects(response, expected_url)

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(
            reverse("subekashi:channel", args=["存在しない作者名XYZ"])
        )
        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class ContactViewTest(TestCase):
    """ContactView (/contact/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:contact"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_form_returns_ok(self):
        # SEND_DISCORD=False のため send_discord は即 True を返す
        response = self.client.post(
            reverse("subekashi:contact"),
            {"category": "不具合の報告", "detail": "テスト詳細文"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result"], "ok")

    def test_post_valid_form_creates_contact_record(self):
        # 自動登録によりContactレコードが作成されること
        self.client.post(
            reverse("subekashi:contact"),
            {"category": "不具合の報告", "detail": "テスト詳細文"},
        )
        self.assertTrue(Contact.objects.filter(detail="テスト詳細文").exists())

    def test_post_invalid_form_returns_error(self):
        # detail が未入力の場合はフォームバリデーションエラー
        response = self.client.post(
            reverse("subekashi:contact"),
            {"category": "不具合の報告"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("入力必須項目", response.context["result"])

    def test_post_invalid_form_does_not_create_contact_record(self):
        count_before = Contact.objects.count()
        self.client.post(
            reverse("subekashi:contact"),
            {"category": "不具合の報告"},
        )
        self.assertEqual(Contact.objects.count(), count_before)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class HistoriesViewTest(TestCase):
    """HistoriesView (/histories/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:histories"))
        self.assertEqual(response.status_code, 200)

    def test_author_history_links_to_author_page_not_deleted_message(self):
        # author向けのHistory(song=None)が「この曲は削除されました」と誤表示されないことを確認する
        editor = Editor.objects.create(ip="127.0.0.2")
        author = Author.objects.create(name="履歴一覧テスト作者")
        History.create_for_author(
            author=author, title="別名を追加", history_type="edit", changes=None, editor=editor,
        )

        response = self.client.get(reverse("subekashi:histories"))

        self.assertContains(response, "履歴一覧テスト作者")
        self.assertNotContains(response, "この曲は削除されました")

    def test_author_deleted_after_history_shows_deleted_message(self):
        editor = Editor.objects.create(ip="127.0.0.3")
        author = Author.objects.create(name="削除される作者")
        History.create_for_author(
            author=author, title="作者削除", history_type="delete", changes=["理由", "テスト"], editor=editor,
        )
        author.delete()

        response = self.client.get(reverse("subekashi:histories"))

        self.assertContains(response, "この曲または作者は削除されました")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE, RATELIMIT_ENABLE=False)
class SongCardsViewTest(TestCase):
    """SongCardsView (/api/html/song_cards) のテスト"""

    def setUp(self):
        self.client = Client()
        Song.objects.create(title="カードテスト曲", lyrics="歌詞")

    def test_sort_upload_time_shows_search_info(self):
        """sort=upload_time のとき「YouTubeの曲を表示しています」が含まれること"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"sort": "upload_time"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("YouTubeの曲を表示しています", content)

    def test_sort_minus_upload_time_shows_search_info(self):
        """sort=-upload_time のとき「YouTubeの曲を表示しています」が含まれること"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"sort": "-upload_time"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("YouTubeの曲を表示しています", content)

    def test_no_sort_does_not_show_upload_time_search_info(self):
        """sort指定なしのとき投稿日用のsearch-infoが含まれないこと"""
        response = self.client.get(reverse("subekashi:song_cards"))
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertNotIn("YouTubeの曲を表示しています", content)

    def test_other_sort_does_not_show_upload_time_search_info(self):
        """sort=title のとき投稿日用のsearch-infoが含まれないこと"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"sort": "title"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertNotIn("YouTubeの曲を表示しています", content)

    def test_questionable_song_card_hides_lyrics(self):
        """is_questionable=True の曲のカードには .song-card-lyrics が含まれないこと"""
        Song.objects.create(title="界隈曲カードテスト", is_questionable=True)
        response = self.client.get(
            reverse("subekashi:song_cards"), {"keyword": "界隈曲カードテスト"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertNotIn("song-card-lyrics", content)

    def test_normal_song_card_shows_lyrics(self):
        """is_questionable=False の曲のカードには .song-card-lyrics が含まれること"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"keyword": "カードテスト曲"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("song-card-lyrics", content)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class RedirectViewTest(TestCase):
    """/search/ と /new/ のリダイレクトテスト"""

    def setUp(self):
        self.client = Client()

    def test_search_redirects_to_songs(self):
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/songs/", fetch_redirect_response=False)

    def test_new_redirects_to_songs_new(self):
        response = self.client.get("/new/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/songs/new/", fetch_redirect_response=False)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AdViewTest(TestCase):
    """AdView (/ad/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:ad"))
        self.assertEqual(response.status_code, 200)

    def test_post_with_unregistered_previous_ad_does_not_error(self):
        """
        cookieに残った旧宣伝URLがAdレコードとして存在しない場合でも
        AttributeErrorにならず正常に処理されること（Issue #985）
        """
        previous_ad_url = "https://www.youtube.com/watch?v=aaaaaaaaaaa"
        response = self.client.post(
            reverse("subekashi:ad"),
            {
                "url1": "",
                "ad1": previous_ad_url,
                "url2": "",
                "ad2": "",
                "url3": "",
                "ad3": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("subekashi:ad_complete"))

    def test_post_valid_new_ad_redirects_and_increments_dup(self):
        # SEND_DISCORD=False のため send_discord は即 True を返す
        new_ad_url = "https://www.youtube.com/watch?v=bbbbbbbbbbb"
        response = self.client.post(
            reverse("subekashi:ad"),
            {
                "url1": new_ad_url,
                "ad1": "",
                "url2": "",
                "ad2": "",
                "url3": "",
                "ad3": "",
            },
        )
        self.assertRedirects(response, reverse("subekashi:ad_complete"))
        adIns = Ad.objects.get(url="https://youtu.be/bbbbbbbbbbb")
        self.assertEqual(adIns.dup, 1)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AiViewTest(TestCase):
    """AiView (/ai/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:ai"))
        self.assertEqual(response.status_code, 200)

    def test_show_janome_notice_default_true(self):
        response = self.client.get(reverse("subekashi:ai"))
        self.assertTrue(response.context["show_janome_notice"])
        self.assertContains(response, "id=\"janome-notice\"")

    def test_show_janome_notice_false_when_cookie_set(self):
        # base.js の setCookie() は JSON.stringify() で保存するため、実際に送信される
        # Cookie値は show_janome_notice="off" のようにクォート付きになる。
        # Djangoの parse_cookie() はRFC 6265のquoted cookie-valueとしてクォートを
        # 自動的に取り除くため、request.COOKIES側ではクォートなしの"off"として
        # 受け取れることをここで確認する。
        response = self.client.get(reverse("subekashi:ai"), HTTP_COOKIE='show_janome_notice="off"')
        self.assertFalse(response.context["show_janome_notice"])
        self.assertNotContains(response, "id=\"janome-notice\"")

    def test_best_lyric_is_plain_text_even_with_matching_word_candidate(self):
        # 方針転換（#1053）により、最高評価の歌詞では単語入れ替え機能を提供しない。
        # Word候補が存在していてもクリック可能なトークンにはならない
        Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")
        Ai.objects.create(lyrics="私は走る", score=5, genetype="janome")

        response = self.client.get(reverse("subekashi:ai"))

        self.assertNotContains(response, 'class="word-token"')
        self.assertContains(response, "私は走る")

    def test_legacy_model_genetype_is_excluded_from_best_lyrics(self):
        # レガシーのGPTインポート（genetype="model"）は廃止されたため、
        # スコア5であっても最高評価の歌詞には表示されない
        Ai.objects.create(lyrics="レガシー歌詞", score=5, genetype="model")

        response = self.client.get(reverse("subekashi:ai"))

        self.assertNotContains(response, "レガシー歌詞")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AiResultViewTest(TestCase):
    """AiResultView (/ai/result/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:ai_result"))
        self.assertEqual(response.status_code, 200)

    def test_lyric_word_with_candidate_is_rendered_as_clickable_token(self):
        Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")
        Ai.objects.create(lyrics="私は走る", score=0, genetype="janome")

        response = self.client.get(reverse("subekashi:ai_result"))

        self.assertContains(response, 'class="word-token"')
        self.assertContains(response, 'data-word="走る"')

    def test_legacy_model_genetype_is_excluded_from_result_queue(self):
        # レガシーのGPTインポート（genetype="model"）は廃止されたため、
        # 未評価（score=0）であっても作成結果キューには表示されない
        Ai.objects.create(lyrics="レガシー歌詞", score=0, genetype="model")

        response = self.client.get(reverse("subekashi:ai_result"))

        self.assertNotContains(response, "レガシー歌詞")

    def test_falls_back_to_scored_janome_when_none_unscored(self):
        # 未評価のjanomeレコードが1件も無くても、単語入れ替えの元になる歌詞が
        # 途絶えないよう、評価済みのjanomeレコードにフォールバックして表示する。
        # janomeはトークンごとに別々の<span>に分割して描画するため、複数語の
        # 文字列だとテンプレート上で分断され、そのままの形では現れない。
        # そのため単一トークンになる語（りんご）を使って検証する。
        Ai.objects.create(lyrics="りんご", score=3, genetype="janome")

        response = self.client.get(reverse("subekashi:ai_result"))

        self.assertContains(response, "りんご")

    def test_fallback_still_excludes_legacy_model_genetype(self):
        # フォールバック時であっても、レガシーのgenetype="model"は対象に含めない
        Ai.objects.create(lyrics="レガシー歌詞", score=5, genetype="model")

        response = self.client.get(reverse("subekashi:ai_result"))

        self.assertNotContains(response, "レガシー歌詞")

    def test_lyric_tokens_render_without_whitespace_between_spans(self):
        # 「最高の行をコピー」はDOMのinnerTextをそのままコピーするため、
        # トークン間に空白文字が入っているとコピー結果にも余分なスペースが
        # 混ざってしまう。{% spaceless %}によりタグ間の空白が除去され、
        # 単語同士が隙間なく連結して描画されることを確認する（#1081）
        Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")
        Ai.objects.create(lyrics="私は走る", score=0, genetype="janome")

        response = self.client.get(reverse("subekashi:ai_result"))
        content = response.content.decode()

        lyric_match = re.search(r'<p class="lyric"[^>]*>(.*?)</p>', content, re.DOTALL)
        self.assertIsNotNone(lyric_match)
        self.assertNotRegex(lyric_match.group(1), r">\s+<")
