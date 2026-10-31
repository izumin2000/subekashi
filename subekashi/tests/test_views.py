"""
ビューの HTTP レスポンステスト

各ページの基本的なアクセス可否・ステータスコード・リダイレクト先を検証する。
ManifestStaticFilesStorage はテストに不要なため StaticFilesStorage に差し替える。
"""
import io
import json
import os
import re
import socket
import tempfile
import threading
from urllib.parse import quote, urlparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from PIL import Image
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core import signing
from django.core.cache import cache
from django.db import connection
from django.template.loader import render_to_string
from django.test import TestCase, TransactionTestCase, Client, RequestFactory, override_settings, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from article.models import Article
from subekashi.forms import AuthorAliasForm
from subekashi.constants.constants import HISTORIES_PER_PAGE, LONG_TERM_COOKIE_AGE, SHORT_TERM_COOKIE_AGE, SORT_CHOICES
from subekashi.lib.ogp import OGP_SALT, OGP_VERSION, load_ogp_token, make_ogp_token, render_ogp_image
from subekashi.lib.query_utils import YOUTUBE_FILTERS, YOUTUBE_SORTS
from subekashi.lib.security import encrypt
from subekashi.lib.song_service import restore_song
from subekashi.lib.youtube import YoutubeApiError
from subekashi.models import Ad, Ai, Author, AuthorAlias, AuthorLink, Contact, Editor, History, Prush, Song, SongLink, SongTimeline, Stats, Word
from subekashi.models.author import TransitiveAlias
from subekashi.views.songs import COOKIE_FORMS, SEARCH_FORM_QUERIES, TEXT_FORMS


STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

MANIFEST_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}


@override_settings(STORAGES=STATIC_STORAGE)
class TopViewTest(TestCase):
    """TopView (/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertEqual(response.status_code, 200)

    def test_toast_delete_shows_toast(self):
        # 曲を削除した後はトップに遷移し、トーストを表示する（#1239）
        response = self.client.get(reverse("subekashi:top"), {"toast": "delete"})
        self.assertContains(response, 'showToast("ok", "曲を削除しました。");')

    def test_toast_delete_notify_error_shows_warning_toast(self):
        # 削除はできたがDiscordへの通知に失敗した場合は、500ページにせず警告のトーストを表示する（#1239）
        response = self.client.get(reverse("subekashi:top"), {"toast": "delete_notify_error"})
        self.assertContains(response, 'showToast("warning", "曲を削除しましたが、管理者への通知に失敗しました。");')

    def test_no_toast_does_not_show_delete_toast(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertNotContains(response, "曲を削除しました")

    def test_viewport_meta_has_no_stray_attribute(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<meta name="viewport" content="width=device-width,')
        self.assertNotContains(response, 'meta=""')

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

    def test_linked_article_title_link_is_removed(self):
        """リンクでくくる記事は、<a>が入れ子にならないようタイトル中のリンクを外す（#483）"""
        article = Article.objects.create(
            article_id="release-link", title="[リンク](https://example.com)と**太字**", tag="release",
            post_time=timezone.now(), is_open=True,
        )
        response = self.client.get(reverse("subekashi:top"))
        url = reverse("article:default_article", args=[article.article_id])
        self.assertContains(response, f"<span><a href='{url}'>リンクと<strong>太字</strong></a></span>")

    def test_news_tag_article_title_link_is_kept(self):
        """リンクでくくらないニュースは、タイトル中のリンクをそのまま表示する（#483）"""
        Article.objects.create(
            article_id="news-link", title="[リンク](https://example.com)のニュース", tag="news",
            post_time=timezone.now(), is_open=True,
        )
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<span><a href="https://example.com">リンク</a>のニュース</span>')

    def test_single_news_has_dots(self):
        """ニュースの「1つずつ表示」では、top.jsで切り替えのボタンを入れる要素を置く（#1116）"""
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<div id="single-news-display">')
        self.assertContains(response, '<div id="single-news-dots"></div>')

    def test_all_news_has_no_dots(self):
        """ニュースの「一度に全て表示」では、切り替えのボタンを入れる要素を置かない（#1116）"""
        self.client.cookies["news_type"] = "all"
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<div id="all-news-display">')
        self.assertNotContains(response, 'id="single-news-dots"')

    def test_pc_global_header_is_in_pc_header_menu(self):
        """メニュー位置がトップの場合、PC向けグローバルヘッダーは#pc-header-menuの中に1つだけ置かれる（#1123）"""
        response = self.client.get(reverse("subekashi:top"))
        content = response.content.decode()

        self.assertEqual(content.count('id="pc-global-header"'), 1)
        pc_header_menu = re.search(r'<nav id="pc-header-menu">.*?</nav>', content, re.DOTALL).group()
        self.assertIn('id="pc-global-header"', pc_header_menu)

    def test_pc_global_header_is_above_subekashi_header_when_aside(self):
        """メニュー位置がサイドの場合、PC向けグローバルヘッダーは#subekashi-headerの上に1つだけ置かれる（#1123）"""
        self.client.cookies["pc_menu_position"] = "aside"
        response = self.client.get(reverse("subekashi:top"))
        content = response.content.decode()

        self.assertEqual(content.count('id="pc-global-header"'), 1)
        self.assertNotIn('id="pc-header-menu"', content)
        self.assertLess(content.index('id="pc-global-header"'), content.index('id="subekashi-header"'))

    def test_footers_have_privacy_policy_link(self):
        """PCのフッターとスマホメニューのフッターに、プライバシーポリシーの記事へのリンクがある（#1170）"""
        response = self.client.get(reverse("subekashi:top"))
        content = response.content.decode()
        privacy_url = reverse("article:default_article", args=["privacy"])
        self.assertEqual(privacy_url, "/articles/privacy/")

        footers = {
            "pc": r'<div id="footer-wrapper">.*?</footer>',
            "sp": r'<footer id="sp-menu-footer">.*?</footer>',
        }
        for name, pattern in footers.items():
            with self.subTest(footer=name):
                footer = re.search(pattern, content, re.DOTALL).group()
                self.assertIn(f'<a href="{privacy_url}"><i class="fas fa-shield-alt"></i>プライバシーポリシー</a>', footer)

    def _create_upcoming_song(self, title, days, **kwargs):
        return Song.objects.create(title=title, upload_time=timezone.now() + timedelta(days=days), **kwargs)

    def test_upcoming_songs_are_shown_in_upload_time_order(self):
        """投稿予定には、YouTubeの投稿日が未来の曲のみを投稿日の早い順に表示する（#376）"""
        later = self._create_upcoming_song("後の投稿予定", 3)
        sooner = self._create_upcoming_song("先の投稿予定", 1)
        self._create_upcoming_song("投稿済み", -1)
        Song.objects.create(title="投稿日なし")

        response = self.client.get(reverse("subekashi:top"))

        self.assertContains(response, "<h1>投稿予定</h1>")
        self.assertEqual(list(response.context["upcomingInsL"]), [sooner, later])

    def test_upcoming_section_is_hidden_without_upcoming_songs(self):
        """投稿日が未来の曲が無い場合は、投稿予定の見出しを表示しない（#376）"""
        self._create_upcoming_song("投稿済み", -1)

        response = self.client.get(reverse("subekashi:top"))

        self.assertNotContains(response, "<h1>投稿予定</h1>")

    def test_upcoming_count_follows_cookie(self):
        """投稿予定の曲数は設定（is_shown_upcoming）に従い、cookieが無い場合は5曲、非表示(0)の場合は見出しも表示しない（#376）"""
        for days in range(1, 12):
            self._create_upcoming_song(f"投稿予定{days}", days)

        cases = [(None, 5), ("5", 5), ("10", 10), ("15", 11)]
        for value, count in cases:
            with self.subTest(value=value):
                self.client.cookies.clear()
                if value:
                    self.client.cookies["is_shown_upcoming"] = value
                response = self.client.get(reverse("subekashi:top"))
                self.assertEqual(len(response.context["upcomingInsL"]), count)

        self.client.cookies["is_shown_upcoming"] = "0"
        response = self.client.get(reverse("subekashi:top"))
        self.assertNotIn("upcomingInsL", response.context)
        self.assertNotContains(response, "<h1>投稿予定</h1>")

    def test_upcoming_with_invalid_cookie_shows_default_count(self):
        """投稿予定の設定のcookieが不正な値の場合は、エラーにせず5曲表示する（#376）"""
        for days in range(1, 7):
            self._create_upcoming_song(f"投稿予定{days}", days)

        for value in ["3", "abc", "<script>"]:
            with self.subTest(value=value):
                self.client.cookies["is_shown_upcoming"] = value
                response = self.client.get(reverse("subekashi:top"))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context["upcomingInsL"]), 5)

    def test_upcoming_follows_songrange_and_jokerange(self):
        """投稿予定も新着・未完成と同じく、トップ画面の界隈曲・ネタ曲の表示設定に従う（#376）"""
        subeana = self._create_upcoming_song("界隈曲の投稿予定", 1)
        xx = self._create_upcoming_song("界隈曲以外の投稿予定", 2, is_subeana=False)
        joke = self._create_upcoming_song("ネタ曲の投稿予定", 3, is_joke=True)

        response = self.client.get(reverse("subekashi:top"))
        self.assertEqual(list(response.context["upcomingInsL"]), [subeana])

        self.client.cookies["songrange"] = "all"
        self.client.cookies["jokerange"] = "on"
        response = self.client.get(reverse("subekashi:top"))
        self.assertEqual(list(response.context["upcomingInsL"]), [subeana, xx, joke])

    def test_upcoming_excludes_removed_songs(self):
        """削除した曲（#1239）は投稿予定に表示しない（#376）"""
        self._create_upcoming_song("削除した投稿予定", 1, is_removed=True)

        response = self.client.get(reverse("subekashi:top"))

        self.assertNotContains(response, "<h1>投稿予定</h1>")

    def test_upcoming_more_link_searches_from_today(self):
        """投稿予定の「もっと見る」は、今日以降に投稿（予定）の曲を投稿日の早い順で、保存設定を上書きせずに検索する（#376）"""
        self._create_upcoming_song("投稿予定", 1)

        response = self.client.get(reverse("subekashi:top"))

        today = timezone.localdate().isoformat()
        self.assertContains(response, f'<a href="/songs/?upload_time_gte={today}&sort=upload_time&save_select=off" class="action-button black-action-button">')

    def _get_search_form_html(self, response):
        match = re.search(r'<form action="/songs/" method="GET" id="search-form">.*?</form>', response.content.decode(), re.DOTALL)
        return match.group() if match else None

    def test_search_shows_keyword_only_by_default(self):
        """検索の表示設定のcookieが無い場合、キーワードのみの検索フォームが表示される（#585）"""
        response = self.client.get(reverse("subekashi:top"))
        form_html = self._get_search_form_html(response)

        self.assertEqual(response.context["is_shown_search"], "on")
        self.assertIn('<input type="text" id="keyword" name="keyword" placeholder="タイトル・チャンネル名・歌詞・URL">', form_html)
        self.assertNotIn('id="search-form-radios"', form_html)
        self.assertNotContains(response, "subekashi/js/search_form.js")

    def test_search_shows_keyword_only_when_on(self):
        """検索の表示設定が「キーワードのみ」(on)の場合、キーワードのみの検索フォームが表示される（#585）"""
        self.client.cookies["is_shown_search"] = "on"
        response = self.client.get(reverse("subekashi:top"))
        form_html = self._get_search_form_html(response)

        self.assertIn('id="keyword"', form_html)
        self.assertNotIn('id="search-forms"', form_html)

    def test_search_is_hidden_when_off(self):
        """検索の表示設定が「非表示」(off)の場合、検索フォームは表示されない（#585）"""
        self.client.cookies["is_shown_search"] = "off"
        response = self.client.get(reverse("subekashi:top"))

        self.assertNotContains(response, "<h1>検索</h1>")
        self.assertIsNone(self._get_search_form_html(response))
        self.assertNotContains(response, "subekashi/js/search_form.js")

    def test_search_shows_all_forms_when_all(self):
        """検索の表示設定が「全て表示」(all)の場合、検索画面と同じフォームが表示され、キーワードのフォームが初期表示される（#585）"""
        self.client.cookies["is_shown_search"] = "all"
        response = self.client.get(reverse("subekashi:top"))
        form_html = self._get_search_form_html(response)

        radios = re.findall(r'id="search-form-radio-(\w+)"', form_html)
        self.assertEqual(radios, list(SEARCH_FORM_QUERIES))
        self.assertEqual(re.findall(r'name="search-form" value="(\w+)" checked>', form_html), ["keyword"])
        self.assertIn('<div class="search-form" id="search-form-keyword" >', form_html)
        self.assertIn('<div class="search-form" id="search-form-title" hidden>', form_html)
        self.assertIn('<input type="text" id="keyword" name="keyword" placeholder="タイトル・作者・歌詞・URL" value="">', form_html)
        self.assertIn('id="search-form-radios-toggle"', form_html)
        self.assertIn('<script id="youtube-queries" type="application/json">', form_html)
        self.assertIn('<input type="submit" value="検索" id="searchsubmit">', form_html)

    def test_all_search_loads_search_form_js_before_top_js(self):
        """「全て表示」の場合、トップ画面のJSより先に検索フォームのJSが読み込まれる（#585）"""
        self.client.cookies["is_shown_search"] = "all"
        content = self.client.get(reverse("subekashi:top")).content.decode()

        self.assertLess(content.index("subekashi/js/search_form.js"), content.index("subekashi/js/top.js"))

    def test_is_shown_all_search_matches_search_form_js(self):
        """top.jsに渡すisShownAllSearchは、search_form.jsを読み込む場合のみtrueになる（#585）"""
        for value, expected in [("all", "true"), ("on", "false"), ("off", "false"), ("invalid", "false")]:
            with self.subTest(value=value):
                self.client.cookies["is_shown_search"] = value
                content = self.client.get(reverse("subekashi:top")).content.decode()

                self.assertEqual(re.findall(r"const isShownAllSearch = (\w+);", content), [expected])
                self.assertEqual("subekashi/js/search_form.js" in content, expected == "true")

    def test_search_form_css_is_loaded_only_when_all(self):
        """検索フォームのCSSは「全て表示」の場合のみ、トップ画面のCSSより先に読み込まれる（#585）"""
        for value, is_loaded in [("all", True), ("on", False), ("off", False)]:
            with self.subTest(value=value):
                self.client.cookies["is_shown_search"] = value
                content = self.client.get(reverse("subekashi:top")).content.decode()

                self.assertEqual("subekashi/css/components/search_form.css" in content, is_loaded)
                if is_loaded:
                    self.assertLess(content.index("subekashi/css/components/search_form.css"), content.index("subekashi/css/top.css"))

    def test_all_search_has_no_csrf_token(self):
        """「全て表示」の検索フォームはGETで送信するため、CSRFトークンを含まない（#585）"""
        self.client.cookies["is_shown_search"] = "all"
        response = self.client.get(reverse("subekashi:top"))

        self.assertNotIn("csrfmiddlewaretoken", self._get_search_form_html(response))

    def test_all_search_reflects_saved_select_cookies(self):
        """「全て表示」の場合、検索画面と同じく保存された並び替え・界隈曲・ネタ曲の選択肢と、フォームボタンの設定が反映される（#585）"""
        self.client.cookies["is_shown_search"] = "all"
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_sort"] = "-view"
        self.client.cookies["search_songrange"] = "subeana"
        self.client.cookies["search_jokerange"] = "off"
        self.client.cookies["form_button"] = "icon"
        response = self.client.get(reverse("subekashi:top"))
        form_html = self._get_search_form_html(response)

        self.assertEqual(re.findall(r'name="sort" value="([^"]*)" checked>', form_html), ["-view"])
        self.assertEqual(re.findall(r'name="songrange" value="([^"]*)"[^>]*checked>', form_html), ["subeana"])
        self.assertEqual(re.findall(r'name="jokerange" value="([^"]*)"[^>]*checked>', form_html), ["off"])
        self.assertIn('<div class="radio-group icon-only" id="search-form-radios">', form_html)

    def test_all_search_reflects_saved_categorys_cookie(self):
        """「全て表示」の場合、検索画面と同じく保存されたカテゴリの選択が反映される（#423）"""
        self.client.cookies["is_shown_search"] = "all"
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_categorys"] = "arrange,~meme"
        response = self.client.get(reverse("subekashi:top"))
        form_html = self._get_search_form_html(response)
        self.assertEqual(re.findall(r'name="category_(\w+)" value="(True|False)" checked>', form_html), [("arrange", "True"), ("meme", "False")])

    def test_all_search_uses_default_when_saved_select_is_off(self):
        """「全て表示」の場合、検索の選択肢の保存がoffなら、保存された選択肢ではなくデフォルト値が選択される（#585）"""
        self.client.cookies["is_shown_search"] = "all"
        self.client.cookies["is_saved_select"] = "off"
        self.client.cookies["search_sort"] = "-view"
        self.client.cookies["search_songrange"] = "subeana"
        response = self.client.get(reverse("subekashi:top"))
        form_html = self._get_search_form_html(response)

        self.assertEqual(re.findall(r'name="sort" value="([^"]*)" checked>', form_html), ["-post_time"])
        self.assertEqual(re.findall(r'name="songrange" value="([^"]*)"[^>]*checked>', form_html), ["all"])

    def test_all_search_ignores_url_query_and_does_not_save_cookies(self):
        """「全て表示」の場合、トップ画面のURLクエリはフォームの選択・入力欄に使われず、検索の選択肢のcookieも保存されない（#585）"""
        self.client.cookies["is_shown_search"] = "all"
        self.client.cookies["is_saved_select"] = "on"
        query = {"sort": "-view", "songrange": "xx", "is_lack": "True", "mediatypes": "youtube"}
        query.update({name: "2024-01-01" for name in TEXT_FORMS})
        response = self.client.get(reverse("subekashi:top"), query)
        form_html = self._get_search_form_html(response)

        self.assertEqual(response.context["search_form"], "keyword")
        self.assertEqual(re.findall(r'name="sort" value="([^"]*)" checked>', form_html), ["-post_time"])
        self.assertEqual(re.findall(r'name="is_lack" value="([^"]*)"[^>]*checked>', form_html), [""])
        self.assertEqual(re.findall(r'id="media-[^"]+" checked>', form_html), [])
        for name in TEXT_FORMS:
            with self.subTest(name=name):
                self.assertEqual(re.findall(rf'<input [^>]*name="{name}"[^>]*value="([^"]*)"', form_html), [""])
        for name in ["search_sort", "search_songrange", "search_jokerange"]:
            self.assertNotIn(name, response.cookies)

    def test_all_search_selects_same_radios_as_songs_without_query(self):
        """「全て表示」のフォームで表示時に選択されるラジオボタンは、URLクエリが無い検索画面と一致する（#585）

        top.jsは表示時から選択を変更していないラジオボタンをURLクエリに含めないため、検索画面で同じ値が選択される必要がある
        """
        saved_cookies = {"search_sort": "-view", "search_songrange": "subeana", "search_jokerange": "off"}
        invalid_cookies = {"search_sort": "invalid", "search_songrange": "invalid", "search_jokerange": "invalid"}
        cases = [
            ("cookieなし", {}),
            ("保存on", {"is_saved_select": "on", **saved_cookies}),
            ("保存off", {"is_saved_select": "off", **saved_cookies}),
            ("保存onで不正な値", {"is_saved_select": "on", **invalid_cookies}),
        ]
        checked_pattern = r'name="(sort|songrange|jokerange|is_\w+)" value="([^"]*)"[^>]*checked>'
        for label, cookies in cases:
            with self.subTest(label):
                self.client.cookies.clear()
                for name, value in cookies.items():
                    self.client.cookies[name] = value
                self.client.cookies["is_shown_search"] = "all"
                top_checked = re.findall(checked_pattern, self._get_search_form_html(self.client.get(reverse("subekashi:top"))))
                songs_checked = re.findall(checked_pattern, self.client.get(reverse("subekashi:songs")).content.decode())

                self.assertEqual(top_checked, songs_checked)
                self.assertEqual(len(top_checked), 11)

    def test_search_with_invalid_cookie_is_keyword_only(self):
        """検索の表示設定のcookieが不正な値の場合、キーワードのみの検索フォームが表示される（#585）"""
        for value in ["keyword", "ALL", "<script>"]:
            with self.subTest(value=value):
                self.client.cookies["is_shown_search"] = value
                response = self.client.get(reverse("subekashi:top"))
                form_html = self._get_search_form_html(response)

                self.assertEqual(response.context["is_shown_search"], "on")
                self.assertIn('id="keyword"', form_html)
                self.assertNotIn('id="search-forms"', form_html)
                self.assertNotContains(response, "subekashi/js/search_form.js")
                self.assertNotContains(response, "subekashi/css/components/search_form.css")

    def test_guide_is_shown_first_by_default(self):
        """初心者向け案内は、cookieが無い場合に、画面の幅いっぱいに表示するため本文（#mainarticle）より前のファーストビューに表示される（#1236）"""
        response = self.client.get(reverse("subekashi:top"))
        content = response.content.decode()

        self.assertTrue(response.context["is_shown_guide"])
        self.assertContains(response, '<h2 class="guide-line">このサイトについて</h2>')
        self.assertContains(response, '<h2 class="guide-line">界隈曲とは</h2>')
        self.assertContains(response, '<h2 class="guide-line">すべあな界隈曲とは</h2>')
        self.assertLess(content.index('id="guide"'), content.index('<article id="mainarticle">'))

    def test_guide_close_button_is_below_image(self):
        """初心者向け案内の「表示しない」ボタンは、背景の画像（#guide-image）の下に置く（#1236）"""
        response = self.client.get(reverse("subekashi:top"))
        guide = BeautifulSoup(response.content, "html.parser").find(id="guide")
        button = guide.find(id="guide-close")

        self.assertContains(response, '<button type="button" id="guide-close" class="action-button black-action-button"><i class="fas fa-times"></i><span class="icon-p-big">表示しない</span></button>', count=1)
        self.assertIsNone(guide.find(id="guide-image").find(id="guide-close"))
        self.assertIn(button.parent, guide.find(id="guide-image").find_next_siblings())

    def test_guide_passes_cookie_age_to_top_js(self):
        """「表示しない」ボタンで閉じたときのcookieの保存期間を、インラインのスクリプトのグローバル変数ではなく#guideのdata-cookie-ageでtop.jsに渡す（#1236）"""
        response = self.client.get(reverse("subekashi:top"))
        guide = BeautifulSoup(response.content, "html.parser").find(id="guide")

        self.assertEqual(guide["data-cookie-age"], str(LONG_TERM_COOKIE_AGE))
        self.assertNotContains(response, "guideCookieAge")

    def test_guide_is_hidden_when_closed(self):
        """「表示しない」ボタンで閉じた（is_shown_guide=off）場合、初心者向け案内は表示しない（#1236）"""
        self.client.cookies["is_shown_guide"] = "off"
        response = self.client.get(reverse("subekashi:top"))

        self.assertFalse(response.context["is_shown_guide"])
        self.assertNotContains(response, 'id="guide"')
        self.assertNotContains(response, "data-cookie-age")

    def test_guide_with_invalid_cookie_is_shown(self):
        """is_shown_guideがoff以外の値の場合、初心者向け案内を表示する（#1236）"""
        for value in ["on", "OFF", "<script>"]:
            with self.subTest(value=value):
                self.client.cookies["is_shown_guide"] = value
                response = self.client.get(reverse("subekashi:top"))

                self.assertTrue(response.context["is_shown_guide"])
                self.assertContains(response, 'id="guide"')

    def test_guide_background_image_exists(self):
        """top.cssで初心者向け案内の背景にする画像が静的ファイルにある（#1236）"""
        with open(finders.find("subekashi/css/top.css"), encoding="utf-8") as f:
            image_paths = re.findall(r'url\("\.\./(image/guide[^"]*)"\)', f.read())

        self.assertEqual(image_paths, ["image/guide.webp"])
        self.assertIsNotNone(finders.find("subekashi/image/guide.webp"))


@override_settings(STORAGES=STATIC_STORAGE)
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
        """is_draft=True (大文字) で下書きのみになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "True"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["is_draft"], "True")

    def test_bool_query_param_1_sets_context(self):
        """is_draft=1 で下書きのみになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["is_draft"], "True")

    def test_bool_query_param_false_uppercase_sets_context(self):
        """is_draft=False (大文字) で下書き以外になること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "False"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["is_draft"], "False")

    def test_bool_query_param_0_sets_context(self):
        """is_draft=0 で下書き以外になること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "0"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["is_draft"], "False")

    def test_bool_query_param_invalid_value_is_not_filtered(self):
        """is_draft に真偽値以外を指定した場合はフィルタなしになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("is_draft", response.context)

    def test_bool_query_param_false_selects_false_radio(self):
        """is_lack=False のとき「以外」のラジオボタンが選択された状態で表示されること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_lack": "False"})
        self.assertContains(response, '<input type="radio" id="is_lack-false" name="is_lack" value="False" checked>')
        self.assertContains(response, '<label for="is_lack-false"><i class="fas fa-not-equal"></i><span class="icon-p-big">以外</span></label>')

    def test_bool_query_param_not_specified_selects_all_radio(self):
        """is_lack を指定しないとき「指定なし」のラジオボタンが選択された状態で表示されること"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertContains(response, '<input type="radio" id="is_lack-all" name="is_lack" value="" data-default checked>')
        self.assertContains(response, '<label for="is_lack-all"><i class="fas fa-expand"></i><span class="icon-p-big">指定なし</span></label>')

    def test_bool_filters_are_not_duplicated(self):
        """インスト曲・オリジナル模倣曲は、それぞれ1つのフォームにのみ表示されること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_inst": "True", "is_original": "False"})
        self.assertContains(response, '<input type="radio" id="is_inst-true" name="is_inst" value="True" checked>', count=1)
        self.assertContains(response, '<input type="radio" id="is_original-false" name="is_original" value="False" checked>', count=1)

    def test_is_special_query_param_selects_true_radio(self):
        """is_special=True のときスペシャルデザインのフォームで「のみ」のラジオボタンが選択された状態で表示されること（#939）"""
        response = self.client.get(reverse("subekashi:songs"), {"is_special": "True"})
        self.assertContains(response, '<label for="search-form-radio-special"><i class="fas fa-magic"></i><span class="icon-p-big">スペシャルデザイン</span></label>')
        self.assertContains(response, '<input type="radio" id="is_special-true" name="is_special" value="True" checked>', count=1)

    def test_is_collab_query_param_selects_true_radio(self):
        """is_collab=True のとき合作のフォームで「のみ」のラジオボタンが選択された状態で表示されること（#943）"""
        response = self.client.get(reverse("subekashi:songs"), {"is_collab": "True"})
        self.assertContains(response, '<label for="search-form-radio-collab"><i class="fas fa-user-friends"></i><span class="icon-p-big">合作</span></label>')
        self.assertContains(response, '<input type="radio" id="is_collab-true" name="is_collab" value="True" checked>', count=1)

    def test_imitate_form_label_is_imitate_source(self):
        """模倣のフォームは入力した曲を模倣元に持つ曲で絞り込むため、「模倣元」と模倣元のアイコンで表示されること（#1241）"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertContains(response, '<label for="search-form-radio-imitate"><i class="fas fa-sitemap imitate"></i><span class="icon-p-big">模倣元</span></label>', count=1)
        self.assertContains(response, '<label for="imitate"><i class="fas fa-sitemap imitate"></i><span class="icon-p-big">模倣元</span></label>', count=1)

    def test_songrange_and_jokerange_are_radio(self):
        """界隈曲の種類・ネタ曲はラジオボタンで選択された状態で表示されること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_subeana": "xx", "is_joke": "False"})
        self.assertContains(response, '<input type="radio" id="songrange-xx" name="songrange" value="xx" checked>')
        self.assertContains(response, '<label for="songrange-xx"><i class="fas fa-not-equal"></i><span class="icon-p-big">以外</span></label>')
        self.assertContains(response, '<input type="radio" id="jokerange-off" name="jokerange" value="off" checked>')
        self.assertContains(response, '<label for="jokerange-off"><i class="fas fa-not-equal"></i><span class="icon-p-big">以外</span></label>')

    def test_songrange_and_jokerange_default_radio(self):
        """界隈曲の種類・ネタ曲は指定がなければ「指定なし」のラジオボタンが選択されること"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertContains(response, '<input type="radio" id="songrange-all" name="songrange" value="all" data-default checked>')
        self.assertContains(response, '<input type="radio" id="jokerange-on" name="jokerange" value="on" data-default checked>')
        self.assertContains(response, '<label for="songrange-all"><i class="fas fa-expand"></i><span class="icon-p-big">指定なし</span></label>')
        self.assertContains(response, '<label for="jokerange-on"><i class="fas fa-expand"></i><span class="icon-p-big">指定なし</span></label>')

    def test_radio_labels_do_not_contain_hyouji(self):
        """検索フォームのラジオボタンの選択肢に「表示」が含まれないこと"""
        response = self.client.get(reverse("subekashi:songs"))
        content = response.content.decode()
        search_forms = content[content.index('<div id="search-forms">'):content.index('id="search-button"')]
        labels = re.findall(r'<label for="[^"]+"><i class="[^"]+"></i><span class="icon-p-big">([^<]+)</span></label>', search_forms)
        self.assertTrue(labels)
        for label in labels:
            self.assertNotIn("表示", label)

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
        """is_original/is_inst/is_questionable/is_special/is_collab/is_lack/is_deleted でもTrue/Falseが正しく変換されること"""
        for field in ["is_original", "is_inst", "is_questionable", "is_special", "is_collab", "is_lack", "is_deleted"]:
            for value in ["True", "False"]:
                with self.subTest(field=field, value=value):
                    response = self.client.get(reverse("subekashi:songs"), {field: value})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.context[field], value)

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

    def test_save_select_off_query_does_not_overwrite_saved_cookies(self):
        """save_select=offのURLクエリ（トップ画面の投稿予定の「もっと見る」等のリンク）の並び替え等は、表示にのみ反映しcookieには保存しない（#376）"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_sort"] = "-view"
        self.client.cookies["search_songrange"] = "subeana"
        response = self.client.get(reverse("subekashi:songs"), {"sort": "upload_time", "songrange": "xx", "save_select": "off"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sort"], "upload_time")
        self.assertEqual(response.context["songrange"], "xx")
        self.assertNotIn("search_sort", response.cookies)
        self.assertNotIn("search_songrange", response.cookies)

    def test_save_select_off_query_keeps_saved_select_for_other_forms(self):
        """save_select=offでも、URLクエリで指定していないフォームには保存した選択を使う（#376）"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_songrange"] = "subeana"
        self.client.cookies["search_jokerange"] = "off"
        response = self.client.get(reverse("subekashi:songs"), {"sort": "upload_time", "save_select": "off"})
        self.assertEqual(response.context["songrange"], "subeana")
        self.assertEqual(response.context["jokerange"], "off")

    def test_search_form_defaults_to_keyword(self):
        """URLクエリがない場合はキーワードのフォームが表示されること"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(response.context["search_form"], "keyword")
        self.assertContains(response, '<input type="radio" id="search-form-radio-keyword" name="search-form" value="keyword" checked>')
        self.assertContains(response, '<div class="search-form" id="search-form-keyword" >')
        self.assertContains(response, '<div class="search-form" id="search-form-title" hidden>')

    def test_search_form_selected_by_query(self):
        """URLクエリで指定されたフィルタを含むフォームが表示され、そのラジオボタンのみが選択されること"""
        cases = [
            ({}, "keyword"),
            ({"keyword": "テスト"}, "keyword"),
            ({"title": "テスト"}, "title"),
            ({"author": "テスト"}, "author"),
            ({"lyrics": "テスト"}, "lyrics"),
            ({"url": "https://youtu.be/xxx"}, "url"),
            ({"mediatypes": "youtube"}, "url"),
            ({"imitate": "1"}, "imitate"),
            ({"categorys": "arrange"}, "category"),
            ({"view_gte": "100"}, "youtube"),
            ({"upload_time_lte": "2024-01-01"}, "youtube"),
            ({"is_subeana": "xx"}, "subeana"),
            ({"songrange": "subeana"}, "subeana"),
            ({"is_joke": "only"}, "joke"),
            ({"jokerange": "off"}, "joke"),
            ({"is_original": "True"}, "original"),
            ({"is_inst": "True"}, "inst"),
            ({"is_questionable": "True"}, "questionable"),
            ({"is_special": "True"}, "special"),
            ({"is_collab": "True"}, "collab"),
            ({"is_deleted": "True"}, "deleted"),
            ({"is_lack": "True"}, "lack"),
            ({"is_draft": "True"}, "draft"),
            ({"sort": "-view"}, "sort"),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                response = self.client.get(reverse("subekashi:songs"), query)
                self.assertEqual(response.context["search_form"], expected)
                self.assertContains(response, f'<div class="search-form" id="search-form-{expected}" >')
                # JSは選択されているラジオボタンが必ず1つあることを前提にしている
                self.assertEqual(re.findall(r'name="search-form" value="(\w+)" checked>', response.content.decode()), [expected])

    def test_search_form_covers_all_forms(self):
        """全てのフォームのラジオボタンに、初期表示するためのURLクエリが対応づけられていること"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()
        radios = re.findall(r'id="search-form-radio-(\w+)"', content)
        self.assertEqual(radios, list(SEARCH_FORM_QUERIES))

    def test_invalid_bool_value_selects_default_radio(self):
        """真偽値のフィルタに不正な値を指定した場合は、そのフォームを表示し「指定なし」が選択されること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_lack": "foo"})
        self.assertEqual(response.context["search_form"], "lack")
        self.assertContains(response, '<input type="radio" id="is_lack-all" name="is_lack" value="" data-default checked>')
        self.assertEqual(re.findall(r'name="is_lack" value="([^"]*)"[^>]*checked>', response.content.decode()), [""])

    def test_mediatypes_query_checks_media(self):
        """mediatypesで指定したメディアのチェックボックスが選択された状態で表示されること"""
        response = self.client.get(reverse("subekashi:songs"), {"mediatypes": "youtube,nicovideo,unknown"})
        content = response.content.decode()
        checked = re.findall(r'<input type="checkbox" value="media-[^"]+" id="media-([^"]+)" checked>', content)
        self.assertCountEqual(checked, ["youtube", "nicovideo"])

    def test_no_mediatypes_query_checks_nothing(self):
        """mediatypesを指定しない場合はメディアのチェックボックスが選択されないこと"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()
        self.assertEqual(re.findall(r'id="media-[^"]+" checked>', content), [])

    def _get_category_selection(self, response):
        """カテゴリのラジオボタンで「のみ」（True）・「以外」（False）が選択されているカテゴリ（#423）"""
        selection = dict(re.findall(r'name="category_(\w+)" value="(True|False)" checked>', response.content.decode()))
        context_selection = {
            category_filter["category"]["value"]: category_filter["value"]
            for category_filter in response.context["category_filters"] if category_filter["value"]
        }
        self.assertEqual(selection, context_selection)
        return selection

    def test_category_form_shows_all_categorys(self):
        """#423: カテゴリのフォームに全てのカテゴリの指定なし・のみ・以外のラジオボタンを表示し、指定しない場合は指定なしを選択すること"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()
        category_values = [value for value, _ in Song.CHOICES]
        self.assertEqual(re.findall(r'<input type="radio" id="category_\w+-all" name="category_(\w+)" value="" data-default checked>', content), category_values)
        self.assertEqual(re.findall(r'<input type="radio" id="category_\w+-true" name="category_(\w+)" value="True" >', content), category_values)
        self.assertEqual(re.findall(r'<input type="radio" id="category_\w+-false" name="category_(\w+)" value="False" >', content), category_values)
        self.assertNotIn('type="checkbox" value="category-', content)

    def test_prush_form_has_prush_choices(self):
        """#1064: プレラのフォームは、指定なしと、年表でプレラが最初に出てくる日付の新しい順に年ごとに分けたプレラの選択肢にすること"""
        Prush.objects.create(name="年末プレラ５", date=date(2024, 12, 31))
        Prush.objects.create(name="日付が無いプレラ")
        Prush.objects.create(name="晩夏プレラ6", date=date(2025, 8, 20))
        Prush.objects.create(name="年末プレラ2", date=date(2021, 12, 31))
        Prush.objects.create(name="晩夏プレラ５", date=date(2024, 8, 20))
        response = self.client.get(reverse("subekashi:songs"))
        self.assertContains(response, '<label for="search-form-radio-prush"><i class="fas fa-angle-double-right"></i><span class="icon-p-big">プレラ</span></label>')
        content = response.content.decode()
        start = content.index('<select id="prush" name="prush">')
        select = content[start:content.index("</select>", start)]
        self.assertEqual(re.findall(r'<optgroup label="([^"]*)">', select), ["2025年", "2024年", "2021年", "年が不明"])
        self.assertEqual(
            re.findall(r'<option value="([^"]*)">', select),
            ["", "晩夏プレラ6", "年末プレラ５", "晩夏プレラ５", "年末プレラ2", "日付が無いプレラ"],
        )
        self.assertIn('<option value="">指定なし</option>', select)

    def test_prush_query_selects_prush_form(self):
        """#1064: prushのURLクエリ（曲ページのタグのリンク）では、プレラのフォームでそのプレラを選択した状態で表示すること"""
        Prush.objects.create(name="年末プレラ５")
        Prush.objects.create(name="晩夏プレラ6")
        response = self.client.get(reverse("subekashi:songs"), {"prush": "年末プレラ５"})
        self.assertEqual(response.context["search_form"], "prush")
        self.assertContains(response, '<option value="年末プレラ５" selected>年末プレラ５</option>')
        self.assertContains(response, '<option value="晩夏プレラ6">晩夏プレラ6</option>')

    def test_category_radio_has_icon(self):
        """#423: カテゴリのラジオボタンの見出しには、カテゴリのアイコンを付けること"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertContains(response, '<p class="radio-col-label"><i class="far fa-laugh-squint"></i><span class="icon-p-big">ネタ動画</span></p>')

    def test_categorys_query_selects_category(self):
        """#423: categorysで「のみ」のカテゴリと、先頭に~を付けた「以外」のカテゴリを選択した状態で表示すること（存在しないカテゴリは無視）"""
        response = self.client.get(reverse("subekashi:songs"), {"categorys": "arrange,~meme,unknown,~unknown"})
        self.assertEqual(self._get_category_selection(response), {"arrange": "True", "meme": "False"})

    def test_saved_categorys_cookie_selects_category(self):
        """#423: 検索の選択肢の保存がonの場合、URLクエリが無ければ保存したカテゴリの選択を表示すること"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_categorys"] = "arrange,~meme,unknown"
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(self._get_category_selection(response), {"arrange": "True", "meme": "False"})
        # 保存した選択を表示しただけでは、表示するフォームは切り替えない（並び替え等の保存した選択と同じ）
        self.assertEqual(response.context["search_form"], "keyword")

    def test_saved_categorys_cookie_ignored_when_saved_select_is_off(self):
        """#423: 検索の選択肢の保存がoffの場合、保存したカテゴリの選択は使わないこと"""
        self.client.cookies["is_saved_select"] = "off"
        self.client.cookies["search_categorys"] = "arrange"
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(self._get_category_selection(response), {})

    def test_categorys_query_overrides_saved_cookie_without_saving(self):
        """#423: URLクエリのcategorys（曲ページのタグのリンク等）は表示にのみ反映し、保存したカテゴリの選択を上書きしないこと"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_categorys"] = "meme"
        response = self.client.get(reverse("subekashi:songs"), {"categorys": "~arrange"})
        self.assertEqual(self._get_category_selection(response), {"arrange": "False"})
        self.assertNotIn("search_categorys", response.cookies)

    def test_post_categorys_saves_cookie(self):
        """#423: 検索画面でカテゴリの選択を変更したとき（songs.jsのPOST）は、選択肢にあるカテゴリのみをSONG_CATEGORIESの順でcookieに保存すること"""
        self.client.cookies["is_saved_select"] = "on"
        response = self.client.post(reverse("subekashi:songs"), {"categorys": "~meme,unknown,arrange"})
        self.assertEqual(response.cookies["search_categorys"].value, "arrange,~meme")
        self.assertEqual(response.cookies["search_categorys"]["max-age"], LONG_TERM_COOKIE_AGE)

    def test_post_empty_categorys_saves_empty_cookie(self):
        """#423: 全てのカテゴリを指定なしにしたときは、空の選択を保存すること（保存した選択に戻らないように）"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_categorys"] = "arrange"
        response = self.client.post(reverse("subekashi:songs"), {"categorys": ""})
        self.assertEqual(response.cookies["search_categorys"].value, "")
        self.assertEqual(self._get_category_selection(response), {})

    def test_post_categorys_not_saved_when_saved_select_is_off(self):
        self.client.cookies["is_saved_select"] = "off"
        response = self.client.post(reverse("subekashi:songs"), {"categorys": "arrange"})
        self.assertNotIn("search_categorys", response.cookies)

    def test_post_other_form_does_not_save_categorys(self):
        """#423: 並び替え等の変更では、カテゴリの選択を保存しないこと"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_categorys"] = "~arrange"
        response = self.client.post(reverse("subekashi:songs"), {"sort": "-view"})
        self.assertNotIn("search_categorys", response.cookies)
        self.assertEqual(self._get_category_selection(response), {"arrange": "False"})

    def test_search_form_prefers_earlier_form(self):
        """複数のフォームのURLクエリが指定された場合はラジオボタンの並び順で先のフォームが表示されること"""
        cases = [
            ({"is_lack": "True", "keyword": "テスト"}, "keyword"),
            ({"title": "テスト", "sort": "-view"}, "sort"),
            ({"title": "テスト", "view_gte": "100"}, "youtube"),
            ({"view_gte": "100", "lyrics": "テスト"}, "lyrics"),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                response = self.client.get(reverse("subekashi:songs"), query)
                self.assertEqual(response.context["search_form"], expected)

    def test_search_form_radio_order(self):
        """よく利用するフォームを先頭に、キーワード・並び替え・歌詞・YouTubeの順でラジオボタンが並ぶこと"""
        response = self.client.get(reverse("subekashi:songs"))
        radios = re.findall(r'id="search-form-radio-(\w+)"', response.content.decode())
        self.assertEqual(radios[:4], ["keyword", "sort", "lyrics", "youtube"])
        self.assertEqual(len(radios), 20)

    def test_search_form_ignores_empty_query(self):
        """値が空のURLクエリではフォームが切り替わらないこと"""
        response = self.client.get(reverse("subekashi:songs"), {"title": ""})
        self.assertEqual(response.context["search_form"], "keyword")

    def test_default_radio_has_data_default(self):
        """フィルタバッジはdata-defaultのラジオボタンをデフォルト値として判定するため、各フィルタでデフォルト値（指定なし）のラジオボタンにのみdata-defaultが付くこと"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()
        expected = {
            "songrange": COOKIE_FORMS["songrange"]["default"],
            "jokerange": COOKIE_FORMS["jokerange"]["default"],
            "is_original": "", "is_inst": "", "is_questionable": "", "is_special": "", "is_collab": "", "is_deleted": "", "is_lack": "", "is_draft": "",
        }
        for name, default in expected.items():
            with self.subTest(name=name):
                values = re.findall(rf'<input type="radio" id="[^"]+" name="{name}" value="([^"]*)" data-default', content)
                self.assertEqual(values, [default])

    def test_invalid_cookie_value_uses_default(self):
        """cookieに不正な値が保存されている場合はデフォルト値のラジオボタンが選択されること"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_songrange"] = "invalid"
        self.client.cookies["search_jokerange"] = "invalid"
        self.client.cookies["search_sort"] = "invalid"
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(response.context["songrange"], "all")
        self.assertEqual(response.context["jokerange"], "on")
        self.assertEqual(response.context["sort"], "-post_time")
        self.assertContains(response, 'name="songrange" value="all" data-default checked>')
        self.assertContains(response, 'name="jokerange" value="on" data-default checked>')
        self.assertContains(response, 'name="sort" value="-post_time" checked>')

    def test_sort_is_radio(self):
        """並び替えはラジオボタンで表示され、指定した並び替えが選択されること"""
        response = self.client.get(reverse("subekashi:songs"), {"sort": "-view"})
        content = response.content.decode()
        self.assertNotIn('<select id="sort"', content)
        self.assertEqual(len(re.findall(r'<input type="radio" id="sort-\d+" name="sort"', content)), len(SORT_CHOICES))
        self.assertEqual(re.findall(r'name="sort" value="([^"]*)" checked>', content), ["-view"])

    def test_sort_labels_have_youtube_icon(self):
        """並び替えのラベルは短く、YouTube関連の並び替えにのみYouTubeのアイコンが付くこと"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()
        labels = dict(re.findall(r'<label for="(sort-\d+)"><i class="[^"]+"></i><span class="icon-p-big">(.*?)</span></label>', content))
        self.assertEqual(labels["sort-1"], "登録日/早い順")
        self.assertEqual(labels["sort-4"], "更新日/遅い順")
        self.assertEqual(labels["sort-5"], '<i class="fab fa-youtube"></i>投稿日/早い順')
        self.assertEqual(labels["sort-8"], '<i class="fab fa-youtube"></i>再生回数/多い順')
        self.assertEqual(labels["sort-10"], '<i class="fab fa-youtube"></i>高評価数/多い順')
        self.assertEqual(labels["sort-12"], "模倣元の数/多い順")
        self.assertEqual(labels["sort-14"], "模倣曲の数/多い順")
        self.assertEqual(labels["sort-15"], "ランダム")
        self.assertNotIn("YouTubeの", "".join(labels.values()))

    def test_imitate_count_sort_labels_and_icons(self):
        """模倣元の数は上下反転した模倣のアイコン、模倣曲の数は通常の模倣のアイコンで表示されること（#542）"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()
        expected = {
            "imitate_count": ("fas fa-sitemap imitate", "模倣元の数/少ない順"),
            "-imitate_count": ("fas fa-sitemap imitate", "模倣元の数/多い順"),
            "imitated_count": ("fas fa-sitemap", "模倣曲の数/少ない順"),
            "-imitated_count": ("fas fa-sitemap", "模倣曲の数/多い順"),
        }
        for value, (icon, label) in expected.items():
            with self.subTest(value=value):
                match = re.search(
                    rf'<input type="radio" id="(sort-\d+)" name="sort" value="{re.escape(value)}"[^>]*>\s*'
                    r'<label for="\1"><i class="([^"]+)"></i><span class="icon-p-big">(.*?)</span></label>',
                    content,
                )
                self.assertIsNotNone(match)
                self.assertEqual(match.group(2), icon)
                self.assertEqual(match.group(3), label)

    def test_sort_defaults_to_post_time_desc(self):
        """並び替えを指定しない場合は「更新日が遅い順」が選択されること"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(re.findall(r'name="sort" value="([^"]*)" checked>', response.content.decode()), ["-post_time"])

    def test_youtube_queries_are_passed_to_js(self):
        """自動で適用されるフィルタの案内に使うYouTube関連のクエリが、サーバー側の定義のままJSに渡されること"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(response.context["youtube_queries"], {"filters": YOUTUBE_FILTERS, "sorts": YOUTUBE_SORTS})
        self.assertContains(response, '<script id="youtube-queries" type="application/json">')

    def test_search_form_radios_toggle_button_is_shown(self):
        """フォームを切り替えるラジオボタンを全て表示するボタンが、閉じた状態で表示されること"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertContains(response, '<button type="button" id="search-form-radios-toggle" aria-controls="search-form-radios" aria-expanded="false"><i class="fas fa-angle-down"></i><span>全て表示</span></button>')

    def test_form_button_shows_icon_and_text_by_default(self):
        """フォームボタンの設定のcookieが無い場合、フォームを切り替えるラジオボタンはアイコンと文字で表示されること（#1164）"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertContains(response, '<div class="radio-group" id="search-form-radios">')

    def test_form_button_shows_icon_only_when_set(self):
        """フォームボタンの設定がアイコンのみの場合、フォームを切り替えるラジオボタンにのみicon-onlyが付くこと（#1164）"""
        self.client.cookies["form_button"] = "icon"
        response = self.client.get(reverse("subekashi:songs"))

        self.assertEqual(response.context["form_button"], "icon")
        self.assertContains(response, '<div class="radio-group icon-only" id="search-form-radios">')
        self.assertContains(response, 'class="radio-group icon-only"', count=1)

    def test_form_button_with_invalid_cookie_falls_back_to_default(self):
        """フォームボタンの設定のcookieが不正な値の場合、デフォルトのアイコンと文字で表示されること（#1164）"""
        self.client.cookies["form_button"] = "text"
        response = self.client.get(reverse("subekashi:songs"))

        self.assertEqual(response.context["form_button"], "icon_text")
        self.assertContains(response, '<div class="radio-group" id="search-form-radios">')

    def test_scroll_to_results_button_is_removed(self):
        """「結果を表示」ボタン(scroll-to-results)が表示されないこと"""
        response = self.client.get(reverse("subekashi:songs"))
        self.assertNotContains(response, "scroll-to-results")

    def test_search_form_css_is_loaded_before_songs_css(self):
        """検索フォームのCSSが、検索画面のCSSより先に読み込まれること（#585）"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()

        self.assertLess(content.index("subekashi/css/components/search_form.css"), content.index("subekashi/css/songs.css"))

    def test_search_form_css_is_not_loaded_on_other_pages(self):
        """検索フォームのCSSは、検索フォームが無いページでは読み込まれないこと（#585）"""
        for url in [reverse("subekashi:setting"), reverse("subekashi:song_new")]:
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), "subekashi/css/components/search_form.css")

    def test_text_forms_cover_all_inputs(self):
        """URLクエリを初期値にする入力欄（TEXT_FORMS）が、フォームの文字・数値・日付の入力欄と一致すること（#585）"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()
        inputs = re.findall(r'<input type="(?:text|number|date)" id="[^"]+" name="([^"]+)"', content)
        self.assertCountEqual(inputs, TEXT_FORMS)

    def test_text_forms_reflect_url_query(self):
        """入力欄にURLクエリの値がエスケープされて入ること（#585）"""
        response = self.client.get(reverse("subekashi:songs"), {name: f'{name}"<b>' for name in TEXT_FORMS})
        content = response.content.decode()
        for name in TEXT_FORMS:
            with self.subTest(name=name):
                self.assertEqual(response.context["form_values"][name], f'{name}"<b>')
                self.assertEqual(re.findall(rf'<input [^>]*name="{name}"[^>]*value="([^"]*)"', content), [f"{name}&quot;&lt;b&gt;"])

    def test_search_form_js_is_loaded_before_songs_js(self):
        """トップ画面と共通の検索フォームのJSが、検索画面のJSより先に読み込まれること（#585）"""
        content = self.client.get(reverse("subekashi:songs")).content.decode()
        self.assertLess(content.index("subekashi/js/search_form.js"), content.index("subekashi/js/songs.js"))


@override_settings(STORAGES=STATIC_STORAGE)
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

    @override_settings(GOOGLE_SHEETS_SPREADSHEET_ID="sheet-id")
    def test_timeline_button_opens_row(self):
        # #1269: 年表に載っている曲は、編集履歴の右隣に、年表のシートの行を選択した状態で開くボタンを表示する
        SongTimeline.objects.create(song=self.song, year=2024, sheet_id=123, row=45, is_lyrics_blank=False)
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        content = response.content.decode()
        button = '<a href="https://docs.google.com/spreadsheets/d/sheet-id/edit#gid=123&amp;range=45:45" class="action-button" target="_blank"><i class="fas fa-table"></i><span class="icon-p-big">年表で見る</span></a>'

        self.assertIn(button, content)
        self.assertLess(content.index("編集履歴"), content.index(button))
        self.assertNotContains(response, "年表に登録する")

    @override_settings(GOOGLE_SHEETS_SPREADSHEET_ID="sheet-id")
    def test_timeline_register_button_when_lyrics_blank(self):
        # #1269: URL列で一致した行の歌詞列が空の曲は、曲のページのURLをコピーしてから、歌詞列のセルを選択した状態で年表を開く
        SongTimeline.objects.create(song=self.song, year=2024, sheet_id=123, row=45, is_lyrics_blank=True)
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        content = response.content.decode()
        button = (
            '<a href="https://docs.google.com/spreadsheets/d/sheet-id/edit#gid=123&amp;range=O45" id="timeline-register" class="action-button" target="_blank" '
            f'data-song-url="{settings.ROOT_URL}/songs/{self.song.id}/"><i class="fas fa-table"></i><i class="fas fa-exclamation small-icon"></i><span class="icon-p-big">年表に登録する</span></a>'
        )

        self.assertIn(button, content)
        self.assertLess(content.index("編集履歴"), content.index(button))
        self.assertNotContains(response, "年表で見る")
        # コピーしてから開く処理は、CSPのnonceを付けたscriptのaddEventListenerで行う（onclickを使わない）
        self.assertContains(response, "document.getElementById('timeline-register')?.addEventListener('click'")
        # コピーを待った後のwindow.openはSafariでブロックされることがあるため、開けなければこのタブで開く
        self.assertContains(response, 'const timelineTab = window.open(link.href, "_blank");')
        self.assertContains(response, "location.href = link.href;")

    @override_settings(GOOGLE_SHEETS_SPREADSHEET_ID="sheet-id")
    def test_no_timeline_button_without_timeline_row(self):
        # 年表に載っていない曲（timelineコマンドで一致する行が無い曲）には表示しない
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertNotContains(response, "年表で見る")
        self.assertNotContains(response, "年表に登録する")

    @override_settings(GOOGLE_SHEETS_SPREADSHEET_ID="")
    def test_no_timeline_button_without_spreadsheet_id(self):
        SongTimeline.objects.create(song=self.song, year=2024, sheet_id=123, row=45, is_lyrics_blank=True)
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertNotContains(response, "年表で見る")
        self.assertNotContains(response, "年表に登録する")

    def _add_link(self, url):
        SongLink.objects.create(url=url).songs.add(self.song)

    def _get_song_content(self, **cookies):
        self.client.cookies.load(cookies)
        return self.client.get(reverse("subekashi:song", args=[self.song.id])).content.decode()

    def test_embed_is_shown_above_lyrics(self):
        # #1254: 公式がiframeでの埋め込みに対応しているURLは、歌詞の上にdetailsで埋め込む
        self._add_link("https://youtu.be/dQw4w9WgXcQ")
        content = self._get_song_content()

        self.assertIn('<details id="embed" data-cookie-age="', content)
        self.assertIn('<summary><i class="fas fa-play-circle"></i><span class="icon-p">埋め込み</span>YouTube</summary>', content)
        self.assertIn(
            '<iframe class="embed-frame embed-video" src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ" title="YouTubeの埋め込み" loading="lazy"',
            content,
        )
        self.assertLess(content.index('<details id="embed"'), content.index('<div id="lyrics-wrapper">'))

    def test_embed_is_below_imitate_details(self):
        self._add_link("https://youtu.be/dQw4w9WgXcQ")
        self.song.imitates.add(Song.objects.create(title="模倣元の曲"))
        content = self._get_song_content()
        self.assertLess(content.index('<span class="icon-p">模倣元</span>'), content.index('<details id="embed"'))

    def test_embed_is_shown_without_lyrics(self):
        Song.objects.filter(pk=self.song.pk).update(lyrics="")
        self._add_link("https://youtu.be/dQw4w9WgXcQ")
        content = self._get_song_content()
        self.assertIn('<details id="embed"', content)
        self.assertNotIn('<div id="lyrics-wrapper">', content)

    def test_embeds_of_multiple_links(self):
        self._add_link("https://youtu.be/dQw4w9WgXcQ")
        self._add_link("https://nicovideo.jp/watch/sm12345678")
        self._add_link("https://soundcloud.com/artist/track-name")
        content = self._get_song_content()

        self.assertEqual(content.count('<iframe class="embed-frame'), 3)
        self.assertIn('src="https://embed.nicovideo.jp/watch/sm12345678"', content)
        self.assertIn('class="embed-frame embed-audio" src="https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist%2Ftrack-name&amp;visual=false"', content)
        summary = content[content.index('<span class="icon-p">埋め込み</span>'):]
        summary = summary[:summary.index("</summary>")]
        for name in ["YouTube", "ニコニコ動画", "SoundCloud"]:
            self.assertIn(name, summary)

    def test_embed_origins_are_allowed_by_response_csp(self):
        # #1254: 埋め込めないURLは除き、埋め込んだiframeのオリジンは、ページのCSPのframe-srcに含まれる
        for url in [
            "https://youtu.be/dQw4w9WgXcQ",
            "https://x.com/user/status/1234567890",
            "https://nicovideo.jp/watch/sm12345678",
            "https://booth.pm/ja/items/1",
            "https://soundcloud.com/artist/track-name",
        ]:
            self._add_link(url)
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        srcs = re.findall(r'<iframe class="embed-frame [^"]*" src="([^"]+)"', response.content.decode())
        frame_src = next(
            directive.split()[1:] for directive in response["Content-Security-Policy"].split(";") if directive.strip().startswith("frame-src")
        )

        self.assertEqual(len(srcs), 3)
        for src in srcs:
            parsed_src = urlparse(src)
            self.assertIn(f"{parsed_src.scheme}://{parsed_src.netloc}", frame_src)
        self.assertEqual(sorted(urlparse(src).netloc for src in srcs), ["embed.nicovideo.jp", "w.soundcloud.com", "www.youtube-nocookie.com"])

    def test_no_embed_without_embeddable_link(self):
        # #1254: 埋め込めないURLだけの曲・URLが無い曲には、埋め込みの欄を表示しない
        self.assertNotIn('id="embed"', self._get_song_content())
        self._add_link("https://x.com/user/status/1234567890")
        content = self._get_song_content()
        self.assertNotIn('id="embed"', content)
        self.assertNotIn("<iframe", content)

    def test_embed_is_open_by_default(self):
        self._add_link("https://youtu.be/dQw4w9WgXcQ")
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertTrue(response.context["is_shown_embed"])
        self.assertRegex(response.content.decode(), r'<details id="embed" data-cookie-age="\d+" open>')

    def test_embed_is_closed_by_cookie(self):
        # #1254: 閉じた状態はis_shown_embed=offのcookieに保存され、次に開いたときも閉じたままにする
        self._add_link("https://youtu.be/dQw4w9WgXcQ")
        self.client.cookies["is_shown_embed"] = "off"
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        content = response.content.decode()

        self.assertFalse(response.context["is_shown_embed"])
        self.assertRegex(content, r'<details id="embed" data-cookie-age="\d+">')
        self.assertIn('<iframe class="embed-frame', content)

    def test_embed_is_open_with_other_cookie_values(self):
        # offのみ閉じる。on・不正な値は開く
        self._add_link("https://youtu.be/dQw4w9WgXcQ")
        for value in ["on", "OFF", "<script>"]:
            with self.subTest(value=value):
                self.client.cookies["is_shown_embed"] = value
                response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
                self.assertTrue(response.context["is_shown_embed"])
                self.assertRegex(response.content.decode(), r'<details id="embed" data-cookie-age="\d+" open>')

    def test_embed_cookie_is_saved_by_toggle_script(self):
        # 開閉の保存は、CSPのnonceを付けたscriptのaddEventListenerで行う（onclickを使わない）。cookieの保存期間はdata属性で渡す
        self._add_link("https://youtu.be/dQw4w9WgXcQ")
        content = self._get_song_content()

        self.assertIn(f'<details id="embed" data-cookie-age="{LONG_TERM_COOKIE_AGE}"', content)
        self.assertIn("embedEle.addEventListener('toggle'", content)
        self.assertIn("document.cookie = `is_shown_embed=${embedEle.open ? 'on' : 'off'}; path=/; max-age=${embedEle.dataset.cookieAge}; samesite=lax`;", content)
        self.assertNotIn("onclick", content[content.index('<details id="embed"'):content.index("</details>", content.index('<details id="embed"'))])

    def test_removed_song_shows_removed_page(self):
        # ユーザーが削除した曲（#1239）のページは、曲の情報を表示せず、削除を取り消すボタンを表示する（#1264）
        self.song.lyrics = "削除した曲の歌詞テスト"
        self.song.is_removed = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))

        assert_song_removed_page(self, response)
        self.assertContains(response, "<h1>詳細テスト曲のページは削除されました</h1>", status_code=410)
        self.assertNotContains(response, "削除した曲の歌詞テスト", status_code=410)
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">', status_code=410)

    def test_toast_restore_shows_toast(self):
        # 削除を取り消した後は曲のページに遷移し、トーストを表示する（#1264）
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]), {"toast": "restore"})
        self.assertContains(response, 'showToast("ok", "削除を取り消しました。");')

    def test_toast_restore_notify_error_shows_warning_toast(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]), {"toast": "restore_notify_error"})
        self.assertContains(response, 'showToast("warning", "削除を取り消しましたが、管理者への通知に失敗しました。");')

    def test_imitate_lists_exclude_removed_song(self):
        removed = Song.objects.create(title="削除した模倣関係の曲", is_removed=True)
        self.song.imitates.add(removed)
        removed.imitates.add(self.song)
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertNotContains(response, "削除した模倣関係の曲")
        self.assertEqual(list(response.context["imitate_list"]), [])
        self.assertEqual(list(response.context["imitated_list"]), [])

    def test_edit_button_label_is_edit_or_delete(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, '<span class="icon-p-big">編集/削除</span>')
        self.assertNotContains(response, "削除申請")

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

    def _make_complete(self):
        """未完成でない曲にする（URL・歌詞・模倣元がある）"""
        link = SongLink.objects.create(url="https://youtu.be/abcdefghijk")
        link.songs.add(self.song)
        self.song.imitates.add(Song.objects.create(title="模倣元の曲"))

    def _get_tags_html(self, **fields):
        Song.objects.filter(pk=self.song.pk).update(**fields)
        content = self.client.get(reverse("subekashi:song", args=[self.song.id])).content.decode()
        if '<tr id="tags">' not in content:
            return None
        start = content.index('<tr id="tags">')
        return content[start:content.index("</tr>", start)]

    def test_tags_not_shown_without_flags(self):
        """#1228: フラグがない曲はタグ欄を表示しないこと"""
        self._make_complete()
        self.assertIsNone(self._get_tags_html())

    def test_tags_shown_with_only_special(self):
        """#1228: スペシャルデザインのフラグだけの曲もタグ欄を表示すること"""
        self._make_complete()
        tags = self._get_tags_html(is_special=True)
        self.assertIn('<p class="special-tag"><i class="fas fa-magic"></i><span class="icon-p-big">スペシャルデザイン</span></p>', tags)

    def test_lack_tag_links_to_search(self):
        """#1228: 未完成の曲は、未完成の曲の検索へのリンクをタグに表示すること"""
        tags = self._get_tags_html()
        self.assertIn(f'<a href="{reverse("subekashi:songs")}?is_lack=True"><i class="fas fa-tasks"></i><span class="icon-p-big">未完成</span></a>', tags)

    def test_field_tag_links_to_search(self):
        """#1228: フィールドのフラグは、検索へのリンクをタグに表示すること"""
        self._make_complete()
        tags = self._get_tags_html(is_draft=True, is_subeana=False)
        self.assertIn(f'<a href="{reverse("subekashi:songs")}?is_draft=True"><i class="fas fa-user-edit"></i><span class="icon-p-big">下書き</span></a>', tags)
        self.assertIn(f'<a href="{reverse("subekashi:songs")}?is_subeana=xx"><i class="fas fa-fish"></i><span class="icon-p-big">非すべあな模倣曲</span></a>', tags)

    def test_tutorial_tags(self):
        """#1228: 界隈曲?・限定公開のタグには説明のアイコンを付け、リンクにしないこと"""
        tags = self._get_tags_html(is_questionable=True, is_limited=True)
        self.assertIn('<p class="special-tag"><i class="fas fa-question"></i><span class="icon-p-big">界隈曲?</span><i class="fas fa-info-circle" data-tutorial="is_questionable"></i></p>', tags)
        self.assertIn('<p class="special-tag"><i class="fas fa-low-vision"></i><span class="icon-p-big">限定公開</span><i class="fas fa-info-circle" data-tutorial="is_limited"></i></p>', tags)

    def test_questionable_non_subeana_has_no_xx_tag(self):
        """#1228: 界隈曲?の非すべあな曲には、非すべあな模倣曲のタグを表示しないこと"""
        tags = self._get_tags_html(is_questionable=True, is_subeana=False)
        self.assertIn("界隈曲?", tags)
        self.assertNotIn("非すべあな模倣曲", tags)

    def test_category_tag_links_to_search(self):
        """#423: カテゴリが曲以外の曲は、そのカテゴリの検索へのリンクをタグの先頭に表示すること"""
        tags = self._get_tags_html(category="arrange", is_questionable=True)
        category_tag = f'<a href="{reverse("subekashi:songs")}?categorys=arrange"><i class="fas fa-sliders-h"></i><span class="icon-p-big">アレンジ</span></a>'
        self.assertIn(category_tag, tags)
        self.assertLess(tags.index(category_tag), tags.index("界隈曲?"))

    def test_tags_shown_with_only_category(self):
        """#423: フラグがなくても、カテゴリが曲以外の曲はタグ欄を表示すること"""
        self._make_complete()
        tags = self._get_tags_html(category="meme")
        self.assertIn(f'<a href="{reverse("subekashi:songs")}?categorys=meme"><i class="far fa-laugh-squint"></i><span class="icon-p-big">ネタ動画</span></a>', tags)

    def test_prush_tag_links_to_search(self):
        """#1064: プレラがある曲は、そのプレラの検索へのリンクをタグに表示すること"""
        self._make_complete()
        prush = Prush.objects.create(name="端午プレラ6 / 端午クソ動画投稿祭6")
        tags = self._get_tags_html(prush=prush)
        self.assertIn(
            f'<a href="{reverse("subekashi:songs")}?prush={quote(prush.name, safe="/")}"><i class="fas fa-angle-double-right"></i><span class="icon-p-big">端午プレラ6 / 端午クソ動画投稿祭6</span></a>',
            tags,
        )

    def test_song_category_tag_not_shown(self):
        """#423: カテゴリが曲の曲には、カテゴリのタグを表示しないこと"""
        tags = self._get_tags_html()
        self.assertIn("未完成", tags)
        self.assertNotIn("categorys=", tags)

    def test_tags_order(self):
        """#1228: タグは界隈曲?・未完成・下書き・限定公開の順に並ぶこと"""
        tags = self._get_tags_html(is_questionable=True, is_draft=True, is_limited=True)
        self.assertLess(tags.index("界隈曲?"), tags.index("未完成"))
        self.assertLess(tags.index("未完成"), tags.index("下書き"))
        self.assertLess(tags.index("下書き"), tags.index("限定公開"))

    def _get_imitate_details_html(self, summary):
        """模倣元・模倣曲のdetailsの見出しから、次の模倣曲のdetails・歌詞の手前までのHTML"""
        content = self.client.get(reverse("subekashi:song", args=[self.song.id])).content.decode()
        start = content.index(f'<span class="icon-p">{summary}</span>')
        ends = [content.find(marker, start + 1) for marker in ['<span class="icon-p">模倣曲</span>', '<div id="lyrics-wrapper">', '</section>']]
        return content[start:min(end for end in ends if end != -1)]

    def test_imitate_songs_are_grouped_by_joke_and_category(self):
        """#423: 模倣元のうち、ネタ曲と曲以外のカテゴリの曲は、それぞれdetailsにまとめること"""
        song = Song.objects.create(title="模倣元の曲")
        joke = Song.objects.create(title="模倣元のネタ曲", is_joke=True)
        cover = Song.objects.create(title="模倣元のカバー", category="cover")
        arrange = Song.objects.create(title="模倣元のアレンジ", category="arrange", is_joke=True)
        self.song.imitates.add(song, joke, cover, arrange)
        details = self._get_imitate_details_html("模倣元")
        self.assertIn("4曲", details)
        nested = re.findall(r'<details[^>]*>\s*<summary><i class="([^"]+)"></i><span class="icon-p">([^<]+)</span></summary>(.*?)</details>', details, re.DOTALL)
        self.assertEqual(
            [(icon, label, re.findall(r'>([^<]+)</a>', links)) for icon, label, links in nested],
            [
                ("far fa-meh-rolling-eyes", "ネタ曲", ["模倣元のネタ曲"]),
                # 曲以外のカテゴリの曲は、ネタ曲でもカテゴリの方にまとめ、SONG_CATEGORIESの順に並べる
                ("fas fa-sliders-h", "アレンジ", ["模倣元のアレンジ"]),
                ("fas fa-microphone", "カバー", ["模倣元のカバー"]),
            ],
        )
        # カテゴリが曲でネタ曲でない曲は、detailsにまとめずに並べる
        self.assertEqual(re.findall(r'>([^<]+)</a>', details.split("<details")[0]), ["模倣元の曲"])

    def test_imitated_songs_are_grouped_by_category(self):
        """#423: 模倣曲も、曲以外のカテゴリの曲はdetailsにまとめること"""
        medley = Song.objects.create(title="模倣曲のメドレー", category="medley")
        medley.imitates.add(self.song)
        details = self._get_imitate_details_html("模倣曲")
        self.assertIn('<summary><i class="fas fa-stream"></i><span class="icon-p">メドレー</span></summary>', details)
        self.assertNotIn("ネタ曲", details)

    def create_short_and_full_songs(self):
        author = Author.objects.create(name="short作者")
        self.song.authors.set([author])
        short1 = Song.objects.create(title="詳細テスト曲[short]")
        short2 = Song.objects.create(title="詳細テスト曲 (Short Ver.)")
        short1.authors.set([author])
        short2.authors.set([author])
        return short1, short2

    def test_full_song_shows_all_short_songs_in_song_info(self):
        """#667: full版の曲には、short版の曲へのリンクが全てsong-infoに表示されること"""
        short1, short2 = self.create_short_and_full_songs()
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertEqual(response.context["short_songs"], [short1, short2])
        self.assertEqual(response.context["full_songs"], [])
        content = response.content.decode()
        start = content.index('<table id="song-info">')
        song_info = content[start:content.index("</table>", start)]
        self.assertIn("short版", song_info)
        self.assertNotIn("full版", song_info)
        self.assertIn(f'<a href="{reverse("subekashi:song", args=[short1.id])}">詳細テスト曲[short]</a>', song_info)
        self.assertIn(f'<a href="{reverse("subekashi:song", args=[short2.id])}">詳細テスト曲 (Short Ver.)</a>', song_info)

    def test_short_song_shows_full_song_in_song_info(self):
        """#667: short版の曲には、full版の曲へのリンクがsong-infoに表示されること"""
        short1, _ = self.create_short_and_full_songs()
        response = self.client.get(reverse("subekashi:song", args=[short1.id]))
        self.assertEqual(response.context["full_songs"], [self.song])
        self.assertEqual(response.context["short_songs"], [])
        content = response.content.decode()
        start = content.index('<table id="song-info">')
        song_info = content[start:content.index("</table>", start)]
        self.assertIn("full版", song_info)
        self.assertIn(f'<a href="{reverse("subekashi:song", args=[self.song.id])}">詳細テスト曲</a>', song_info)

    def test_song_by_aliased_author_is_shown_in_song_info(self):
        """#667: 別名でつながっている名義のfull版・short版も双方向に表示されること"""
        author = Author.objects.create(name="short作者")
        sub_author = Author.objects.create(name="short作者の別名義")
        AuthorAlias.objects.create(author=author, name="short作者の別名義", alias_type="another")
        self.song.authors.set([author])
        short = Song.objects.create(title="詳細テスト曲[short]")
        short.authors.set([sub_author])
        self.assertEqual(self.client.get(reverse("subekashi:song", args=[short.id])).context["full_songs"], [self.song])
        self.assertEqual(self.client.get(reverse("subekashi:song", args=[self.song.id])).context["short_songs"], [short])

    def test_short_and_full_rows_not_shown_without_related_songs(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertNotContains(response, "full版")
        self.assertNotContains(response, "short版")

    def test_related_song_title_is_escaped(self):
        """#667: full版・short版の曲のタイトルはエスケープして表示すること"""
        author = Author.objects.create(name="short作者")
        full = Song.objects.create(title="<b>曲</b>")
        short = Song.objects.create(title="<b>曲</b>[short]")
        full.authors.set([author])
        short.authors.set([author])
        response = self.client.get(reverse("subekashi:song", args=[short.id]))
        self.assertContains(response, "&lt;b&gt;曲&lt;/b&gt;</a>")
        self.assertNotContains(response, "<b>曲</b></a>")


@override_settings(STORAGES=STATIC_STORAGE)
class SongNewViewTest(TestCase):
    """SongNewView (/songs/new/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_new"))
        self.assertEqual(response.status_code, 200)

    def test_get_shows_category_select_in_both_forms(self):
        """#423: 2つのフォームそれぞれに、全てのカテゴリを選べる選択欄を表示すること"""
        response = self.client.get(reverse("subekashi:song_new"))
        for suffix in ["auto", "manual"]:
            self.assertContains(response, f'<select id="category-{suffix}" name="category" data-sync="category">')
        for value, label in Song.CHOICES:
            self.assertContains(response, f'<option value="{value}">{label}</option>', count=2)

    def test_get_has_hidden_allow_dup_url_input_in_auto_form(self):
        """#1285: 重複を許可して登録するURLを送るための入力欄を、URLで登録するフォームに置くこと"""
        response = self.client.get(reverse("subekashi:song_new"))
        self.assertContains(response, '<input type="hidden" id="allow-dup-url" name="allow_dup_url">', count=1)

    @patch("subekashi.views.song_new.send_discord", return_value=True)
    def test_get_allow_dup_url_does_not_allow_dup(self, mock_send_discord):
        """#1285: GETで開いただけでは、重複を許可せず、履歴もDiscordへの通知も作らないこと"""
        song = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(song)
        response = self.client.get(reverse("subekashi:song_new"), {"allow_dup_url": "https://youtu.be/dupallow123"})
        self.assertEqual(response.status_code, 200)
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)
        self.assertFalse(History.objects.exists())
        mock_send_discord.assert_not_called()

    @patch("subekashi.views.song_new.get_youtube_api")
    @patch("subekashi.views.song_new.send_discord", return_value=True)
    def test_post_with_allow_dup_url_allows_dup_and_records_history_for_song_with_url(self, mock_send_discord, mock_api):
        """#1282, #1285: 重複を許可して登録したとき、URLを元から持つ曲の編集履歴に、重複を許可したことを残すこと"""
        mock_api.return_value = {"title": "新しい曲", "author": "新しい作者", "upload_time": None, "view": 1, "like": 1}
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(owner)
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://youtu.be/dupallow123", "allow_dup_url": "https://youtu.be/dupallow123"},
        )
        self.assertEqual(response.status_code, 302)
        link.refresh_from_db()
        self.assertTrue(link.allow_dup)
        new_song = Song.objects.get(title="新しい曲")
        self.assertCountEqual(link.songs.all(), [owner, new_song])
        history = History.objects.get(song=owner)
        self.assertEqual(history.history_type, "edit")
        self.assertEqual(history.title, "重複許可の元の曲のURLの重複を許可")
        self.assertEqual(history.changes, [["種類", "内容"], ["重複許可したURL", "https://youtu.be/dupallow123"]])
        self.assertEqual(history.editor.ip, encrypt("127.0.0.1"))
        self.assertEqual(list(History.objects.filter(song=new_song).values_list("history_type", flat=True)), ["new"])
        texts = [call.args[1] for call in mock_send_discord.call_args_list]
        self.assertEqual(len([t for t in texts if t.startswith("重複許可したURL")]), 1)
        self.assertEqual(len([t for t in texts if t.startswith("新規作成されました")]), 1)

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_with_allow_dup_url_accepts_notation_variation_of_same_url(self, mock_api):
        """#1285: 重複を許可するURLは、登録するURLと同じ動画なら表記が違っていても許可すること"""
        mock_api.return_value = {"title": "新しい曲", "author": "新しい作者", "upload_time": None, "view": 1, "like": 1}
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(Song.objects.create(title="重複許可の元の曲"))
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://www.youtube.com/watch?v=dupallow123", "allow_dup_url": "https://youtu.be/dupallow123"},
        )
        self.assertEqual(response.status_code, 302)
        link.refresh_from_db()
        self.assertTrue(link.allow_dup)

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_with_allow_dup_url_of_allowed_url_records_no_history(self, mock_api):
        mock_api.return_value = {"title": "新しい曲", "author": "新しい作者", "upload_time": None, "view": 1, "like": 1}
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123", allow_dup=True)
        link.songs.add(owner)
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://youtu.be/dupallow123", "allow_dup_url": "https://youtu.be/dupallow123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(History.objects.filter(song=owner).exists())

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_without_allow_dup_url_returns_error_and_keeps_dup_disallowed(self, mock_api):
        """#1285: 重複を許可すると送らなければ、重複するURLは登録できず、重複も許可しないこと"""
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(owner)
        response = self.client.post(reverse("subekashi:song_new"), {"url": "https://youtu.be/dupallow123"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("既に登録されています", response.context["error"])
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)
        self.assertFalse(History.objects.exists())
        mock_api.assert_not_called()

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_with_allow_dup_url_of_other_url_returns_error(self, mock_api):
        """#1285: 重複を許可するURLが、登録するURLと違うときは、登録するURLの重複を許可しないこと"""
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(owner)
        other_link = SongLink.objects.create(url="https://youtu.be/dupother456")
        other_link.songs.add(Song.objects.create(title="別の曲"))
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://youtu.be/dupallow123", "allow_dup_url": "https://youtu.be/dupother456"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("既に登録されています", response.context["error"])
        self.assertFalse(SongLink.objects.filter(allow_dup=True).exists())
        self.assertFalse(History.objects.exists())

    def test_post_with_allow_dup_url_without_url_does_not_allow_dup(self):
        """#1285: URLなしで登録するときは、重複を許可するURLを送られても重複を許可しないこと"""
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(Song.objects.create(title="重複許可の元の曲"))
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "テスト作者", "title": "テスト曲", "allow_dup_url": "https://youtu.be/dupallow123"},
        )
        self.assertEqual(response.status_code, 302)
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)
        self.assertFalse(History.objects.filter(song__title="重複許可の元の曲").exists())

    @patch("subekashi.views.song_new.get_youtube_api", return_value={})
    @patch("subekashi.views.song_new.send_discord", return_value=True)
    def test_post_with_allow_dup_url_does_not_allow_dup_if_save_fails(self, mock_send_discord, mock_api):
        """#1285: 曲を保存できなかったときは、重複を許可せず、履歴もDiscordへの通知も作らないこと"""
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(owner)
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://youtu.be/dupallow123", "allow_dup_url": "https://youtu.be/dupallow123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("YouTube上で削除されたか非公開になっている", response.context["error"])
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)
        self.assertFalse(History.objects.exists())
        mock_send_discord.assert_not_called()

    def test_post_with_category_saves_category(self):
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "カテゴリテスト作者", "title": "カテゴリテスト曲", "category": "otomad"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Song.objects.get(title="カテゴリテスト曲").category, "otomad")

    def test_post_does_not_set_prush(self):
        """#1064: 新規登録画面からはプレラを登録できないこと"""
        Prush.objects.create(name="年末プレラ５")
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "プレラテスト作者", "title": "プレラテスト曲", "prush": "年末プレラ５"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(Song.objects.get(title="プレラテスト曲").prush)

    def test_post_without_category_defaults_to_song(self):
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "カテゴリテスト作者", "title": "カテゴリ未指定テスト曲"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Song.objects.get(title="カテゴリ未指定テスト曲").category, "song")

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_invalid_category_returns_error(self, mock_api):
        """#423: 選択肢にないカテゴリはエラーにし、YouTube Data APIを呼び出さないこと"""
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://youtu.be/aaaaaaaaaaa", "category": "joke"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "カテゴリが不正です。")
        mock_api.assert_not_called()
        self.assertFalse(Song.objects.exists())

    def test_post_non_youtube_url_returns_error(self):
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://example.com/video", "authors": "テスト作者", "title": "テスト曲"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("YouTube", response.context["error"])

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_youtube_url_with_api_error_returns_error(self, mock_api):
        # #1146: get_youtube_apiは呼び出しに失敗すると例外を送出するようになったため、500エラーにならないことを確認する
        # #886: 動画が削除・非公開であるとは限らないため、削除・非公開とは伝えず、インターネットに接続できなかった可能性を伝える
        mock_api.side_effect = YoutubeApiError("YouTube Data APIの呼び出しに失敗しました")
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://youtu.be/aaaaaaaaaaa", "authors": "", "title": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("インターネットに接続できなかった", response.context["error"])
        self.assertIn("YouTubeから動画の情報を取得できませんでした", response.context["error"])
        self.assertNotIn("削除", response.context["error"])
        self.assertContains(response, f'showToast("error", "{response.context["error"]}")')
        self.assertFalse(Song.objects.exists())

    @patch("subekashi.lib.youtube.YOUTUBE_API_KEY", "dummy-key")
    @patch("subekashi.lib.youtube.build")
    def test_post_youtube_url_without_internet_connection_returns_error(self, mock_build):
        # #886: インターネットに接続できなかった場合は、動画が削除・非公開であるとは伝えない
        mock_build.return_value.videos.return_value.list.return_value.execute.side_effect = socket.timeout("timed out")
        response = self.client.post(reverse("subekashi:song_new"), {"url": "https://youtu.be/aaaaaaaaaaa"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("インターネットに接続できなかった", response.context["error"])
        self.assertNotIn("削除", response.context["error"])
        self.assertFalse(Song.objects.exists())

    @patch("subekashi.views.song_new.get_youtube_api", return_value={})
    def test_post_deleted_youtube_url_returns_error(self, mock_api):
        # #886: 動画が削除・非公開の場合は「作者は空白にできません。」ではなく、その趣旨のトーストを表示する
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://youtu.be/aaaaaaaaaaa", "is-deleted-auto": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("YouTube上で削除されたか非公開になっている", response.context["error"])
        self.assertIn("「タイトルと作者から登録」で「非公開/削除済み」にチェックを入れて", response.context["error"])
        self.assertNotIn("作者は空白にできません", response.context["error"])
        self.assertContains(response, f'showToast("error", "{response.context["error"]}")')
        self.assertFalse(Song.objects.exists())

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_duplicate_youtube_url_does_not_call_api(self, mock_api):
        # 既に登録されているURLの場合は、YouTube Data APIのクォータを消費しないよう呼び出さずにエラーにする
        link = SongLink.objects.create(url="https://youtu.be/aaaaaaaaaaa")
        link.songs.add(Song.objects.create(title="既存曲"))
        response = self.client.post(reverse("subekashi:song_new"), {"url": "https://youtu.be/aaaaaaaaaaa"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("既に登録されています", response.context["error"])
        mock_api.assert_not_called()

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_youtube_url_registers_song_with_api_result(self, mock_api):
        mock_api.return_value = {
            "title": "YT動画タイトル",
            "author": "YTチャンネル名",
            "upload_time": None,
            "view": 100,
            "like": 10,
        }
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://youtu.be/aaaaaaaaaaa", "authors": "", "title": ""},
        )
        self.assertEqual(response.status_code, 302)
        song = Song.objects.get(title="YT動画タイトル")
        self.assertEqual(list(song.authors.values_list("name", flat=True)), ["YTチャンネル名"])
        self.assertEqual(list(song.links.values_list("url", flat=True)), ["https://youtu.be/aaaaaaaaaaa"])

    @patch("subekashi.views.song_new.get_youtube_api")
    def test_post_youtube_live_url_registers_short_url(self, mock_api):
        # ライブのURL（youtube.com/live/<id>）も動画のURLとして受け付け、短縮URLで保存する（#52）
        mock_api.return_value = {"title": "ライブ", "author": "YTチャンネル名", "upload_time": None, "view": 100, "like": 10}
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://www.youtube.com/live/aaaaaaaaaaa?si=xxxx", "authors": "", "title": ""},
        )
        self.assertEqual(response.status_code, 302)
        mock_api.assert_called_once_with("aaaaaaaaaaa")
        song = Song.objects.get(title="ライブ")
        self.assertEqual(list(song.links.values_list("url", flat=True)), ["https://youtu.be/aaaaaaaaaaa"])

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

    def test_post_author_name_error_escapes_html_in_response(self):
        # song_new.html側は{{ error }}で（|safeを使わず）Djangoの標準オートエスケープに
        # 任せる設計のため、song_edit.py側のような明示的なescape()呼び出しは不要だが、
        # 将来テンプレートが|safeに変更された場合に気付けるよう回帰防止テストを置いておく
        max_length = Author._meta.get_field("name").max_length
        malicious_name = "<script>alert(1)</script>" * (max_length // 20 + 1)
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": malicious_name, "title": "XSSテスト曲"},
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertFalse(Song.objects.filter(title="XSSテスト曲").exists())

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
        # 入力した作者名がpast別名と一致する場合、統一した名義に正規化されて
        # 保存される。redirect先のURLにその旨を伝えるtoast用のフラグが付与される
        unified_author = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=unified_author, alias_type="past")

        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "以前の名義", "title": "正規化テスト曲"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("name_unified=1", response.url)
        song = Song.objects.get(title="正規化テスト曲")
        self.assertIn(unified_author, song.authors.all())

    def test_post_without_normalization_does_not_flag_toast(self):
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "正規化されない作者", "title": "通常テスト曲"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("name_unified", response.url)


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_removed_song_shows_removed_page(self):
        # ユーザーが削除した曲（#1239）は編集できず、削除を取り消すボタンのあるページを表示する（#1264）
        self.song.is_removed = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song_edit", args=[self.song.id]))
        assert_song_removed_page(self, response)

    def test_get_selects_current_category(self):
        """#423: カテゴリの選択欄は、曲のカテゴリを選択した状態で表示すること"""
        Song.objects.filter(pk=self.song.pk).update(category="medley")
        content = self.client.get(reverse("subekashi:song_edit", args=[self.song.id])).content.decode()
        self.assertIn('<select id="category" name="category">', content)
        self.assertEqual(re.findall(r'<option value="(\w+)" selected>', content), ["medley"])

    def test_get_lyrics_is_hidden_if_not_song(self):
        """#423: 歌詞の入力欄は、カテゴリが曲以外のときにJS（song_edit.js）で非表示にする対象であること"""
        content = self.client.get(reverse("subekashi:song_edit", args=[self.song.id])).content.decode()
        self.assertRegex(content, r'<div class="form-col" data-hide-if-questionable data-hide-if-not-song>\s*<label for="lyrics">')

    def test_get_imitate_label_is_imitate_source(self):
        """#1241: 模倣の入力欄は編集する曲の模倣元を登録するため、「模倣元」と模倣元のアイコンで表示し、原曲以外の曲を検索する欄を「模倣曲」と表記しないこと"""
        response = self.client.get(reverse("subekashi:song_edit", args=[self.song.id]))
        self.assertContains(response, '<label id="imitate-label" data-hide-if-questionable><i class="fas fa-sitemap imitate"></i><span class="icon-p-big">模倣元</span>', count=1)
        self.assertContains(response, '<p id="imitate-sub">もしくは原曲以外から選択</p>', count=1)

    def test_get_has_hidden_allow_dup_url_input(self):
        """#1285: 重複を許可して登録するURLを送るための入力欄を置くこと"""
        response = self.client.get(reverse("subekashi:song_edit", args=[self.song.id]))
        self.assertContains(response, '<input type="hidden" id="allow-dup-url" name="allow_dup_url">', count=1)

    @patch("subekashi.views.song_edit.send_discord", return_value=True)
    def test_get_allow_dup_url_does_not_allow_dup(self, mock_send_discord):
        """#1285: GETで開いただけでは、重複を許可せず、履歴もDiscordへの通知も作らないこと"""
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(owner)
        response = self.client.get(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"allow_dup_url": "https://youtu.be/dupallow123"},
        )
        self.assertEqual(response.status_code, 200)
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)
        self.assertFalse(History.objects.exists())
        mock_send_discord.assert_not_called()

    @patch("subekashi.views.song_edit.send_discord", return_value=True)
    def test_post_with_allow_dup_url_records_history_for_song_with_url_only(self, mock_send_discord):
        """#1282, #1285: 重複を許可したことは、URLを元から持つ曲の編集履歴に残り、編集している曲には残らないこと"""
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(owner)
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "https://youtu.be/dupallow123",
                "allow_dup_url": "https://youtu.be/dupallow123",
            },
        )
        self.assertEqual(response.status_code, 302)
        link.refresh_from_db()
        self.assertTrue(link.allow_dup)
        self.assertCountEqual(link.songs.all(), [owner, self.song])
        history = History.objects.get(song=owner)
        self.assertEqual(history.history_type, "edit")
        self.assertEqual(history.title, "重複許可の元の曲のURLの重複を許可")
        self.assertEqual(history.changes, [["種類", "内容"], ["重複許可したURL", "https://youtu.be/dupallow123"]])
        self.assertFalse(History.objects.filter(song=self.song, title__contains="重複を許可").exists())
        texts = [call.args[1] for call in mock_send_discord.call_args_list]
        self.assertEqual(len([t for t in texts if t.startswith("重複許可したURL")]), 1)

    @patch("subekashi.views.song_edit.send_discord", return_value=True)
    def test_post_with_allow_dup_url_allows_only_listed_urls(self, mock_send_discord):
        """#1285: 複数のURLを登録するとき、重複を許可するURLだけを許可すること"""
        link_a = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link_a.songs.add(Song.objects.create(title="重複許可の元の曲A"))
        link_b = SongLink.objects.create(url="https://youtu.be/dupallow456")
        link_b.songs.add(Song.objects.create(title="重複許可の元の曲B"))
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "https://youtu.be/dupallow123,https://youtu.be/dupallow456",
                "allow_dup_url": "https://youtu.be/dupallow123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("既に登録されています", response.context["error"])
        link_a.refresh_from_db()
        link_b.refresh_from_db()
        self.assertFalse(link_a.allow_dup)
        self.assertFalse(link_b.allow_dup)
        self.assertFalse(self.song.links.exists())

        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "https://youtu.be/dupallow123,https://youtu.be/dupallow456",
                "allow_dup_url": "https://youtu.be/dupallow123,https://youtu.be/dupallow456",
            },
        )
        self.assertEqual(response.status_code, 302)
        link_a.refresh_from_db()
        link_b.refresh_from_db()
        self.assertTrue(link_a.allow_dup)
        self.assertTrue(link_b.allow_dup)
        self.assertEqual(self.song.links.count(), 2)

    def test_post_without_allow_dup_url_returns_error_and_keeps_dup_disallowed(self):
        """#1285: 重複を許可すると送らなければ、重複するURLは登録できず、重複も許可しないこと"""
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(owner)
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "編集テスト作者", "url": "https://youtu.be/dupallow123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("既に登録されています", response.context["error"])
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)
        self.assertFalse(History.objects.exists())

    def test_post_with_allow_dup_url_of_other_url_returns_error(self):
        """#1285: 重複を許可するURLが、登録するURLと違うときは、登録するURLの重複を許可しないこと"""
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(Song.objects.create(title="重複許可の元の曲"))
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "https://youtu.be/dupallow123",
                "allow_dup_url": "https://youtu.be/dupother456",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("既に登録されています", response.context["error"])
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)

    @patch("subekashi.views.song_edit.send_discord", return_value=True)
    def test_post_with_allow_dup_url_of_own_url_does_not_allow_dup(self, mock_send_discord):
        """#1285: 編集している曲にしか紐付いていないURLは重複していないため、allow_dup_urlを送られても許可せず、履歴も作らないこと"""
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(self.song)
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "https://youtu.be/dupallow123",
                "allow_dup_url": "https://youtu.be/dupallow123",
            },
        )
        self.assertEqual(response.status_code, 302)
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)
        self.assertFalse(History.objects.filter(title__contains="重複を許可").exists())
        texts = [call.args[1] for call in mock_send_discord.call_args_list]
        self.assertFalse([t for t in texts if t.startswith("重複許可したURL")])

    def test_post_with_allow_dup_url_of_own_url_shared_with_other_song_records_no_history_for_own_song(self):
        """#1285: 編集している曲と別の曲に紐付いているURLの重複を許可しても、編集している曲には履歴を作らないこと"""
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(self.song, owner)
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "https://youtu.be/dupallow123",
                "allow_dup_url": "https://youtu.be/dupallow123",
            },
        )
        self.assertEqual(response.status_code, 302)
        link.refresh_from_db()
        self.assertTrue(link.allow_dup)
        self.assertFalse(History.objects.filter(song=self.song, title__contains="重複を許可").exists())
        self.assertEqual(History.objects.filter(song=owner, title__contains="重複を許可").count(), 1)

    def test_post_with_allow_dup_url_still_checks_url_length(self):
        """#1285: 重複を許可するURLでも、URLの長さは検証すること"""
        url = "https://x.com/" + "a" * 300
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "編集テスト作者", "url": url, "allow_dup_url": url},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("文字以下である必要があります", response.context["error"])
        self.assertFalse(self.song.links.exists())

    @patch("subekashi.views.song_edit.send_discord", return_value=True)
    def test_post_with_allow_dup_url_does_not_allow_dup_if_save_fails(self, mock_send_discord):
        """#1285: 曲を保存できなかったときは、重複を許可せず、履歴もDiscordへの通知も作らないこと"""
        owner = Song.objects.create(title="重複許可の元の曲")
        link = SongLink.objects.create(url="https://youtu.be/dupallow123")
        link.songs.add(owner)
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "あ" * 300,
                "url": "https://youtu.be/dupallow123",
                "allow_dup_url": "https://youtu.be/dupallow123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("作者名は", response.context["error"])
        link.refresh_from_db()
        self.assertFalse(link.allow_dup)
        self.assertFalse(History.objects.exists())
        mock_send_discord.assert_not_called()

    def test_post_category_is_saved_and_recorded_in_history(self):
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "編集テスト作者", "url": "", "category": "omnibus"},
        )
        self.assertEqual(response.status_code, 302)
        self.song.refresh_from_db()
        self.assertEqual(self.song.category, "omnibus")
        self.assertIn(["カテゴリ", "曲", "総集編"], History.objects.get(song=self.song).changes)

    def test_post_keeps_prush(self):
        """#1064: 編集画面からはプレラを変えられず、編集してもプレラは消えないこと"""
        prush = Prush.objects.create(name="年末プレラ５")
        Song.objects.filter(pk=self.song.pk).update(prush=prush)
        Prush.objects.create(name="晩夏プレラ6")
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集後の曲", "authors": "編集テスト作者", "url": "", "prush": "晩夏プレラ6"},
        )
        self.assertEqual(response.status_code, 302)
        self.song.refresh_from_db()
        self.assertEqual(self.song.title, "編集後の曲")
        self.assertEqual(self.song.prush, prush)

    def test_post_without_category_keeps_current_category(self):
        """#423: categoryを送らない場合（カテゴリの選択欄がない古いページからの送信等）は、編集前のカテゴリのままにすること"""
        Song.objects.filter(pk=self.song.pk).update(category="offv")
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "編集テスト作者", "url": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.song.refresh_from_db()
        self.assertEqual(self.song.category, "offv")

    def test_post_invalid_category_returns_error(self):
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "編集テスト作者", "url": "", "category": "joke"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "カテゴリが不正です。")
        self.song.refresh_from_db()
        self.assertEqual(self.song.category, "song")

    def test_post_non_song_category_keeps_lyrics(self):
        """#423: カテゴリが曲以外の場合、歌詞の入力欄は非表示にするだけで、送信された歌詞はそのまま保存すること"""
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "編集テスト作者", "url": "", "lyrics": "歌詞", "category": "medley"},
        )
        self.assertEqual(response.status_code, 302)
        self.song.refresh_from_db()
        self.assertEqual(self.song.category, "medley")
        self.assertEqual(self.song.lyrics, "歌詞")

    def test_get_response_is_not_cached(self):
        # #1135: ブラウザにキャッシュされた古いフォームが送信されると、その間の編集（模倣の追加等）が巻き戻ってしまう
        response = self.client.get(reverse("subekashi:song_edit", args=[self.song.id]))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("public", response["Cache-Control"])

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

    def test_post_untrusted_url_error_url_encodes_query_param(self):
        # コードレビュー指摘対応: お問い合わせリンクのdetail=クエリパラメータは
        # HTMLエスケープのみではURLに含まれる&や#でクエリ文字列が途中で切れてしまうため、
        # URLエンコードされていることを確認する
        url_with_special_chars = "https://example.com/video?a=1&b=2"
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "テスト作者", "url": url_with_special_chars},
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # &がエンコードされずそのまま出力されていると、クエリ文字列が途中で切れてしまう
        self.assertNotIn("detail=https://example.com/video?a=1&b=2", content)
        self.assertIn("a%3D1%26b%3D2", content)

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
        unified_author = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=unified_author, alias_type="past")

        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "以前の名義", "url": "", "imitate": "", "lyrics": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("name_unified=1", response.url)
        self.song.refresh_from_db()
        self.assertIn(unified_author, self.song.authors.all())

    def test_post_without_normalization_does_not_flag_toast(self):
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "正規化されない作者", "url": "", "imitate": "", "lyrics": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("name_unified", response.url)

    def test_post_bilibili_url_is_saved_in_formatted_form(self):
        """#1246: ビリビリ動画のURLは、av番号・www・末尾の/・クエリを揃えて保存すること"""
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "https://www.bilibili.com/video/av417727107/?spm_id_from=333.999.0.0,https://www.bilibili.com/video/BV1in4y1Q7qw?p=2&vd_source=e746505daf0168401b3bf90bae76310d",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertCountEqual(
            self.song.links.values_list("url", flat=True),
            ["https://bilibili.com/video/BV1qV411J7Kq", "https://bilibili.com/video/BV1in4y1Q7qw?p=2"],
        )

    def test_post_bilibili_av_url_of_registered_bv_url_returns_error(self):
        """#1246: av番号のURLとBV番号のURLは、同じ動画のURLとして重複を判定すること"""
        link = SongLink.objects.create(url="https://bilibili.com/video/BV1qV411J7Kq")
        link.songs.add(Song.objects.create(title="既存曲"))
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {"title": "編集テスト曲", "authors": "編集テスト作者", "url": "https://www.bilibili.com/video/av417727107/"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("既に登録されています", response.context["error"])
        self.assertFalse(self.song.links.exists())


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_removed_song_shows_removed_page(self):
        # ユーザーが削除した曲（#1239）の編集履歴のページは表示せず、削除を取り消すボタンのあるページを表示する。履歴は編集履歴の一覧で見られる
        self.song.is_removed = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song_history", args=[self.song.id]))
        assert_song_removed_page(self, response)

    def test_edit_history_has_diff_table(self):
        # 編集の変更履歴は、編集前と編集後の差分をeditor.jsで表示する（#608）
        editor = Editor.objects.create(ip="127.0.0.11")
        History.create_for_song(
            song=self.song, title="履歴テスト曲のタイトルを編集", history_type="edit",
            changes=[["種類", "編集前", "編集後"], ["タイトル", "旧タイトル", "履歴テスト曲"]], editor=editor,
        )
        History.create_for_song(
            song=self.song, title="履歴テスト曲を新規作成", history_type="new",
            changes=[["種類", "内容"], ["タイトル", "旧タイトル"]], editor=editor,
        )

        response = self.client.get(reverse("subekashi:song_history", args=[self.song.id]))

        self.assertContains(response, '<table class="diff-table">', count=1)
        self.assertContains(response, "subekashi/js/editor.js")

    def test_restore_history_shows_reason_table(self):
        # 削除の取り消し（#1264）の履歴は、削除の履歴と同じく理由の表を表示する（#1275）
        self.client.post(reverse("subekashi:song_delete", args=[self.song.id]), {"reason": "取り消す前の削除理由"})
        self.client.post(reverse("subekashi:song_restore", args=[self.song.id]), {"reason": "誤って削除したため取り消す"})

        response = self.client.get(reverse("subekashi:song_history", args=[self.song.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "履歴テスト曲の削除を取り消し")
        self.assertContains(response, '<div class="change-table-wrapper">', count=2)
        self.assertContains(response, '<table class="delete-table">', count=2)
        self.assertContains(response, "取り消す前の削除理由")
        self.assertContains(response, "誤って削除したため取り消す")

    def test_restore_history_without_reason_has_no_changes_table(self):
        # 理由を入力しなかった頃（#1264）の取り消しの履歴はchanges=Noneのため、変更内容の表を表示しない（#1275）
        History.create_for_song(
            song=self.song, title="履歴テスト曲の削除を取り消し", history_type="restore", changes=None,
            editor=Editor.objects.create(ip="127.0.0.31"),
        )

        response = self.client.get(reverse("subekashi:song_history", args=[self.song.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "履歴テスト曲の削除を取り消し")
        self.assertNotContains(response, '<div class="change-table-wrapper">')


@override_settings(STORAGES=STATIC_STORAGE)
class SongDeleteViewTest(TestCase):
    """SongDeleteView (/songs/<id>/delete/) のテスト

    削除申請ではなく、送信するとすぐに曲を論理削除する（#1239）
    """

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="削除テスト曲")

    def _post(self, reason="削除理由テスト"):
        return self.client.post(reverse("subekashi:song_delete", args=[self.song.id]), {"reason": reason})

    def test_existing_song_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_delete", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song_delete", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_post_valid_reason_redirects_to_top(self):
        # 削除した曲のページは表示できないため、トップに遷移する。SEND_DISCORD=False のため send_discord は即 True を返す
        response = self._post()
        self.assertRedirects(response, "/?toast=delete", fetch_redirect_response=False)

    def test_post_valid_reason_removes_song(self):
        self._post()
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        assert_song_removed_page(self, response)

    def test_post_valid_reason_saves_history(self):
        self._post()
        history = History.objects.get(song_id=self.song.id)
        self.assertEqual(history.history_type, "delete")
        self.assertEqual(history.title, "削除テスト曲を削除")
        self.assertEqual(history.changes, ["理由", "削除理由テスト"])

    @patch("subekashi.views.song_delete.NEW_DISCORD_URL", "https://discord.example/new")
    @patch("subekashi.views.song_delete.send_discord", return_value=True)
    def test_post_sends_discord_notification(self, mock_send_discord):
        # 申請ではなく曲の変更になったため、新規登録・編集と同じ通知先に送る
        self._post()
        url, content = mock_send_discord.call_args[0]
        self.assertEqual(url, "https://discord.example/new")
        self.assertTrue(content.startswith("削除されました\n"))
        self.assertIn(f"/songs/{self.song.id}\n", content)
        self.assertIn("削除理由テスト", content)

    @patch("subekashi.views.song_delete.send_discord", return_value=False)
    def test_post_discord_failure_redirects_with_notify_error(self, _mock_send_discord):
        # 通知に失敗しても曲は削除されているため、500ページにはせず、削除できたことと通知に失敗したことを伝える
        response = self._post()
        self.assertRedirects(response, "/?toast=delete_notify_error", fetch_redirect_response=False)
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)
        self.assertTrue(History.objects.filter(song_id=self.song.id, history_type="delete").exists())

    def test_post_empty_reason_returns_error(self):
        response = self._post(reason="")
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)
        self.assertFalse(Song.all_objects.get(pk=self.song.pk).is_removed)

    def test_removed_song_shows_removed_page(self):
        self.song.is_removed = True
        self.song.save()
        assert_song_removed_page(self, self.client.get(reverse("subekashi:song_delete", args=[self.song.id])))
        assert_song_removed_page(self, self._post())
        self.assertFalse(History.objects.filter(song_id=self.song.id).exists())

    def test_locked_song_is_not_removed(self):
        self.song.is_lock = True
        self.song.save()
        response = self._post()
        self.assertRedirects(response, f"/songs/{self.song.id}?toast=lock", fetch_redirect_response=False)
        self.assertFalse(Song.all_objects.get(pk=self.song.pk).is_removed)

    def test_delete_form_explains_removal(self):
        response = self.client.get(reverse("subekashi:song_delete", args=[self.song.id]))
        self.assertContains(response, "削除した曲は、曲のページ・検索・作者のページ等に表示されなくなります。")
        # 削除の取り消しはお問い合わせではなく、曲のページのボタンで行う（#1264）
        self.assertContains(response, "誤って削除した場合は、曲のページの「削除を取り消す」から元に戻せます。")
        self.assertContains(response, '<input type="submit" value="削除" id="delete-submit" disabled>')
        self.assertNotContains(response, "削除申請")


@override_settings(STORAGES=STATIC_STORAGE)
class SongRemovedPageTest(TestCase):
    """ユーザーが削除した曲（#1239）のページ（song_removed.html）のテスト（#1264）

    曲名・直近の削除理由と、削除を取り消すボタンを表示する
    """

    def setUp(self):
        self.client = Client()
        self.editor = Editor.objects.create(ip="127.0.0.21")
        self.song = Song.objects.create(title="削除ページテスト曲", is_removed=True)

    def _get(self):
        return self.client.get(reverse("subekashi:song", args=[self.song.id]))

    def _create_history(self, history_type, changes, minutes_ago):
        history = History.create_for_song(
            song=self.song, title=f"削除ページテスト曲の{history_type}", history_type=history_type, changes=changes, editor=self.editor,
        )
        History.objects.filter(pk=history.pk).update(create_time=timezone.now() - timedelta(minutes=minutes_ago))

    def test_title_is_shown_with_escape(self):
        self.song.title = "<b>削除ページテスト曲</b>"
        self.song.save()
        response = self._get()
        self.assertContains(response, "<h1>&lt;b&gt;削除ページテスト曲&lt;/b&gt;のページは削除されました</h1>", status_code=410)

    def test_latest_delete_reason_is_shown(self):
        # 削除・取り消しを繰り返した曲は、直近の削除の理由を表示する
        self._create_history("delete", ["理由", "古い削除理由"], minutes_ago=30)
        self._create_history("restore", ["理由", "取り消した理由"], minutes_ago=20)
        self._create_history("delete", ["理由", "新しい削除理由"], minutes_ago=10)
        response = self._get()
        self.assertContains(response, '<p id="song-removed-reason">削除理由：新しい削除理由</p>', status_code=410)
        self.assertNotContains(response, "古い削除理由", status_code=410)
        self.assertNotContains(response, "取り消した理由", status_code=410)

    def test_reason_is_escaped_and_keeps_line_breaks(self):
        self._create_history("delete", ["理由", "<script>重複</script>\n2行目"], minutes_ago=10)
        response = self._get()
        self.assertContains(
            response, '<p id="song-removed-reason">削除理由：&lt;script&gt;重複&lt;/script&gt;<br>2行目</p>', status_code=410,
        )

    def test_reason_is_not_shown_without_delete_history(self):
        # 管理サイトで削除した曲は削除の履歴が無いため、理由を表示しない
        response = self._get()
        self.assertNotContains(response, "削除理由", status_code=410)

    def test_reason_is_not_shown_when_latest_history_is_not_delete(self):
        # 削除を取り消した後に管理サイトで削除した場合、取り消す前の削除の理由は表示しない
        self._create_history("delete", ["理由", "取り消した削除の理由"], minutes_ago=20)
        self._create_history("restore", ["理由", "削除を取り消した理由"], minutes_ago=10)
        response = self._get()
        self.assertNotContains(response, "取り消した削除の理由", status_code=410)
        self.assertNotContains(response, "削除を取り消した理由", status_code=410)
        self.assertNotContains(response, "削除理由", status_code=410)

    def test_unexpected_changes_of_delete_history_does_not_raise(self):
        # 削除の履歴のchangesが["理由", 理由]の形でなくても、500にせず理由を表示しない
        for changes in [None, [], ["理由"], "理由"]:
            with self.subTest(changes=changes):
                History.objects.all().delete()
                self._create_history("delete", changes, minutes_ago=10)
                response = self._get()
                assert_song_removed_page(self, response)
                self.assertNotContains(response, "削除理由", status_code=410)

    def test_restore_button_posts_with_csrf_token(self):
        response = self._get()
        self.assertContains(
            response, f'<form action="{reverse("subekashi:song_restore", args=[self.song.id])}" method="POST">', status_code=410,
        )
        self.assertContains(response, 'name="csrfmiddlewaretoken"', status_code=410)
        self.assertContains(
            response, '<i class="fas fa-trash-restore-alt"></i><span class="icon-p-big">削除を取り消す</span>', status_code=410,
        )

    def test_restore_form_has_required_reason(self):
        # 削除理由と同じく、削除を取り消す理由は必須で入力する（#1275）
        response = self._get()
        # 上の削除理由と区別できるよう、削除を取り消すフォームは見出しと説明を付けた区切り（#song-restore）にする
        self.assertContains(response, '<div id="song-restore">', status_code=410)
        self.assertContains(response, "<h1>削除を取り消す</h1>", status_code=410)
        self.assertContains(response, "<p>この曲を元に戻す場合は、取り消す理由を入力してください。</p>", status_code=410)
        self.assertContains(response, '<label for="restore-reason">取り消し理由</label>', status_code=410)
        self.assertContains(response, '<textarea id="restore-reason" name="reason" required></textarea>', status_code=410)
        # 理由が空の間は押せない。理由を入力すると、song_removed.jsがボタンを押せるようにする
        self.assertContains(response, 'class="action-button black-action-button" id="song-restore-submit" disabled>', status_code=410)
        self.assertContains(response, "subekashi/js/song_removed.js", status_code=410)
        self.assertNotContains(response, "showToast(", status_code=410)

    def test_page_does_not_link_to_contact_for_undo(self):
        # 削除の取り消しはお問い合わせで申請せず、ボタンで行う
        response = self._get()
        self.assertNotContains(response, "削除の取り消し", status_code=410)
        self.assertNotContains(response, "申請", status_code=410)

    def test_locked_song_has_no_restore_button(self):
        self.song.is_lock = True
        self.song.save()
        response = self._get()
        self.assertContains(response, "この曲はロックされているため、削除を取り消せません。", status_code=410)
        self.assertNotContains(response, reverse("subekashi:song_restore", args=[self.song.id]), status_code=410)
        self.assertNotContains(response, "restore-reason", status_code=410)
        self.assertNotContains(response, 'id="song-restore"', status_code=410)

    def test_song_with_conflict_url_has_no_restore_button(self):
        # 削除した曲のURLが他の曲に登録されていると、取り消すとURLが重複するため、ボタンの代わりに登録している曲を表示する
        link = SongLink.objects.create(url="https://youtu.be/removedpage1")
        other = Song.objects.create(title="<i>同じURLを登録した曲</i>")
        link.songs.add(self.song, other)
        response = self._get()
        self.assertContains(response, "この曲のURLが次の曲に登録されているため、削除を取り消せません。", status_code=410)
        self.assertContains(
            response, f'<li><a href="{reverse("subekashi:song", args=[other.id])}">&lt;i&gt;同じURLを登録した曲&lt;/i&gt;</a></li>', status_code=410,
        )
        self.assertNotContains(response, reverse("subekashi:song_restore", args=[self.song.id]), status_code=410)

    def test_page_is_not_cached_by_browser(self):
        # 削除を取り消した後に開き直したとき、ブラウザのキャッシュからこのページを表示しないようにする
        response = self._get()
        self.assertEqual(response["Cache-Control"], "no-cache")


@override_settings(STORAGES=STATIC_STORAGE)
class SongRestoreViewTest(TestCase):
    """SongRestoreView (/songs/<id>/restore/) のテスト（#1264）

    削除した曲のページの「削除を取り消す」ボタンから、曲の削除を取り消す
    """

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="取り消しテスト作者")
        self.song = Song.objects.create(title="取り消しテスト曲", is_removed=True)
        self.song.authors.add(self.author)

    def _post(self, data=None):
        # 取り消しの理由は必須（#1275）
        return self.client.post(
            reverse("subekashi:song_restore", args=[self.song.id]), {"reason": "取り消しテストの理由"} if data is None else data,
        )

    def test_post_restores_song_and_redirects_to_song_page(self):
        # SEND_DISCORD=False のため send_discord は即 True を返す
        response = self._post()
        self.assertRedirects(response, f"/songs/{self.song.id}?toast=restore", fetch_redirect_response=False)
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertFalse(Song.all_objects.get(pk=self.song.pk).is_removed)
        self.assertEqual(self.client.get(reverse("subekashi:song", args=[self.song.id])).status_code, 200)
        self.assertEqual(list(self.author.songs.all()), [self.song])

    def test_post_saves_history(self):
        self._post()
        history = History.objects.get(song_id=self.song.id)
        self.assertEqual(history.history_type, "restore")
        self.assertEqual(history.get_history_type_display(), "削除の取り消し")
        self.assertEqual(history.title, "取り消しテスト曲の削除を取り消し")
        self.assertEqual(history.changes, ["理由", "取り消しテストの理由"])
        self.assertEqual(history.editor.ip, encrypt("127.0.0.1"))

    @patch("subekashi.views.song_restore.NEW_DISCORD_URL", "https://discord.example/new")
    @patch("subekashi.views.song_restore.send_discord", return_value=True)
    def test_post_sends_discord_notification(self, mock_send_discord):
        # 削除と同じく、新規登録・編集と同じ通知先に送る
        self._post()
        url, content = mock_send_discord.call_args[0]
        self.assertEqual(url, "https://discord.example/new")
        self.assertTrue(content.startswith(f"削除が取り消されました\n{settings.ROOT_URL}/songs/{self.song.id}\n"))
        self.assertIn("理由：取り消しテストの理由\n", content)

    @patch("subekashi.views.song_restore.send_discord", return_value=True)
    def test_post_without_reason_is_not_restored(self, mock_send_discord):
        # 取り消しの理由が無い・空白だけの場合は取り消さず、削除した曲のページにエラーを表示する（#1275）
        for data in [{}, {"reason": ""}, {"reason": " \n　 "}]:
            with self.subTest(data=data):
                response = self._post(data)
                assert_song_removed_page(self, response)
                self.assertContains(response, 'showToast("error", "取り消し理由を入力してください。");', status_code=410)
                self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)
                self.assertFalse(History.objects.filter(song_id=self.song.id).exists())
                mock_send_discord.assert_not_called()

    @patch("subekashi.views.song_restore.send_discord", return_value=False)
    def test_post_discord_failure_redirects_with_notify_error(self, _mock_send_discord):
        # 通知に失敗しても削除は取り消されているため、500ページにはせず、取り消せたことと通知に失敗したことを伝える
        response = self._post()
        self.assertRedirects(response, f"/songs/{self.song.id}?toast=restore_notify_error", fetch_redirect_response=False)
        self.assertFalse(Song.all_objects.get(pk=self.song.pk).is_removed)
        self.assertTrue(History.objects.filter(song_id=self.song.id, history_type="restore").exists())

    def test_get_is_not_allowed(self):
        response = self.client.get(reverse("subekashi:song_restore", args=[self.song.id]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("subekashi:song_restore", args=[self.song.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)

    def test_nonexistent_song_returns_404(self):
        response = self.client.post(reverse("subekashi:song_restore", args=[99999]))
        self.assertEqual(response.status_code, 404)

    @patch("subekashi.views.song_restore.send_discord", return_value=True)
    def test_not_removed_song_redirects_to_song_page(self, mock_send_discord):
        # 既に削除を取り消した曲（別のタブで取り消した等）は、履歴を残さず曲のページに遷移する
        self.song.is_removed = False
        self.song.save()
        response = self._post()
        self.assertRedirects(response, f"/songs/{self.song.id}", fetch_redirect_response=False)
        self.assertFalse(History.objects.filter(song_id=self.song.id).exists())
        mock_send_discord.assert_not_called()

    def test_not_removed_song_without_reason_redirects_to_song_page(self):
        # 理由の確認より前に、削除を取り消した曲かどうかを確認する
        self.song.is_removed = False
        self.song.save()
        response = self._post({})
        self.assertRedirects(response, f"/songs/{self.song.id}", fetch_redirect_response=False)

    @patch("subekashi.views.song_restore.send_discord", return_value=True)
    def test_locked_song_is_not_restored(self, mock_send_discord):
        self.song.is_lock = True
        self.song.save()
        response = self._post()
        assert_song_removed_page(self, response)
        self.assertContains(response, "この曲はロックされているため、削除を取り消せません。", status_code=410)
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)
        self.assertFalse(History.objects.filter(song_id=self.song.id).exists())
        mock_send_discord.assert_not_called()

    def test_locked_song_without_reason_shows_lock_message(self):
        # ロックされた曲は理由を入力するフォームを表示しないため、理由のエラーではなくロックの説明を表示する
        self.song.is_lock = True
        self.song.save()
        response = self._post({})
        self.assertContains(response, "この曲はロックされているため、削除を取り消せません。", status_code=410)
        self.assertNotContains(response, "showToast(", status_code=410)

    @patch("subekashi.views.song_restore.send_discord", return_value=True)
    def test_song_with_conflict_url_is_not_restored(self, mock_send_discord):
        # 削除している間にURLが他の曲に登録されていた場合、取り消すとURLが重複するため取り消さない
        link = SongLink.objects.create(url="https://youtu.be/restoreview1")
        other = Song.objects.create(title="取り消しテストの同じURLの曲")
        link.songs.add(self.song, other)
        response = self._post()
        assert_song_removed_page(self, response)
        self.assertContains(response, "取り消しテストの同じURLの曲", status_code=410)
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)
        self.assertFalse(History.objects.filter(song_id=self.song.id).exists())
        mock_send_discord.assert_not_called()

    def test_delete_and_restore_round_trip(self):
        # 削除した曲を取り消すと曲のページが表示され、削除と取り消しの両方の履歴が残る
        self.song.is_removed = False
        self.song.save()
        self.client.post(reverse("subekashi:song_delete", args=[self.song.id]), {"reason": "誤って登録"})
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        assert_song_removed_page(self, response)
        self.assertContains(response, "削除理由：誤って登録", status_code=410)

        self._post()

        self.assertEqual(self.client.get(reverse("subekashi:song", args=[self.song.id])).status_code, 200)
        self.assertEqual(
            list(History.objects.filter(song_id=self.song.id).order_by("create_time", "id").values_list("history_type", "changes")),
            [("delete", ["理由", "誤って登録"]), ("restore", ["理由", "取り消しテストの理由"])],
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_song_row_is_locked_before_check_and_restore(self):
        # 削除されているか・取り消せるかの確認と取り消しは、曲の行をロックしてから行う
        with CaptureQueriesContext(connection) as queries:
            self._post()
        sqls = [query["sql"] for query in queries.captured_queries]
        table = connection.ops.quote_name("subekashi_song")
        lock_index = next((i for i, sql in enumerate(sqls) if f"FROM {table}" in sql and sql.endswith("FOR UPDATE")), None)
        update_index = next((i for i, sql in enumerate(sqls) if sql.startswith(f"UPDATE {table}")), None)
        self.assertIsNotNone(lock_index, "曲の行をロックしていない")
        self.assertIsNotNone(update_index)
        self.assertLess(lock_index, update_index)


@skipUnlessDBFeature("has_select_for_update")
@override_settings(STORAGES=STATIC_STORAGE)
class SongRestoreConcurrencyTest(TransactionTestCase):
    """「削除を取り消す」が同時に押された場合のテスト（#1264）

    別々のDB接続から同時に送るため、TransactionTestCaseで実際にコミットする。SQLiteはSELECT ... FOR UPDATEが無いため実行しない
    """

    def test_simultaneous_posts_restore_once(self):
        song = Song.objects.create(title="同時に取り消す曲", is_removed=True)
        url = reverse("subekashi:song_restore", args=[song.id])
        first_restoring = threading.Event()
        release = threading.Event()
        restored_ids = []

        # 1つ目の取り消しをコミットする前に止め、その間に2つ目を送る
        def restore_and_wait(target):
            restored_ids.append(target.id)
            if len(restored_ids) == 1:
                first_restoring.set()
                release.wait(10)
            restore_song(target)

        def post():
            try:
                Client().post(url, {"reason": "同時に取り消す理由"})
            finally:
                connection.close()

        with patch("subekashi.views.song_restore.restore_song", side_effect=restore_and_wait):
            first = threading.Thread(target=post)
            second = threading.Thread(target=post)
            first.start()
            try:
                self.assertTrue(first_restoring.wait(10))
                second.start()
                # 2つ目は1つ目がコミットするまで曲の行のロックを待つ
                second.join(1)
                self.assertTrue(second.is_alive())
            finally:
                release.set()
                first.join(10)
                if second.ident is not None:
                    second.join(10)

        self.assertEqual(restored_ids, [song.id])
        self.assertFalse(Song.all_objects.get(pk=song.pk).is_removed)
        self.assertEqual(History.objects.filter(song_id=song.id, history_type="restore").count(), 1)


@override_settings(STORAGES=STATIC_STORAGE)
class SongAdminTest(TestCase):
    """管理サイトの曲の一覧・変更画面のテスト（#1239）

    ユーザーが削除した曲も表示し、is_removedのチェックを外して復元できるようにする
    """

    def setUp(self):
        self.client = Client()
        self.client.force_login(User.objects.create_superuser("admin", password="password"))
        self.song = Song.objects.create(title="管理サイトの曲")
        self.removed = Song.objects.create(title="管理サイトの削除した曲", is_removed=True)

    def test_changelist_includes_removed_song(self):
        response = self.client.get(reverse("admin:subekashi_song_changelist"))
        self.assertContains(response, "管理サイトの曲")
        self.assertContains(response, "管理サイトの削除した曲")

    def test_changelist_can_filter_removed_songs(self):
        response = self.client.get(reverse("admin:subekashi_song_changelist"), {"is_removed__exact": "1"})
        self.assertContains(response, "管理サイトの削除した曲")
        self.assertNotContains(response, "管理サイトの曲")

    def test_change_page_of_removed_song_has_is_removed_checkbox(self):
        response = self.client.get(reverse("admin:subekashi_song_change", args=[self.removed.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="is_removed" id="id_is_removed" checked')


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_removed_song_history_shows_deleted_message(self):
        # ユーザーが削除した曲（#1239）のページは404になるため、リンクせずに削除されたと表示する
        song = Song.objects.create(title="編集者履歴の削除した曲", is_removed=True)
        History.create_for_song(
            song=song, title="編集者履歴の削除した曲を削除", history_type="delete", changes=["理由", "重複"], editor=self.editor,
        )

        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]))

        self.assertContains(response, "この曲または作者は削除されました")
        self.assertNotContains(response, f'href="{reverse("subekashi:song", args=[song.id])}"')

    def test_is_me_uses_x_real_ip(self):
        editor = Editor.objects.create(ip=encrypt("203.0.113.1"))
        response = self.client.get(
            reverse("subekashi:editor", args=[editor.id]),
            HTTP_X_REAL_IP="203.0.113.1", HTTP_X_FORWARDED_FOR="198.51.100.1",
        )
        self.assertTrue(response.context["is_me"])

    def test_x_forwarded_for_cannot_impersonate_editor(self):
        # X-Forwarded-Forで他人のIPを名乗っても、その人の編集者にならない（#1189）
        editor = Editor.objects.create(ip=encrypt("203.0.113.1"))
        response = self.client.get(
            reverse("subekashi:editor", args=[editor.id]),
            HTTP_X_REAL_IP="203.0.113.2", HTTP_X_FORWARDED_FOR="203.0.113.1",
        )
        self.assertFalse(response.context["is_me"])

    def _create_author_histories(self, editor, *titles):
        author = Author.objects.create(name=f"編集者検索テスト作者{Author.objects.count()}")
        for title in titles:
            History.create_for_author(
                author=author, title=title, history_type="edit", changes=None, editor=editor,
            )

    def test_search_filters_histories_by_title(self):
        # 編集履歴の概要（title）の部分一致で絞り込む（#954）
        self._create_author_histories(self.editor, "別名を追加", "リンクを編集")

        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]), {"q": "別名"})

        self.assertEqual([history.title for history in response.context["page_obj"]], ["別名を追加"])
        self.assertEqual(response.context["total_count"], 1)
        self.assertContains(response, 'id="history-count">1件</p>')
        self.assertContains(response, 'name="q" value="別名"')

    def test_search_excludes_other_editors_histories(self):
        other_editor = Editor.objects.create(ip="127.0.0.14")
        self._create_author_histories(other_editor, "別名を追加")

        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]), {"q": "別名"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 0)
        self.assertContains(response, 'id="history-count">0件</p>')

    def test_search_input_has_aria_label(self):
        # placeholderだけではスクリーンリーダーに伝わらないため、aria-labelでラベルを付ける
        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]))
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(soup.select_one('form input[name="q"]')["aria-label"], "編集履歴の概要で検索")

    def test_blank_query_shows_all_histories(self):
        self._create_author_histories(self.editor, "別名を追加", "リンクを編集")

        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]), {"q": "  "})

        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["search_query"], "")

    def test_search_query_is_escaped_in_form(self):
        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]), {"q": '"><script>alert(1)</script>'})

        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, 'value="&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"')

    def test_pagination_keeps_search_query(self):
        # 検索結果が複数ページのとき、前へ・次へのリンクで検索語を引き継ぐ
        author = Author.objects.create(name="編集者ページ送り作者")
        History.objects.bulk_create([
            History(author=author, title=f"別名&追加{i}", history_type="edit", editor=self.editor)
            for i in range(HISTORIES_PER_PAGE + 1)
        ])
        History.create_for_author(author=author, title="対象外", history_type="edit", changes=None, editor=self.editor)

        query = quote("別名&追加")
        first = self.client.get(reverse("subekashi:editor", args=[self.editor.id]), {"q": "別名&追加"})
        self.assertEqual(first.context["total_count"], HISTORIES_PER_PAGE + 1)
        self.assertContains(first, f'href="?page=2&amp;q={query}"', count=2)

        second = self.client.get(reverse("subekashi:editor", args=[self.editor.id]), {"q": "別名&追加", "page": 2})
        self.assertContains(second, f'href="?page=1&amp;q={query}"', count=2)

    def test_pagination_without_search_query_has_no_q(self):
        author = Author.objects.create(name="編集者ページ送り作者2")
        History.objects.bulk_create([
            History(author=author, title=f"履歴{i}", history_type="edit", editor=self.editor)
            for i in range(HISTORIES_PER_PAGE + 1)
        ])

        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]))

        self.assertContains(response, 'href="?page=2"', count=2)

    def test_private_editor_hides_search_form_and_histories(self):
        # 非公開の編集者は、検索しても履歴を見られない
        private_editor = Editor.objects.create(ip="127.0.0.15", is_open=False)
        self._create_author_histories(private_editor, "別名を追加")

        response = self.client.get(reverse("subekashi:editor", args=[private_editor.id]), {"q": "別名"})

        self.assertContains(response, "この編集者の情報は非公開です。")
        self.assertNotContains(response, 'name="q"')
        self.assertNotContains(response, "別名を追加")
        self.assertNotContains(response, "/report/")

    def test_report_button_links_to_report_page(self):
        # 荒らしの報告（#1291）。他人の編集者のページには、報告のフォームへのボタンがある
        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]), HTTP_X_REAL_IP="203.0.113.5")

        soup = BeautifulSoup(response.content, "html.parser")
        button = soup.select_one(".action-buttons a#editor-report")
        self.assertEqual(button["href"], reverse("subekashi:editor_report", args=[self.editor.id]))
        self.assertEqual(button.get_text(strip=True), "報告")

    def test_report_button_is_hidden_for_me(self):
        editor = Editor.objects.create(ip=encrypt("203.0.113.1"))

        response = self.client.get(reverse("subekashi:editor", args=[editor.id]), HTTP_X_REAL_IP="203.0.113.1")

        self.assertTrue(response.context["is_me"])
        self.assertNotContains(response, 'id="editor-report"')

    def test_report_toast_is_shown_only_after_reporting(self):
        url = reverse("subekashi:editor", args=[self.editor.id])

        self.assertContains(self.client.get(url, {"toast": "report"}), "報告しました。ご協力ありがとうございます。")
        self.assertNotContains(self.client.get(url), "報告しました。ご協力ありがとうございます。")


@override_settings(STORAGES=STATIC_STORAGE)
@patch("subekashi.views.editor_report.CONTACT_DISCORD_URL", "https://discord.example/contact")
class EditorReportViewTest(TestCase):
    """EditorReportView (/editor/<id>/report/) のテスト（#1291）"""

    def setUp(self):
        self.client = Client()
        self.editor = Editor.objects.create(ip="127.0.0.40")
        self.url = reverse("subekashi:editor_report", args=[self.editor.id])
        self.editor_url = reverse("subekashi:editor", args=[self.editor.id])
        self.reporter_ip = "203.0.113.5"

    def _post(self, reason="他の曲のタイトルを繰り返し書き換えています", **extra):
        return self.client.post(self.url, {"reason": reason}, HTTP_X_REAL_IP=self.reporter_ip, **extra)

    def test_get_returns_form(self):
        response = self.client.get(self.url, HTTP_X_REAL_IP=self.reporter_ip)

        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.select_one("form#editor-report-form")
        self.assertEqual(form["action"], self.url)
        self.assertEqual(form["method"].lower(), "post")
        self.assertTrue(form.select_one('textarea[name="reason"][required]'))
        self.assertTrue(form.select_one('input[name="csrfmiddlewaretoken"]'))
        self.assertEqual(soup.select_one(".action-buttons a")["href"], self.editor_url)

    def test_get_submit_is_disabled_until_reason_is_entered(self):
        # 報告理由が空の間は送信できない。入力に合わせて有効にするのはJSで行う
        response = self.client.get(self.url, HTTP_X_REAL_IP=self.reporter_ip)

        soup = BeautifulSoup(response.content, "html.parser")
        submit = soup.select_one("form#editor-report-form input#report-submit")
        self.assertEqual(submit["type"], "submit")
        self.assertTrue(submit.has_attr("disabled"))
        self.assertTrue(soup.select_one('script[src$="subekashi/js/editor_report.js"]'))

    def test_get_is_noindex(self):
        response = self.client.get(self.url, HTTP_X_REAL_IP=self.reporter_ip)
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')

    def test_nonexistent_editor_returns_404(self):
        with patch("subekashi.views.editor_report.send_discord") as mock_send_discord:
            get_response = self.client.get(reverse("subekashi:editor_report", args=[99999]))
            post_response = self.client.post(reverse("subekashi:editor_report", args=[99999]), {"reason": "理由"})

        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(post_response.status_code, 404)
        mock_send_discord.assert_not_called()

    @patch("subekashi.views.editor_report.send_discord", return_value=True)
    def test_cannot_report_myself(self, mock_send_discord):
        # 自分自身は報告できないため、編集者のページに戻す
        editor = Editor.objects.create(ip=encrypt(self.reporter_ip))
        url = reverse("subekashi:editor_report", args=[editor.id])

        get_response = self.client.get(url, HTTP_X_REAL_IP=self.reporter_ip)
        post_response = self.client.post(url, {"reason": "理由"}, HTTP_X_REAL_IP=self.reporter_ip)

        self.assertRedirects(get_response, reverse("subekashi:editor", args=[editor.id]), fetch_redirect_response=False)
        self.assertRedirects(post_response, reverse("subekashi:editor", args=[editor.id]), fetch_redirect_response=False)
        mock_send_discord.assert_not_called()

    @patch("subekashi.views.editor_report.send_discord", return_value=True)
    def test_post_redirects_to_editor_with_toast(self, mock_send_discord):
        response = self._post()
        self.assertRedirects(response, f"{self.editor_url}?toast=report", fetch_redirect_response=False)

    @patch("subekashi.views.editor_report.send_discord", return_value=True)
    def test_post_sends_reason_admin_url_and_encrypted_ip_to_contact_discord(self, mock_send_discord):
        self._post(reason="他の曲のタイトルを繰り返し書き換えています")

        mock_send_discord.assert_called_once()
        url, text = mock_send_discord.call_args.args
        self.assertEqual(url, "https://discord.example/contact")
        self.assertIn("他の曲のタイトルを繰り返し書き換えています", text)
        self.assertIn(f"{settings.ROOT_URL}{reverse('admin:subekashi_editor_change', args=[self.editor.id])}", text)
        self.assertIn(encrypt(self.reporter_ip), text)
        self.assertNotIn(self.reporter_ip, text)

    @patch("subekashi.views.editor_report.send_discord", return_value=True)
    def test_post_reporter_ip_uses_x_real_ip(self, mock_send_discord):
        # X-Forwarded-Forで報告した人のIPを偽れない（#1189）
        self._post(HTTP_X_FORWARDED_FOR="198.51.100.1")

        text = mock_send_discord.call_args.args[1]
        self.assertIn(encrypt(self.reporter_ip), text)
        self.assertNotIn(encrypt("198.51.100.1"), text)

    @patch("subekashi.views.editor_report.send_discord", return_value=True)
    def test_post_does_not_change_editor_or_histories(self, mock_send_discord):
        self._post()

        self.assertEqual(Editor.objects.count(), 1)
        self.assertEqual(History.objects.count(), 0)

    @patch("subekashi.views.editor_report.send_discord", return_value=True)
    def test_post_empty_reason_shows_error_and_does_not_send(self, mock_send_discord):
        for data in ({"reason": ""}, {"reason": "  "}, {}):
            with self.subTest(data=data):
                response = self.client.post(self.url, data, HTTP_X_REAL_IP=self.reporter_ip)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["error"], "報告理由を入力してください。")
                self.assertContains(response, 'showToast("error", "報告理由を入力してください。")')
        mock_send_discord.assert_not_called()

    @patch("subekashi.views.editor_report.send_discord", return_value=True)
    def test_post_too_long_reason_shows_error_and_keeps_reason(self, mock_send_discord):
        response = self._post(reason="あ" * 1001)

        self.assertEqual(response.context["error"], "報告理由は1000文字以内で入力してください。")
        self.assertContains(response, "あ" * 1001)
        mock_send_discord.assert_not_called()

    @patch("subekashi.views.editor_report.send_discord", return_value=False)
    def test_post_discord_failure_shows_error_and_keeps_reason(self, mock_send_discord):
        # 報告はDiscordにしか残らないため、送れなかったときは完了にせず、入力した理由を残したままフォームに戻す
        response = self._post(reason="送信に失敗する報告")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "報告を送信できませんでした。時間をおいて再度お試しください。")
        self.assertContains(response, 'showToast("error", "報告を送信できませんでした。時間をおいて再度お試しください。")')
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(soup.select_one("textarea[name=reason]").get_text(), "送信に失敗する報告")

    @patch("subekashi.views.editor_report.send_discord", return_value=False)
    def test_reason_is_escaped_in_form(self, mock_send_discord):
        response = self._post(reason='</textarea><script>alert(1)</script>')

        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;/textarea&gt;&lt;script&gt;alert(1)&lt;/script&gt;")


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_song_search_link_present(self):
        # 作者名を絞り込みに指定した曲の検索画面へのaction-buttonを表示する（#954）
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        soup = BeautifulSoup(response.content, "html.parser")
        button = soup.select_one(f'.action-buttons a.action-button[href="{reverse("subekashi:songs")}?author={quote(self.author.name)}"]')
        self.assertIsNotNone(button)
        self.assertIsNotNone(button.select_one("i.fa-search"))

    def test_song_search_link_encodes_author_name(self):
        author = Author.objects.create(name="A&B=C+D/E#F 作者")
        response = self.client.get(reverse("subekashi:author", args=[author.id]))
        self.assertContains(response, f'href="{reverse("subekashi:songs")}?author=A%26B%3DC%2BD/E%23F%20%E4%BD%9C%E8%80%85"')

    def test_stats_link_present(self):
        # 統計ページへのaction-buttonが別名ボタンの右に追加される（#334）
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, reverse("subekashi:author_stats", args=[self.author.id]))

    def test_stats_link_has_icon(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "fa-chart-line")

    def test_stats_summary_shows_kenreki(self):
        # view=1234は1,20,50,100,200,500,1000の7段階に到達 -> 7pt。
        # #1099: 2で割った鍵盤数(7//2=3)ではなく、pt合計(7)をそのまま表示する
        Song.objects.filter(title="作者ビューテスト曲").update(view=1234)
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, 'id="author-stats-summary"')
        self.assertEqual(response.context["kenreki"]["points"], 7)
        match = re.search(
            r'id="author-stats-summary"[^>]*><i class="fas fa-trophy"></i> (\d+)</p>',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), 7)

    def test_stats_summary_hidden_when_author_has_no_songs(self):
        no_song_author = Author.objects.create(name="曲の無い作者")
        response = self.client.get(reverse("subekashi:author", args=[no_song_author.id]))
        self.assertIsNone(response.context["kenreki"])
        self.assertNotContains(response, 'id="author-stats-summary"')

    def _create_sort_songs(self):
        # 登録日（id）・投稿日（upload_time）の順序が逆になる曲（setUpの曲は投稿日なし）
        for title, year in [("並び替え2024年", 2024), ("並び替え2020年", 2020)]:
            song = Song.objects.create(title=title, upload_time=datetime(year, 1, 1, tzinfo=dt_timezone.utc))
            song.authors.add(self.author)

    def _song_titles(self, response):
        return [song.title for song in response.context["songInsL"]]

    def test_default_sort_is_newest_registration(self):
        # URLクエリ・cookieが無い場合は、従来通り登録日の遅い順（#606）
        self._create_sort_songs()
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertEqual(response.context["sort"], "-id")
        self.assertEqual(self._song_titles(response), ["並び替え2020年", "並び替え2024年", "作者ビューテスト曲"])
        self.assertContains(response, '<option value="-id" selected>')

    def test_sort_query_orders_songs(self):
        # 投稿日の並び替えでは、投稿日が無い曲を除外せず末尾に表示する（#606）
        self._create_sort_songs()
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]), {"sort": "upload_time"})
        self.assertEqual(self._song_titles(response), ["並び替え2020年", "並び替え2024年", "作者ビューテスト曲"])
        self.assertContains(response, '<option value="upload_time" selected>')

    def test_sort_form_lists_same_choices_as_songs_page(self):
        self._create_sort_songs()
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, '<form method="get" id="author-sort" data-auto-submit>')
        options = re.findall(r'<option value="([^"]*)"', response.content.decode())
        self.assertEqual(options, [choice["value"] for choice in SORT_CHOICES])

    def test_sort_form_hidden_when_author_has_one_song(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertNotContains(response, 'id="author-sort"')

    def test_youtube_sort_note_shown_only_for_youtube_sorts(self):
        self._create_sort_songs()
        for sort in [choice["value"] for choice in SORT_CHOICES]:
            with self.subTest(sort=sort):
                response = self.client.get(reverse("subekashi:author", args=[self.author.id]), {"sort": sort})
                if sort in YOUTUBE_SORTS:
                    self.assertContains(response, 'id="author-sort-note"')
                else:
                    self.assertNotContains(response, 'id="author-sort-note"')

    def test_invalid_sort_query_uses_default_and_is_not_saved(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]), {"sort": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sort"], "-id")
        self.assertNotIn("author_sort", response.cookies)

    def test_sort_query_is_saved_to_cookie(self):
        # 曲の検索画面と同様に、選択した並び替えをcookieに保存する（#606）
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]), {"sort": "-view"})
        self.assertEqual(response.cookies["author_sort"].value, "-view")
        self.assertEqual(response.cookies["author_sort"]["max-age"], LONG_TERM_COOKIE_AGE)

    def test_sort_query_is_not_saved_when_saved_select_is_off(self):
        self.client.cookies["is_saved_select"] = "off"
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]), {"sort": "-view"})
        self.assertEqual(response.context["sort"], "-view")
        self.assertNotIn("author_sort", response.cookies)

    def test_saved_sort_cookie_is_used_without_query(self):
        self._create_sort_songs()
        self.client.cookies["author_sort"] = "-upload_time"
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertEqual(self._song_titles(response), ["並び替え2024年", "並び替え2020年", "作者ビューテスト曲"])

    def test_selected_sort_applies_to_other_authors(self):
        # ある作者ページで選んだ並び替えが、別の作者ページでも使われる
        other_author = Author.objects.create(name="並び替え別作者")
        self.client.get(reverse("subekashi:author", args=[self.author.id]), {"sort": "-like"})
        response = self.client.get(reverse("subekashi:author", args=[other_author.id]))
        self.assertEqual(response.context["sort"], "-like")

    def test_saved_sort_cookie_is_ignored_when_saved_select_is_off(self):
        self.client.cookies["is_saved_select"] = "off"
        self.client.cookies["author_sort"] = "-upload_time"
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertEqual(response.context["sort"], "-id")

    def test_invalid_sort_cookie_uses_default(self):
        self.client.cookies["author_sort"] = "invalid"
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertEqual(response.context["sort"], "-id")

    def test_not_cached_by_browser(self):
        # 並び替えはcookieによって変わるため、別の並び替えを選んだ後にキャッシュされた古い並び順を表示しない
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("public", response["Cache-Control"])

    def test_description_does_not_depend_on_sort(self):
        # 説明文（meta description）は並び替えによって変わらない
        self._create_sort_songs()
        url = reverse("subekashi:author", args=[self.author.id])
        descriptions = {self.client.get(url, {"sort": sort}).context["description"] for sort in ["-id", "upload_time", "random"]}
        self.assertEqual(descriptions, {"ビューテスト作者の曲一覧：並び替え2020年, 並び替え2024年, 作者ビューテスト曲"})


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_only_youtube_items_have_youtube_flag(self):
        # YouTube由来の指標(総再生回数・総高評価数)のみYouTubeアイコンを表示する (#896)
        Song.objects.create(title="曲", view=100, like=10)

        response = self.client.get(reverse("subekashi:stats"))

        youtube_labels = [item["label"] for item in response.context["stats_items"] if item.get("is_youtube")]
        self.assertEqual(youtube_labels, ["総再生回数", "総高評価数"])
        self.assertContains(response, "fa-youtube")

    def test_imitated_authors_item_counts_authors_imitated_at_least_once(self):
        # 1度でも模倣されたことのある作者数（#1163）。模倣曲の作者や模倣されていない作者は数えない
        imitated_author = Author.objects.create(name="模倣された作者")
        imitator = Author.objects.create(name="模倣した作者")
        original = Song.objects.create(title="原曲")
        original.authors.add(imitated_author)
        imitate = Song.objects.create(title="模倣曲")
        imitate.authors.add(imitator)
        imitate.imitates.add(original)

        response = self.client.get(reverse("subekashi:stats"))

        stats_items = {item["label"]: item["value"] for item in response.context["stats_items"]}
        self.assertEqual(stats_items["総作者数"], 2)
        self.assertEqual(stats_items["模倣された作者数"], 1)
        self.assertContains(response, "模倣された作者数")

    def test_imitated_authors_item_reflects_songrange_filter(self):
        subeana_author = Author.objects.create(name="すべあな界隈の作者")
        xx_author = Author.objects.create(name="界隈外の作者")
        subeana_song = Song.objects.create(title="すべあな曲", is_subeana=True)
        subeana_song.authors.add(subeana_author)
        xx_song = Song.objects.create(title="界隈外曲", is_subeana=False)
        xx_song.authors.add(xx_author)
        imitate = Song.objects.create(title="模倣曲", is_subeana=True)
        imitate.imitates.add(subeana_song, xx_song)

        response = self.client.get(reverse("subekashi:stats"), {"songrange": "xx"})

        stats_items = {item["label"]: item["value"] for item in response.context["stats_items"]}
        self.assertEqual(stats_items["模倣された作者数"], 1)

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

    def test_highlighted_month_is_none_when_only_year_specified(self):
        Song.objects.create(title="曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))
        response = self.client.get(reverse("subekashi:stats"), {"year": "2024"})
        self.assertIsNone(response.context["highlighted_month"])

    def test_highlighted_month_is_none_when_only_month_specified(self):
        Song.objects.create(title="曲", upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))
        response = self.client.get(reverse("subekashi:stats"), {"month": "1"})
        self.assertIsNone(response.context["highlighted_month"])

    def test_highlighted_month_set_when_year_and_month_both_specified(self):
        # year・month両方指定時、グラフはmonthを無視してその年全体を表示するため
        # （コードレビュー指摘対応）、選択していた月をJS側の棒の色分け用に渡す
        Stats.objects.create(year=2024, month=6, songrange="all", song_count=1)
        # is_subeana両方の曲を用意し、songrangeが"all"以外に自動解決されないようにする
        Song.objects.create(title="曲", upload_time=datetime(2024, 6, 1, tzinfo=dt_timezone.utc), is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)

        response = self.client.get(reverse("subekashi:stats"), {"year": "2024", "month": "6"})

        self.assertEqual(response.context["highlighted_month"], 6)
        self.assertContains(response, 'id="highlighted-month-data"')

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

    def test_monthly_stats_includes_imitated_authors_and_delta(self):
        # 1度でも模倣されたことのある作者数（#1163）が累積値と月ごとの差分の両方でグラフに渡される
        Stats.objects.create(year=2024, month=1, songrange="all", total_imitated_authors=2)
        Stats.objects.create(year=2024, month=2, songrange="all", total_imitated_authors=5)
        Song.objects.create(title="すべあな曲", is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)

        response = self.client.get(reverse("subekashi:stats"))

        monthly_stats = response.context["monthly_stats"]
        self.assertEqual([row["total_imitated_authors"] for row in monthly_stats], [2, 5])
        self.assertEqual([row["total_imitated_authors_delta"] for row in monthly_stats], [2, 3])

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

        self.assertEqual(response.context["kenreki"]["points"], 4)
        self.assertNotContains(response, "kenreki-keyboard-scroll")

    def test_kenreki_stat_value_displays_points_not_song_count_stat(self):
        # #1099: view=1(1段階=1pt)の曲を1曲のみ登録し、鍵歴のpt合計(1)が
        # そのまま表示されることを確認する
        Song.objects.create(title="曲", view=1, like=0)

        response = self.client.get(reverse("subekashi:stats"))

        self.assertEqual(response.context["kenreki"]["points"], 1)
        match = re.search(
            r'<p class="icon-p">鍵歴</p>\s*<p class="stat-value"[^>]*>(\d+)</p>',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), 1)

    def test_kenreki_reflects_songrange_year_month_filters(self):
        # 総合統計ページの鍵歴は他の統計項目と同様、絞り込みの影響を受ける
        # （authorページの鍵歴は全期間の累積実績で絞り込みの影響を受けないのとは異なる仕様）
        Song.objects.create(title="2024年の曲", view=20, like=2, upload_time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc))
        Song.objects.create(title="2025年の曲", view=1000, like=0, upload_time=datetime(2025, 1, 1, tzinfo=dt_timezone.utc))

        unfiltered = self.client.get(reverse("subekashi:stats"))
        filtered_2024 = self.client.get(reverse("subekashi:stats"), {"year": "2024"})

        # 全期間: 2024年の曲(view=20:2段階=2pt, like=2:2段階=2pt=4pt) + 2025年の曲(view=1000:7段階=7pt) = 11pt
        # （鍵歴はSongごとに算出して合計するため、集計後のview=1020に対する閾値判定ではない）
        self.assertEqual(unfiltered.context["kenreki"]["points"], 11)
        # 2024年のみ: view=20(2段階=2pt)+like=2(2段階=2pt)=4pt
        self.assertEqual(filtered_2024.context["kenreki"]["points"], 4)

    def test_kenreki_stat_value_never_colored_even_when_overflowing(self):
        # 総合統計ページの鍵歴はstat-valueの着色をしない（authorページとの仕様差、コードレビュー指摘対応）
        # view/likeはMySQLのIntegerField（INT、上限约21億）の範囲内に収める必要があるため、
        # 段階数を十分に振り切れる大きさとして2*10**9を使う（#593、MySQL移行時に10**12だと
        # Out of range value for columnエラーになることを確認済み）
        for i in range(5):
            Song.objects.create(title=f"曲{i}", view=2 * 10 ** 9, like=2 * 10 ** 9)

        response = self.client.get(reverse("subekashi:stats"))

        self.assertGreaterEqual(response.context["kenreki"]["points"], 88)
        self.assertIsNone(response.context["kenreki"]["overflow_color"])
        self.assertNotContains(response, "style=\"color: hsl(")

    @staticmethod
    def _is_radio_checked(response, radio_id):
        # stats.htmlは各<input>を1行で出力する前提のパターン（re.DOTALL無し）。
        # 将来templateが複数行に変わった場合はこのヘルパーも合わせて見直すこと（コードレビュー指摘対応）
        match = re.search(rf'<input[^>]*id="{radio_id}"[^>]*>', response.content.decode())
        assert match is not None, f'{radio_id} not found in response'
        return "checked" in match.group(0)

    def _create_all_songrange_stats(self):
        # monthly_statsが存在しないとchart-mode/chart-seriesのラジオボタン自体が
        # 描画されないため、Statsレコードを用意する。また、songrangeは実在するSongの
        # 種類に応じてresolve_songrange()が自動選択するため、"全て"が選ばれるよう
        # is_subeana=True/False両方のSongも用意する
        Song.objects.create(title="すべあな曲", is_subeana=True)
        Song.objects.create(title="界隈外曲", is_subeana=False)
        Stats.objects.create(year=2024, month=1, songrange="all", song_count=2)

    def test_chart_settings_default_when_no_cookie(self):
        # #1111: cookie未設定時は月ごと/曲数がデフォルトで選択される
        self._create_all_songrange_stats()

        response = self.client.get(reverse("subekashi:stats"))

        self.assertEqual(response.context["chart_mode"], "monthly")
        self.assertEqual(response.context["chart_series"], "song_count")
        self.assertTrue(self._is_radio_checked(response, "chart-mode-monthly"))
        self.assertFalse(self._is_radio_checked(response, "chart-mode-cumulative"))
        self.assertTrue(self._is_radio_checked(response, "chart-series-song-count"))

    def test_chart_settings_reflect_cookie_values(self):
        # #1111: songrange/year/month用のformとは別に、グラフ表示設定はcookieで
        # 引き継がれる（stats.js側がchart-mode/chart-series変更時にcookieへ保存する）
        self._create_all_songrange_stats()
        self.client.cookies["stats_chart_mode"] = "cumulative"
        self.client.cookies["stats_chart_series"] = "total_view"

        response = self.client.get(reverse("subekashi:stats"))

        self.assertEqual(response.context["chart_mode"], "cumulative")
        self.assertEqual(response.context["chart_series"], "total_view")
        self.assertTrue(self._is_radio_checked(response, "chart-mode-cumulative"))
        self.assertFalse(self._is_radio_checked(response, "chart-mode-monthly"))
        self.assertTrue(self._is_radio_checked(response, "chart-series-total-view"))
        self.assertFalse(self._is_radio_checked(response, "chart-series-song-count"))

    def test_chart_series_imitated_authors_is_selectable_by_cookie(self):
        # 1度でも模倣されたことのある作者数（#1163）をグラフの系列として選択できる
        self._create_all_songrange_stats()
        self.client.cookies["stats_chart_series"] = "total_imitated_authors"

        response = self.client.get(reverse("subekashi:stats"))

        self.assertEqual(response.context["chart_series"], "total_imitated_authors")
        self.assertTrue(self._is_radio_checked(response, "chart-series-total-imitated-authors"))
        self.assertFalse(self._is_radio_checked(response, "chart-series-song-count"))

    def test_chart_settings_reflect_cookie_across_songrange_filter_change(self):
        # #1111の再現ケース: songrange変更（ページ全体の再読み込み相当）を挟んでも
        # グラフ表示設定(cookie)が維持されること
        self.client.cookies["stats_chart_mode"] = "cumulative"
        Song.objects.create(title="すべあな曲", is_subeana=True)

        response = self.client.get(reverse("subekashi:stats"), {"songrange": "subeana"})

        self.assertEqual(response.context["chart_mode"], "cumulative")

    def test_invalid_chart_settings_cookie_falls_back_to_default(self):
        # 不正なcookie値（改ざん・旧バージョンの値等）はデフォルトにフォールバックする
        self.client.cookies["stats_chart_mode"] = "invalid-value"
        self.client.cookies["stats_chart_series"] = "invalid-value"

        response = self.client.get(reverse("subekashi:stats"))

        self.assertEqual(response.context["chart_mode"], "monthly")
        self.assertEqual(response.context["chart_series"], "song_count")


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_only_youtube_items_have_youtube_flag(self):
        # YouTube由来の指標(総再生回数・総高評価数)のみYouTubeアイコンを表示する (#896)
        Song.objects.create(title="この作者の曲", view=100, like=10).authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        youtube_labels = [item["label"] for item in response.context["stats_items"] if item.get("is_youtube")]
        self.assertEqual(youtube_labels, ["総再生回数", "総高評価数"])
        self.assertContains(response, "fa-youtube")

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
        self.assertEqual(response.context["kenreki"]["points"], 1)

    def test_kenreki_points_reflects_total_view_and_like(self):
        # view=20(2段階=2pt)+like=2(2段階=2pt)=合計4pt
        Song.objects.create(title="曲", view=20, like=2).authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        self.assertEqual(response.context["kenreki"]["points"], 4)

    def test_kenreki_stat_value_displays_points_not_song_count_stat(self):
        # #1099: view=1(1段階=1pt)の曲を1曲のみ登録し、鍵歴のpt合計(1)が
        # そのまま表示されることを確認する
        Song.objects.create(title="曲", view=1, like=0).authors.add(self.author)

        response = self.client.get(reverse("subekashi:author_stats", args=[self.author.id]))

        self.assertEqual(response.context["kenreki"]["points"], 1)
        match = re.search(
            r'<p class="icon-p">鍵歴</p>\s*<p class="stat-value"[^>]*>(\d+)</p>',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), 1)

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

        self.assertEqual(unfiltered.context["kenreki"]["points"], filtered.context["kenreki"]["points"])
        self.assertGreater(filtered.context["kenreki"]["points"], 0)


@override_settings(STORAGES=STATIC_STORAGE)
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
        # 作者ページボタンは.action-buttons内の一番左（DOM順で最初）に配置する（#1024）
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

    def test_past_alias_with_slash_in_name_links_to_channel(self):
        # #1127: 別名に"/"が含まれていてもNoReverseMatchにならずchannelへのリンクが表示される
        Author.objects.create(name="別名/スラッシュ")
        AuthorAlias.objects.create(name="別名/スラッシュ", author=self.author, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("subekashi:channel", args=["別名/スラッシュ"]))

    def test_reload_button_present(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, "reloadPage()")
        self.assertContains(response, "fa-redo")

    def test_add_button_has_plus_icon(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, "fa-plus")


@override_settings(STORAGES=STATIC_STORAGE)
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
        # （10クエリ目は#1008で追加した名義の統一先の候補一覧取得、11クエリ目は#1230で追加した、
        # Cの名前を以前の名称として登録しているAへ名義が統一されているかどうかの判定用のCの曲数取得）
        with self.assertNumQueries(11):
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


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_past_description_mentions_unify_name(self):
        # past種別の説明に、名義の統一先として選択できる旨を含める（#1029、#1137）
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        content = response.content.decode()
        past_option = content[content.index('value="past"'):content.index('</option>', content.index('value="past"'))]
        self.assertIn("名義を統一する", past_option)

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
        select_index = content.index('id="alias-type"')
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


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_get_response_is_not_cached(self):
        # #1135: SongEditViewと同様、キャッシュされた古いフォームの送信で編集が巻き戻らないようにする
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("public", response["Cache-Control"])

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
        # 更新ボタンを名義の統一の確認画面と同様のaction-button形式にする（#1024）
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, "更新する")
        self.assertContains(response, '<button type="submit" class="action-button black-action-button">')

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


@override_settings(STORAGES=STATIC_STORAGE)
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


@override_settings(STORAGES=STATIC_STORAGE)
class AuthorUnifyNameSetViewTest(TestCase):
    """AuthorUnifyNameSetView (/authors/<id>/aliases/unify) のテスト（#1008、#1029、#1137）"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="現在の名義")
        self.past_alias = AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")

    def _post(self, name, author=None):
        author = author or self.author
        return self.client.post(reverse("subekashi:author_unify_name_set", args=[author.id]), {"name": name})

    def _aliases_url(self, author, toast):
        return reverse("subekashi:author_aliases", args=[author.id]) + f"?toast={toast}"

    def test_nonexistent_author_returns_404(self):
        response = self.client.post(
            reverse("subekashi:author_unify_name_set", args=[99999]), {"name": "以前の名義"}
        )
        self.assertEqual(response.status_code, 404)

    @patch("subekashi.views.author_alias.send_discord")
    def test_selecting_current_name_with_nothing_to_move_is_noop(self, mock_send_discord):
        # 統一先が現在の名義で、移す曲も無い場合は何も変更せず、Discord通知も送らない
        response = self._post(self.author.name)

        self.assertRedirects(response, self._aliases_url(self.author, "unify_noop"))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertFalse(mock_send_discord.called)
        self.assertEqual(History.objects.count(), 0)

    def test_selecting_current_name_moves_songs_of_past_alias_author(self):
        # フォームを変更しない（現在の名義のまま）送信でも、以前の名称と同名の
        # 別Authorの曲を現在の名義へ統一できる（#1137）
        past_author = Author.objects.create(name="以前の名義")
        song = Song.objects.create(title="以前の名義の曲")
        song.authors.add(past_author)

        response = self._post(self.author.name)

        self.assertRedirects(response, self._aliases_url(self.author, "unify"))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertEqual(list(song.authors.all()), [self.author])
        # 曲を移したAuthorは削除されず、曲数が0になるだけ
        self.assertTrue(Author.objects.filter(pk=past_author.pk).exists())
        self.assertEqual(past_author.songs.count(), 0)
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())

    def test_selecting_past_alias_swaps_name_and_reregisters_old_name_as_past(self):
        response = self._post("以前の名義")

        self.assertRedirects(response, self._aliases_url(self.author, "unify"))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "以前の名義")
        # 選ばれた側の別名行は消え、旧名が新たなpast別名として登録される
        self.assertFalse(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())
        new_alias = AuthorAlias.objects.get(name="現在の名義")
        self.assertEqual(new_alias.author, self.author)
        self.assertEqual(new_alias.alias_type, "past")

    def test_selecting_past_alias_also_moves_songs_of_other_past_alias_authors(self):
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")
        other_past_author = Author.objects.create(name="以前の名義2")
        song = Song.objects.create(title="以前の名義2の曲")
        song.authors.add(other_past_author)

        self._post("以前の名義")

        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "以前の名義")
        self.assertEqual(list(song.authors.all()), [self.author])
        self.assertTrue(Author.objects.filter(pk=other_past_author.pk).exists())
        self.assertEqual(other_past_author.songs.count(), 0)

    def test_authors_matching_non_past_aliases_are_not_unified(self):
        # 別名義（another）等、past以外の種別は意図的に区別すべき名義のため統一の対象外
        AuthorAlias.objects.create(name="別名義", author=self.author, alias_type="another")
        another_author = Author.objects.create(name="別名義")
        song = Song.objects.create(title="別名義の曲")
        song.authors.add(another_author)
        Song.objects.create(title="以前の名義の曲").authors.add(Author.objects.create(name="以前の名義"))

        self._post(self.author.name)

        self.assertEqual(list(song.authors.all()), [another_author])

    def test_selecting_non_past_alias_type_is_rejected(self):
        AuthorAlias.objects.create(name="別名義候補", author=self.author, alias_type="another")
        response = self._post("別名義候補")
        self.assertRedirects(response, self._aliases_url(self.author, "unify_error"))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")

    def test_selecting_name_of_existing_author_makes_it_the_target(self):
        # Author.nameはuniqueのため、選択した名義と同名の既存Authorがあればそれを統一先とし、
        # このauthorの曲・別名・作者リンクを全てそちらへ移す。このauthor自体は削除しない（#1137）
        target = Author.objects.create(name="以前の名義")
        target_song = Song.objects.create(title="統一先の曲")
        target_song.authors.add(target)
        target_link = AuthorLink.objects.create(url="https://example.com/target", author=target)
        own_song = Song.objects.create(title="このauthorの曲")
        own_song.authors.add(self.author)
        own_link = AuthorLink.objects.create(url="https://example.com/own", author=self.author)
        own_alias = AuthorAlias.objects.create(name="このauthorの略称", author=self.author, alias_type="abbr")

        response = self._post("以前の名義")

        self.assertRedirects(response, self._aliases_url(target, "unify"))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertEqual(self.author.songs.count(), 0)
        self.assertEqual(set(target.songs.all()), {target_song, own_song})

        own_link.refresh_from_db()
        self.assertEqual(own_link.author_id, target.id)
        target_link.refresh_from_db()
        self.assertEqual(target_link.author_id, target.id)
        own_alias.refresh_from_db()
        self.assertEqual(own_alias.author_id, target.id)

        # 選択した別名は統一先自身の名前と同じになるため削除され、旧名が統一先のpast別名になる
        self.assertFalse(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())
        old_name_alias = AuthorAlias.objects.get(name="現在の名義")
        self.assertEqual(old_name_alias.author_id, target.id)
        self.assertEqual(old_name_alias.alias_type, "past")
        self.assertFalse(self.author.aliases.exists())

    def test_existing_target_reuses_its_alias_matching_old_name(self):
        # 統一先が既にold_nameと同名の別名を持っている場合、重複登録（IntegrityError）を
        # 起こさずにその別名を活かし、他のpast別名と同様に選択候補になるようalias_typeを"past"へ揃える
        target = Author.objects.create(name="以前の名義")
        existing_alias = AuthorAlias.objects.create(name="現在の名義", author=target, alias_type="another")

        response = self._post("以前の名義")

        self.assertRedirects(response, self._aliases_url(target, "unify"))
        existing_alias.refresh_from_db()
        self.assertEqual(existing_alias.author_id, target.id)
        self.assertEqual(existing_alias.alias_type, "past")
        self.assertEqual(AuthorAlias.objects.filter(name="現在の名義").count(), 1)

    def test_existing_target_with_same_group_alias_does_not_fail(self):
        # グループ名は(name, author)単位でユニークなため、統一先が既に同じグループ名を
        # 持つ場合はこのauthor側のものを移さずに削除する
        target = Author.objects.create(name="以前の名義")
        AuthorAlias.objects.create(name="合作グループ", author=target, alias_type="group")
        AuthorAlias.objects.create(name="合作グループ", author=self.author, alias_type="group")

        response = self._post("以前の名義")

        self.assertRedirects(response, self._aliases_url(target, "unify"))
        self.assertEqual(AuthorAlias.objects.filter(name="合作グループ", author=target).count(), 1)
        self.assertFalse(AuthorAlias.objects.filter(name="合作グループ", author=self.author).exists())

    def test_moved_songs_record_history(self):
        # 統一によりauthorが変わる曲それぞれの編集履歴一覧にも記録する（#1034）。
        # 曲を移したAuthorと統一先が同名になる場合もあるため、idを含めて実体が変わったことを明示する
        target = Author.objects.create(name="以前の名義")
        song1 = Song.objects.create(title="統一対象曲1")
        song1.authors.add(self.author)
        song2 = Song.objects.create(title="統一対象曲2")
        song2.authors.add(self.author)
        unrelated_song = Song.objects.create(title="無関係な曲")
        unrelated_song.authors.add(Author.objects.create(name="無関係な作者"))

        self._post("以前の名義")

        for song in (song1, song2):
            # 将来同様の重複バグが再発した際に検知できるよう、件数も明示的に確認する
            self.assertEqual(History.get_for_song(song).count(), 1)
            history = History.get_for_song(song).first()
            self.assertEqual(history.history_type, "edit")
            self.assertEqual(history.title, "名義の統一により作者を統合")
            self.assertEqual(
                history.changes[1], ["作者", f"id={self.author.id}, name=現在の名義", f"id={target.id}, name=以前の名義"]
            )
        self.assertEqual(History.get_for_song(unrelated_song).count(), 0)

    def test_rename_records_history_on_existing_songs(self):
        # 名前の変更により作者の表示名が変わる、元々このauthorに紐づいている曲にも記録する（#1034）
        own_song = Song.objects.create(title="既存の曲")
        own_song.authors.add(self.author)

        self._post("以前の名義")

        self.assertEqual(History.get_for_song(own_song).count(), 1)
        history = History.get_for_song(own_song).first()
        self.assertEqual(history.history_type, "edit")
        self.assertEqual(history.title, "名義の統一により作者名を変更")
        self.assertEqual(history.changes[1], ["作者", "現在の名義", "以前の名義"])

    def test_moved_and_renamed_song_histories_both_created_in_same_request(self):
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")
        moved_song = Song.objects.create(title="統一対象曲")
        moved_song.authors.add(Author.objects.create(name="以前の名義2"))
        own_song = Song.objects.create(title="元々このauthorの曲")
        own_song.authors.add(self.author)

        self._post("以前の名義")

        self.assertEqual(History.get_for_song(moved_song).count(), 1)
        self.assertEqual(History.get_for_song(moved_song).first().title, "名義の統一により作者を統合")
        self.assertEqual(History.get_for_song(own_song).count(), 1)
        self.assertEqual(History.get_for_song(own_song).first().title, "名義の統一により作者名を変更")

    def test_song_shared_by_author_and_moved_author_gets_only_one_history(self):
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")
        shared_song = Song.objects.create(title="共著の曲")
        shared_song.authors.add(self.author, Author.objects.create(name="以前の名義2"))

        self._post("以前の名義")

        self.assertEqual(History.get_for_song(shared_song).count(), 1)
        self.assertEqual(list(shared_song.authors.all()), [self.author])

    def test_post_creates_history_on_target_and_moved_authors(self):
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")
        moved_author = Author.objects.create(name="以前の名義2")
        Song.objects.create(title="統一対象曲").authors.add(moved_author)

        self._post("以前の名義")

        history = History.get_for_author(self.author).first()
        self.assertEqual(history.history_type, "edit")
        self.assertEqual(history.title, "名義を『以前の名義』に統一")
        moved_row = ["統一した作者", f"id={moved_author.id}, name=以前の名義2", f"id={self.author.id}, name=以前の名義"]
        self.assertEqual(history.changes[1:], [["名義", "現在の名義", "以前の名義"], moved_row])
        # 曲を移したAuthorは削除されずに残るため、そちらの編集履歴一覧にも統一先を記録する
        moved_history = History.get_for_author(moved_author).first()
        self.assertEqual(moved_history.title, "名義を『以前の名義』に統一")
        self.assertEqual(moved_history.changes[1:], [moved_row])

    def test_authors_without_songs_are_not_recorded_as_unified(self):
        # 以前の名称と同名のAuthorが存在しても、曲を持たなければ何も変わらないため記録しない
        empty_author = Author.objects.create(name="以前の名義2")
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")

        self._post("以前の名義")

        history = History.get_for_author(self.author).first()
        self.assertEqual(history.changes[1:], [["名義", "現在の名義", "以前の名義"]])
        self.assertEqual(History.get_for_author(empty_author).count(), 0)

    def test_moved_authors_own_history_is_kept(self):
        # 曲を移したAuthorは削除しないため、過去のHistoryの紐付けもそのまま残る（#1137）
        past_author = Author.objects.create(name="以前の名義")
        Song.objects.create(title="以前の名義の曲").authors.add(past_author)
        old_history = History.create_for_author(
            author=past_author, title="別名を追加", history_type="edit", changes=None,
            editor=Editor.objects.create(ip="127.0.0.9"),
        )

        self._post(self.author.name)

        old_history.refresh_from_db()
        self.assertEqual(old_history.author_id, past_author.id)
        self.assertEqual(old_history.title, "別名を追加")

    def test_moving_songs_query_count_does_not_scale_with_song_count(self):
        # 曲をidでまとめて付け替え、編集履歴もbulk_create()でまとめて作成することで、
        # 統一対象の曲数が増えてもクエリ数が変わらないことを確認する。
        # Editor.get_or_create_from_ip()はIPごとに最初の1回だけINSERTが発生するため、
        # 計測対象のリクエストより前にウォームアップしてクエリ数の比較に影響しないようにする
        warmup_author = Author.objects.create(name="ウォームアップ用作者")
        AuthorAlias.objects.create(name="ウォームアップ用別名", author=warmup_author, alias_type="past")
        self._post("ウォームアップ用別名", author=warmup_author)

        author_one_song = Author.objects.create(name="現在の名義A")
        AuthorAlias.objects.create(name="以前の名義A", author=author_one_song, alias_type="past")
        Song.objects.create(title="曲A").authors.add(Author.objects.create(name="以前の名義A"))

        with CaptureQueriesContext(connection) as ctx_one_song:
            self._post("現在の名義A", author=author_one_song)

        author_many_songs = Author.objects.create(name="現在の名義B")
        AuthorAlias.objects.create(name="以前の名義B", author=author_many_songs, alias_type="past")
        past_author_many_songs = Author.objects.create(name="以前の名義B")
        for i in range(5):
            Song.objects.create(title=f"曲B{i}").authors.add(past_author_many_songs)

        with CaptureQueriesContext(connection) as ctx_many_songs:
            self._post("現在の名義B", author=author_many_songs)

        self.assertEqual(author_many_songs.songs.count(), 5)
        self.assertEqual(len(ctx_one_song.captured_queries), len(ctx_many_songs.captured_queries))

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self._post("以前の名義")
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("現在の名義", content)
        self.assertIn("以前の名義", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_notification_mentions_moved_authors(self, mock_send_discord):
        past_author = Author.objects.create(name="以前の名義")
        Song.objects.create(title="以前の名義の曲").authors.add(past_author)
        mock_send_discord.return_value = True

        self._post(self.author.name)

        content = mock_send_discord.call_args[0][1]
        self.assertIn(f"Author(id={past_author.id}", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_prevents_changes(self, mock_send_discord):
        past_author = Author.objects.create(name="以前の名義2")
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")
        song = Song.objects.create(title="以前の名義2の曲")
        song.authors.add(past_author)
        mock_send_discord.return_value = False

        response = self._post("以前の名義")

        self.assertEqual(response.status_code, 500)
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())
        self.assertEqual(list(song.authors.all()), [past_author])
        self.assertEqual(History.objects.count(), 0)

    @patch("subekashi.views.author_alias.send_discord")
    def test_alias_deleted_concurrently_during_discord_wait_redirects_with_error(self, mock_send_discord):
        # send_discord()（ネットワークI/O）の完了を待つ間に、別のリクエストが対象の
        # past別名を削除してしまうケースを、send_discordのside_effectで模擬する。
        # DoesNotExistが未処理の例外(500)にならず、他の異常系と同じくtoast=unify_error
        # へ穏当にリダイレクトされることを確認する
        def delete_alias_then_succeed(url, content):
            self.past_alias.delete()
            return True

        mock_send_discord.side_effect = delete_alias_then_succeed

        response = self._post("以前の名義")

        self.assertRedirects(response, self._aliases_url(self.author, "unify_error"))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    @patch("subekashi.views.author_alias.send_discord")
    def test_existing_target_deleted_concurrently_during_discord_wait_falls_back_to_rename(self, mock_send_discord):
        # send_discord()の完了を待つ間に、統一先の既存Authorが別のリクエストで削除されてしまう
        # ケース。統一先を再取得し、このauthorの名前を変更する通常の統一として完了する
        target = Author.objects.create(name="以前の名義")

        def delete_target_then_succeed(url, content):
            target.delete()
            return True

        mock_send_discord.side_effect = delete_target_then_succeed

        response = self._post("以前の名義")

        self.assertRedirects(response, self._aliases_url(self.author, "unify"))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "以前の名義")

    @patch("subekashi.views.author_alias.send_discord")
    def test_unrelated_alias_matching_old_name_created_during_discord_wait_is_not_corrupted(self, mock_send_discord):
        # send_discord()の待機中に、無関係な別authorがold_nameと同名のAuthorAliasを
        # 新規作成してしまうケース（TOCTOU）。所有者チェックなしに再利用（alias_typeの
        # 書き換え）してしまうと無関係な別authorのデータを破壊することになるため、
        # 安全側に倒して統一全体をロールバックすることを確認する
        target = Author.objects.create(name="以前の名義")
        own_song = Song.objects.create(title="このauthorの曲")
        own_song.authors.add(self.author)
        unrelated_author = Author.objects.create(name="無関係な作者")

        def create_unrelated_alias_then_succeed(url, content):
            AuthorAlias.objects.create(name="現在の名義", author=unrelated_author, alias_type="another")
            return True

        mock_send_discord.side_effect = create_unrelated_alias_then_succeed

        response = self._post("以前の名義")

        self.assertRedirects(response, self._aliases_url(self.author, "unify_error"))
        # 曲の付け替え・別名の移動ともにロールバックされる
        self.assertEqual(list(own_song.authors.all()), [self.author])
        self.assertEqual(target.songs.count(), 0)
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk, author=self.author).exists())
        # 無関係な別名は書き換えられない
        unrelated_alias = AuthorAlias.objects.get(name="現在の名義")
        self.assertEqual(unrelated_alias.author_id, unrelated_author.id)
        self.assertEqual(unrelated_alias.alias_type, "another")

    def test_old_name_conflicting_with_existing_alias_is_rejected_before_discord(self):
        # AuthorAlias.nameはグローバルにuniqueなため、旧名(old_name)が既に別のauthorの
        # 別名として登録されている場合、以前の名称として再登録できずIntegrityErrorになる。
        # これは同時実行のレースではなく既存データ次第で毎回決定的に失敗するため、
        # Discord通知を送る前に弾く（通知だけ成功してDBが更新されない不整合を避ける）
        other = Author.objects.create(name="別の作者")
        AuthorAlias.objects.create(name=self.author.name, author=other, alias_type="another")

        with patch("subekashi.views.author_alias.send_discord") as mock_send_discord:
            response = self._post("以前の名義")
            self.assertFalse(mock_send_discord.called)

        self.assertRedirects(response, self._aliases_url(self.author, "unify_error"))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())

    def test_alias_list_page_shows_unify_name_form_when_past_alias_exists(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, 'id="unify-name-form"')
        self.assertContains(response, "名義を統一する")
        self.assertContains(response, 'data-tutorial="unify-name"')
        self.assertContains(
            response, f'action="{reverse("subekashi:author_unify_name_confirm", args=[self.author.id])}"'
        )

    def test_alias_list_page_hides_unify_name_form_when_no_past_alias(self):
        # フォーム本体（HTML要素）が描画されないことを確認する。判定用JS自体は
        # フォームの有無に関わらず読み込まれ、要素が存在しない場合は何もせず
        # no-opする実装のため、bareな文字列一致ではなくid属性の有無で判定する
        author = Author.objects.create(name="別名なし作者")
        response = self.client.get(reverse("subekashi:author_aliases", args=[author.id]))
        self.assertNotContains(response, 'id="unify-name-form"')

    def test_unify_name_form_lists_past_aliases_above_arrow_and_current_name_below_checked(self):
        # 「[ ] 以前の名称 ↓ [x] 現在の名義」の並びで、初期状態の統一先は現在の名義（#1137）
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        content = response.content.decode()
        past_index = content.index('value="以前の名義"')
        arrow_index = content.index('id="unify-name-arrow"')
        current_index = content.index('value="現在の名義"')
        self.assertLess(past_index, arrow_index)
        self.assertLess(arrow_index, current_index)
        current_input = content[current_index:content.index(">", current_index)]
        self.assertIn("checked", current_input)
        past_input = content[past_index:content.index(">", past_index)]
        self.assertNotIn("checked", past_input)

    def test_unify_name_submit_button_is_enabled_and_labeled_unify(self):
        # フォームを変更しなくても統一できるよう、ボタンはdisabledにしない（#1137）
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        content = response.content.decode()
        submit_index = content.index('id="unify-name-submit"')
        submit_button = content[submit_index:content.index("</button>", submit_index)]
        self.assertNotIn("disabled", submit_button)
        self.assertIn("統一する", submit_button)


@override_settings(STORAGES=STATIC_STORAGE)
class AuthorAliasesUnifyNameStatusTest(TestCase):
    """別名一覧画面の、名義が統一されているかどうかの表示のテスト（#1230）"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")

    def _get(self, author=None):
        author = author or self.author
        return self.client.get(reverse("subekashi:author_aliases", args=[author.id]))

    def _status(self, response, status_id="unify-name-status"):
        # class属性も確かめられるよう、id属性を持つ<p>タグの先頭から切り出す
        content = response.content.decode()
        start = content.rindex("<p ", 0, content.index(f'id="{status_id}"'))
        return content[start:content.index("</p>", start)]

    def test_shows_unified_when_no_author_matches_past_alias(self):
        status = self._status(self._get())
        self.assertIn("名義は統一されています", status)
        self.assertIn('class="unify-name-status ok"', status)
        self.assertIn("fa-check-circle", status)

    def test_shows_unified_when_author_matching_past_alias_has_no_songs(self):
        # 統一済みの作者は削除されず、曲数0で残る（#1137）
        Author.objects.create(name="以前の名義")
        self.assertIn("名義は統一されています", self._status(self._get()))

    def test_shows_not_unified_with_past_alias_author_and_song_count(self):
        past_author = Author.objects.create(name="以前の名義")
        for title in ["以前の名義の曲1", "以前の名義の曲2"]:
            Song.objects.create(title=title).authors.add(past_author)

        status = self._status(self._get())

        self.assertIn("名義が統一されていません", status)
        # 統一されていないことは誤りではないため、warningではなくinfoで表示する
        self.assertIn('class="unify-name-status info"', status)
        self.assertIn("fa-info-circle", status)
        self.assertNotIn("warning", status)
        self.assertIn("2曲", status)
        self.assertIn(f'href="{reverse("subekashi:author", args=[past_author.id])}"', status)

    def test_lists_all_past_alias_authors_with_songs_and_counts_co_authored_song_once(self):
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")
        AuthorAlias.objects.create(name="以前の名義3", author=self.author, alias_type="past")
        past_author = Author.objects.create(name="以前の名義")
        past_author2 = Author.objects.create(name="以前の名義2")
        past_author3 = Author.objects.create(name="以前の名義3")
        Song.objects.create(title="共著の曲").authors.add(past_author, past_author2)

        status = self._status(self._get())

        self.assertIn("1曲", status)
        self.assertIn(reverse("subekashi:author", args=[past_author.id]), status)
        self.assertIn(reverse("subekashi:author", args=[past_author2.id]), status)
        # 曲の無い作者は統一されていない作者として表示しない
        self.assertNotIn(reverse("subekashi:author", args=[past_author3.id]), status)

    def test_lists_past_alias_authors_in_unify_form_order(self):
        # 統一するフォームの候補（別名の登録順）と同じ順に並べる。作者のid順・名前順のどちらとも
        # 異なる順になるよう、後に登録した別名ほど作者のidと名前が小さくなるようにする
        AuthorAlias.objects.create(name="ん以前の名義", author=self.author, alias_type="past")
        AuthorAlias.objects.create(name="あ以前の名義", author=self.author, alias_type="past")
        first_author = Author.objects.create(name="あ以前の名義")
        second_author = Author.objects.create(name="ん以前の名義")
        for past_author in [first_author, second_author]:
            Song.objects.create(title=f"{past_author.name}の曲").authors.add(past_author)

        status = self._status(self._get())

        self.assertLess(
            status.index(reverse("subekashi:author", args=[second_author.id])),
            status.index(reverse("subekashi:author", args=[first_author.id])),
        )

    def test_authors_matching_non_past_aliases_do_not_affect_status(self):
        # 別名義（another）等、past以外の種別は統一の対象外
        AuthorAlias.objects.create(name="別名義", author=self.author, alias_type="another")
        Song.objects.create(title="別名義の曲").authors.add(Author.objects.create(name="別名義"))
        self.assertIn("名義は統一されています", self._status(self._get()))

    def test_status_matches_unify_noop_after_unifying(self):
        # 表示が「統一されていない」の状態から実際に統一すると、「統一されています」に変わる
        past_author = Author.objects.create(name="以前の名義")
        Song.objects.create(title="以前の名義の曲").authors.add(past_author)
        self.assertIn("名義が統一されていません", self._status(self._get()))

        with patch("subekashi.views.author_alias.send_discord", return_value=True):
            self.client.post(reverse("subekashi:author_unify_name_set", args=[self.author.id]), {"name": self.author.name})

        self.assertIn("名義は統一されています", self._status(self._get()))

    def test_no_status_when_no_past_alias_and_not_past_alias_of_others(self):
        author = Author.objects.create(name="別名なし作者")
        response = self._get(author)
        self.assertNotContains(response, "unify-name-status")
        self.assertNotContains(response, 'data-tutorial="unify-name"')

    def test_successor_status_shows_not_unified_when_author_has_songs(self):
        # この作者の名前を以前の名称として登録している作者（その後の名称）がいる場合、
        # この作者に曲が残っていればまだ統一されていない。統一は統一先の別名一覧で行う
        old_author = Author.objects.create(name="以前の名義")
        Song.objects.create(title="以前の名義の曲").authors.add(old_author)

        response = self._get(old_author)

        status = self._status(response, "unify-name-successor-status")
        self.assertIn("この作者の曲が1曲あり、名義が『現在の名義』に統一されていません", status)
        self.assertIn('class="unify-name-status info"', status)
        self.assertIn("fa-info-circle", status)
        self.assertIn(f'href="{reverse("subekashi:author_aliases", args=[self.author.id])}"', status)
        self.assertContains(response, 'data-tutorial="unify-name"')
        # この作者自身は以前の名称を持たないため、統一するフォームは表示しない
        self.assertNotContains(response, 'id="unify-name-form"')
        self.assertNotContains(response, 'id="unify-name-status"')

    def test_successor_status_shows_unified_when_author_has_no_songs(self):
        old_author = Author.objects.create(name="以前の名義")

        status = self._status(self._get(old_author), "unify-name-successor-status")

        self.assertIn("名義は『", status)
        self.assertIn("』に統一されています", status)
        self.assertIn('class="unify-name-status ok"', status)
        self.assertIn(f'href="{reverse("subekashi:author", args=[self.author.id])}"', status)

    def test_no_successor_status_for_non_past_reverse_alias(self):
        # 別名義（another）として登録されている作者は統一の対象外
        other = Author.objects.create(name="別名義の作者")
        AuthorAlias.objects.create(name=other.name, author=self.author, alias_type="another")
        Song.objects.create(title="別名義の作者の曲").authors.add(other)

        self.assertNotContains(self._get(other), "unify-name-successor-status")

    def test_successor_status_escapes_successor_name(self):
        successor = Author.objects.create(name="<b>その後の名義</b>")
        AuthorAlias.objects.create(name="エスケープ確認用の以前の名義", author=successor, alias_type="past")
        old_author = Author.objects.create(name="エスケープ確認用の以前の名義")

        response = self._get(old_author)

        self.assertContains(response, "&lt;b&gt;その後の名義&lt;/b&gt;")
        self.assertNotContains(response, "<b>その後の名義</b>")


@override_settings(STORAGES=STATIC_STORAGE)
class AuthorUnifyNameConfirmViewTest(TestCase):
    """AuthorUnifyNameConfirmView (/authors/<id>/aliases/unify/confirm) のテスト（#1029、#1137）

    統一により他のAuthorの曲が統一先へ移ることへの安全策として、
    実際の統一前に内容を確認できる画面を経由させるためのビュー。
    """
    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="現在の名義")
        self.past_alias = AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")

    def _get(self, name):
        return self.client.get(reverse("subekashi:author_unify_name_confirm", args=[self.author.id]), {"name": name})

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(
            reverse("subekashi:author_unify_name_confirm", args=[99999]), {"name": "以前の名義"}
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_name_redirects_with_error(self):
        response = self._get("全く関係ない名前")
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=unify_error"
        )

    def test_current_name_with_nothing_to_move_redirects_without_confirmation(self):
        response = self._get(self.author.name)
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=unify_noop"
        )

    def test_current_name_shows_songs_of_past_alias_author(self):
        # フォームを変更しない（現在の名義のまま）送信でも、以前の名称と同名の別Authorの曲を統一できる（#1137）
        past_author = Author.objects.create(name="以前の名義")
        Song.objects.create(title="以前の名義の曲").authors.add(past_author)

        response = self._get(self.author.name)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "以前の名義の曲")
        self.assertContains(response, "の作者が『現在の名義』に統一されます")
        self.assertContains(response, "作者『以前の名義』の曲は全て『現在の名義』に移動します")
        self.assertNotContains(response, f"（id={past_author.id}）")
        self.assertNotContains(response, "作者自体は削除されません")

    def test_past_alias_without_existing_author_does_not_mention_existing_target(self):
        response = self._get("以前の名義")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "既存の作者")
        self.assertNotContains(response, "に移動します")

    def test_existing_target_author_is_shown(self):
        target = Author.objects.create(name="以前の名義")
        response = self._get("以前の名義")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "既存の作者『以前の名義』が統一先となり、この作者の曲・別名・作者リンクは全てそちらに移動します")
        self.assertNotContains(response, f"（id={target.id}）")
        self.assertNotContains(response, "この作者自体は削除されません")

    def test_confirmation_page_does_not_modify_any_data(self):
        past_author = Author.objects.create(name="以前の名義")
        song = Song.objects.create(title="以前の名義の曲")
        song.authors.add(past_author)

        self._get("以前の名義")

        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertEqual(list(song.authors.all()), [past_author])
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())

    def test_no_songs_falls_back_to_plain_message(self):
        response = self._get("以前の名義")
        self.assertContains(response, "名義が『以前の名義』に統一されます")

    def test_shows_own_song_titles_when_renaming(self):
        song = Song.objects.create(title="変更対象の曲")
        song.authors.add(self.author)

        response = self._get("以前の名義")

        self.assertContains(response, "変更対象の曲")
        self.assertContains(response, "の作者が『以前の名義』に統一されます")

    def test_existing_target_lists_own_songs_but_not_targets_songs(self):
        # 統一先の既存Authorの曲は表示上の作者名が変わらないため一覧に含めない
        target = Author.objects.create(name="以前の名義")
        Song.objects.create(title="統一先の曲").authors.add(target)
        Song.objects.create(title="このauthorの曲").authors.add(self.author)

        response = self._get("以前の名義")

        self.assertContains(response, "このauthorの曲")
        self.assertNotContains(response, "統一先の曲")

    def test_song_shared_by_multiple_authors_is_not_listed_twice(self):
        # 同じ曲が統一対象の複数のAuthorの共著になっている場合、
        # 曲タイトルが確認画面に重複して表示されないことを確認する
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")
        shared_song = Song.objects.create(title="共著の曲")
        shared_song.authors.add(self.author, Author.objects.create(name="以前の名義2"))

        response = self._get("以前の名義")

        self.assertEqual(response.content.decode().count("共著の曲"), 1)

    def test_submit_button_is_labeled_unify(self):
        # 幅は共通の.action-buttonで「戻る」と揃うため、幅指定用のクラスは使わない（#450）
        response = self._get("以前の名義")
        self.assertContains(response, "統一する")
        self.assertContains(response, '<button type="submit" class="action-button black-action-button">')
        self.assertNotContains(response, "変更する")
        self.assertContains(response, f'action="{reverse("subekashi:author_unify_name_set", args=[self.author.id])}"')

    def test_show_all_songs_button_hidden_when_ten_or_fewer_songs(self):
        # ボタンのid文字列自体はno-opなJS（要素が無ければ何もしない）内にも常に
        # 出現するため、実際のbutton要素・li要素のクラス属性の有無で判定する
        for i in range(10):
            Song.objects.create(title=f"曲{i}").authors.add(self.author)

        response = self._get("以前の名義")

        self.assertNotContains(response, 'id="unify-name-show-all-songs"')
        self.assertNotContains(response, 'class="unify-name-song-hidden"')

    def test_show_all_songs_button_shown_and_hides_songs_past_ten(self):
        for i in range(11):
            Song.objects.create(title=f"曲{i}").authors.add(self.author)

        response = self._get("以前の名義")

        self.assertContains(response, 'id="unify-name-show-all-songs"')
        self.assertContains(response, "全て表示")
        self.assertEqual(response.content.decode().count('class="unify-name-song-hidden"'), 1)


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_author_name_with_slash_redirects(self):
        # #1127: 作者名に"/"が含まれていてもreverseでき、作者ページへリダイレクトされる
        author = Author.objects.create(name="スラッシュ/作者")
        url = reverse("subekashi:channel", args=["スラッシュ/作者"])

        response = self.client.get(url)

        self.assertRedirects(response, reverse("subekashi:author", args=[author.id]))


@override_settings(STORAGES=STATIC_STORAGE)
class ContactViewTest(TestCase):
    """ContactView (/contact/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:contact"))
        self.assertEqual(response.status_code, 200)

    def test_query_fills_form(self):
        # 曲の編集画面のリンク等から、種類と詳細を入力した状態で開く
        response = self.client.get(reverse("subekashi:contact"), {"category": "提案", "detail": "クエリの詳細テスト"})
        self.assertContains(response, '<option value="提案" selected>提案</option>')
        self.assertContains(response, "クエリの詳細テスト</textarea>")

    def test_undo_removal_category_is_not_shown(self):
        # 削除の取り消しは曲のページのボタンで行うため、種類「削除の取り消し」は無い（#1264）
        response = self.client.get(reverse("subekashi:contact"))
        self.assertNotContains(response, "削除の取り消し")

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


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_removed_song_history_shows_deleted_message(self):
        # ユーザーが削除した曲（#1239）のページは404になるため、リンクせずに削除されたと表示する
        editor = Editor.objects.create(ip="127.0.0.12")
        song = Song.objects.create(title="履歴一覧の削除した曲")
        History.create_for_song(
            song=song, title="履歴一覧の削除した曲を削除", history_type="delete", changes=["理由", "重複"], editor=editor,
        )
        song.is_removed = True
        song.save()

        response = self.client.get(reverse("subekashi:histories"))

        self.assertContains(response, "この曲または作者は削除されました")
        self.assertContains(response, "重複")
        self.assertNotContains(response, f'href="{reverse("subekashi:song", args=[song.id])}"')

    def test_search_input_has_aria_label(self):
        # 編集者のページと共通のコンポーネント（history_search_form.html）で、aria-labelを付ける（#954）
        response = self.client.get(reverse("subekashi:histories"))
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(soup.select_one('form input[name="q"]')["aria-label"], "編集履歴の概要で検索")

    def test_pagination_keeps_search_query(self):
        # 検索結果が複数ページのとき、前へ・次へのリンクで検索語を引き継ぐ（#954）
        editor = Editor.objects.create(ip="127.0.0.16")
        author = Author.objects.create(name="履歴一覧ページ送り作者")
        History.objects.bulk_create([
            History(author=author, title=f"別名を追加{i}", history_type="edit", editor=editor)
            for i in range(HISTORIES_PER_PAGE + 1)
        ])

        first = self.client.get(reverse("subekashi:histories"), {"q": "別名"})
        self.assertContains(first, f'href="?page=2&amp;q={quote("別名")}"', count=2)

        second = self.client.get(reverse("subekashi:histories"), {"q": "別名", "page": 2})
        self.assertContains(second, f'href="?page=1&amp;q={quote("別名")}"', count=2)

    def test_restore_history_links_to_song(self):
        # 削除を取り消した曲（#1264）の履歴は、曲へのリンクを表示する
        song = Song.objects.create(title="履歴一覧の取り消した曲")
        self.client.post(reverse("subekashi:song_delete", args=[song.id]), {"reason": "誤り"})
        self.client.post(reverse("subekashi:song_restore", args=[song.id]), {"reason": "誤って削除した"})

        response = self.client.get(reverse("subekashi:histories"))

        self.assertContains(response, "履歴一覧の取り消した曲の削除を取り消し")
        self.assertContains(response, f'href="{reverse("subekashi:song", args=[song.id])}"', count=2)
        self.assertNotContains(response, "この曲または作者は削除されました")


@override_settings(STORAGES=STATIC_STORAGE, RATELIMIT_ENABLE=False)
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

    def test_categorys_filter(self):
        """#423: categorysで指定したカテゴリの曲のみを表示し、カテゴリのフィルタが有効であることを表示すること"""
        Song.objects.create(title="アレンジのカード", category="arrange")
        Song.objects.create(title="音MADのカード", category="otomad")
        response = self.client.get(reverse("subekashi:song_cards"), {"categorys": "arrange,otomad"})
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("カテゴリが有効です", content)
        self.assertIn("3件中2件ヒットしました", content)
        self.assertIn("アレンジのカード", content)
        self.assertIn("音MADのカード", content)
        self.assertNotIn("カードテスト曲", content)

    def test_categorys_filter_excludes_category(self):
        """#423: categorysで先頭に~を付けたカテゴリの曲は表示しないこと"""
        Song.objects.create(title="アレンジのカード", category="arrange")
        response = self.client.get(reverse("subekashi:song_cards"), {"categorys": "~song"})
        content = "".join(response.json())
        self.assertIn("カテゴリが有効です", content)
        self.assertIn("2件中1件ヒットしました", content)
        self.assertIn("アレンジのカード", content)
        self.assertNotIn("カードテスト曲", content)

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

    def test_validation_error_message_is_escaped(self):
        """エラーメッセージに含まれる入力値がHTMLエスケープされること（#1126）"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"sort": "<img src=x onerror=alert(1)>"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("class='error'", content)
        self.assertNotIn("<img", content)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", content)

    def test_is_questionable_shows_active_filter(self):
        """is_questionable を指定したとき「界隈曲?が有効です」が含まれること"""
        for value in ["True", "False"]:
            with self.subTest(value=value):
                response = self.client.get(
                    reverse("subekashi:song_cards"), {"is_questionable": value}
                )
                self.assertEqual(response.status_code, 200)
                content = "".join(response.json())
                self.assertIn("界隈曲?が有効です", content)

    def test_is_special_shows_active_filter(self):
        """is_special を指定したとき「スペシャルデザインが有効です」が含まれること"""
        for value in ["True", "False"]:
            with self.subTest(value=value):
                response = self.client.get(
                    reverse("subekashi:song_cards"), {"is_special": value}
                )
                self.assertEqual(response.status_code, 200)
                content = "".join(response.json())
                self.assertIn("スペシャルデザインが有効です", content)

    def test_is_special_filters_song_cards(self):
        """is_special=True のときスペシャルデザインの曲のカードのみが返されること"""
        Song.objects.create(title="スペシャルデザインカードテスト", is_special=True)
        response = self.client.get(
            reverse("subekashi:song_cards"), {"is_special": "True"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("スペシャルデザインカードテスト", content)
        self.assertNotIn("カードテスト曲", content)

    def test_is_collab_shows_active_filter(self):
        """is_collab を指定したとき「合作が有効です」が含まれること"""
        for value in ["True", "False"]:
            with self.subTest(value=value):
                response = self.client.get(
                    reverse("subekashi:song_cards"), {"is_collab": value}
                )
                self.assertEqual(response.status_code, 200)
                content = "".join(response.json())
                self.assertIn("合作が有効です", content)

    def test_is_collab_filters_song_cards(self):
        """is_collab=True のとき合作の曲（作者が2人以上の曲）のカードのみが返されること"""
        song = Song.objects.create(title="合作カードテスト")
        song.authors.add(Author.objects.create(name="合作カード作者A"), Author.objects.create(name="合作カード作者B"))
        response = self.client.get(
            reverse("subekashi:song_cards"), {"is_collab": "True"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("合作カードテスト", content)
        self.assertNotIn("カードテスト曲", content)

    def test_imitate_shows_active_filter(self):
        """imitate を指定したとき「模倣元が有効です」が含まれること（#1241）"""
        original = Song.objects.create(title="模倣元カードテスト")
        response = self.client.get(
            reverse("subekashi:song_cards"), {"imitate": original.id}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("模倣元が有効です", content)


@override_settings(STORAGES=STATIC_STORAGE, RATELIMIT_ENABLE=False)
class SongGuessersViewTest(TestCase):
    """song_guessers (/api/html/song_guessers) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_validation_error_message_is_escaped(self):
        """エラーメッセージに含まれる入力値がHTMLエスケープされること（#1126）"""
        response = self.client.get(
            reverse("subekashi:song_guessers"), {"guesser": "曲", "sort": "<img src=x onerror=alert(1)>"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("class='error'", content)
        self.assertNotIn("<img", content)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", content)

    def test_guessers_are_sorted_by_imitated_count(self):
        """候補は模倣曲の数が多い順に表示され、同じ数の曲は登録日の遅い順になること（#1124）"""
        few = Song.objects.create(title="候補ソート模倣1曲")
        many = Song.objects.create(title="候補ソート模倣2曲")
        none_old = Song.objects.create(title="候補ソート模倣なし旧")
        none_new = Song.objects.create(title="候補ソート模倣なし新")
        imitator1 = Song.objects.create(title="模倣した曲1")
        imitator2 = Song.objects.create(title="模倣した曲2")
        imitator1.imitates.add(many, few)
        imitator2.imitates.add(many)
        response = self.client.get(reverse("subekashi:song_guessers"), {"guesser": "候補ソート"})
        self.assertEqual(response.status_code, 200)
        titles = re.findall(r'<i class="fas fa-music"></i> (.*?)</p>', "".join(response.json()))
        self.assertEqual(titles, [many.title, few.title, none_new.title, none_old.title])

    def test_message_by_count(self):
        """候補の数に応じて末尾のメッセージが変わること（50件を超える場合は条件を絞るよう案内する）"""
        for i in range(51):
            Song.objects.create(title=f"候補メッセージ多{i}")
        Song.objects.create(title="候補メッセージ少")
        cases = [
            ("候補メッセージ多", "これ以上の候補を表示する為には条件を絞ってください。"),
            ("候補メッセージ少", "これ以上の検索結果はありません。"),
            ("候補メッセージ該当なし", "検索結果はありません。"),
        ]
        for guesser, message in cases:
            with self.subTest(guesser=guesser):
                response = self.client.get(reverse("subekashi:song_guessers"), {"guesser": guesser})
                self.assertTrue(response.json()[-1].startswith(f"<p>{message}"))

    def test_sort_query_overrides_default_sort(self):
        """sortを指定した場合はその並び順で表示されること"""
        Song.objects.create(title="候補ソート指定B")
        Song.objects.create(title="候補ソート指定A")
        response = self.client.get(reverse("subekashi:song_guessers"), {"guesser": "候補ソート指定", "sort": "title"})
        titles = re.findall(r'<i class="fas fa-music"></i> (.*?)</p>', "".join(response.json()))
        self.assertEqual(titles, ["候補ソート指定A", "候補ソート指定B"])


@override_settings(STORAGES=STATIC_STORAGE)
@patch("django_ratelimit.core.time")
class SongCardsRateLimitTest(TestCase):
    """song_cards・song_guessers のレート制限のテスト（#1188）

    IPごとに毎秒2回までに制限する。PythonAnywhereではREMOTE_ADDRがロードバランサーのIPになり、全ユーザーが
    1つのIPとして数えられるため、settings.RATELIMIT_IP_META_KEYでX-Real-IP（無ければREMOTE_ADDR）を使う。
    テストクライアントのREMOTE_ADDRは常に同じため、X-Real-IPごとに数えられていることを確認できる。
    1秒の区切りをまたいでカウントがリセットされないよう、django_ratelimitの時刻を固定する。
    """

    URL_NAMES = ["subekashi:song_cards", "subekashi:song_guessers"]

    def setUp(self):
        cache.clear()

    def _get(self, url_name, **extra):
        return self.client.get(reverse(url_name), **extra)

    def assertLimited(self, response):
        self.assertEqual(response.status_code, 429)

    def test_third_request_in_a_second_is_limited(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        for url_name in self.URL_NAMES:
            with self.subTest(url_name=url_name):
                for _ in range(2):
                    self.assertEqual(self._get(url_name, HTTP_X_REAL_IP="203.0.113.1").status_code, 200)
                self.assertLimited(self._get(url_name, HTTP_X_REAL_IP="203.0.113.1"))

    def test_limit_is_per_x_real_ip(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        for url_name in self.URL_NAMES:
            with self.subTest(url_name=url_name):
                for _ in range(2):
                    self._get(url_name, HTTP_X_REAL_IP="203.0.113.1")
                self.assertEqual(self._get(url_name, HTTP_X_REAL_IP="203.0.113.2").status_code, 200)
                self.assertLimited(self._get(url_name, HTTP_X_REAL_IP="203.0.113.1"))

    def test_x_forwarded_for_does_not_bypass_limit(self, mock_time):
        # X-Forwarded-Forはクライアントが自由に付けられるため、値を変えても別々に数えない
        mock_time.time.return_value = 1_800_000_000
        for url_name in self.URL_NAMES:
            with self.subTest(url_name=url_name):
                for i in range(2):
                    self._get(url_name, HTTP_X_REAL_IP="203.0.113.1", HTTP_X_FORWARDED_FOR=f"198.51.100.{i}")
                self.assertLimited(
                    self._get(url_name, HTTP_X_REAL_IP="203.0.113.1", HTTP_X_FORWARDED_FOR="198.51.100.9")
                )

    def test_remote_addr_is_used_without_x_real_ip(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        for url_name in self.URL_NAMES:
            with self.subTest(url_name=url_name):
                for _ in range(2):
                    self._get(url_name, REMOTE_ADDR="198.51.100.1")
                self.assertEqual(self._get(url_name, REMOTE_ADDR="198.51.100.2").status_code, 200)
                self.assertLimited(self._get(url_name, REMOTE_ADDR="198.51.100.1"))

    def test_invalid_x_real_ip_uses_remote_addr(self, mock_time):
        # IPでないX-Real-IPで500にならず、REMOTE_ADDRで数える
        mock_time.time.return_value = 1_800_000_000
        for url_name in self.URL_NAMES:
            with self.subTest(url_name=url_name):
                for _ in range(2):
                    self.assertEqual(self._get(url_name, HTTP_X_REAL_IP="not-an-ip").status_code, 200)
                self.assertLimited(self._get(url_name))


@override_settings(STORAGES=STATIC_STORAGE)
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


class RobotsViewTest(TestCase):
    """robots (/robots.txt) のテスト"""

    def setUp(self):
        self.client = Client()

    def _get_disallows(self):
        response = self.client.get("/robots.txt")
        lines = response.content.decode().splitlines()
        return [line.split(":", 1)[1].strip() for line in lines if line.startswith("Disallow:")]

    def _is_disallowed(self, path):
        return any(re.match(re.escape(disallow).replace(r"\*", ".*"), path) for disallow in self._get_disallows())

    def test_returns_robots_txt(self):
        """/static/へリダイレクトせず、/robots.txtでrobots.txtの内容を返す（#1172）"""
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertContains(response, "User-agent: *")
        self.assertContains(response, "Sitemap: https://lyrics.imicomweb.com/static/subekashi/sitemap.xml")

    def test_disallow_values_are_paths(self):
        """Disallowの値は完全なURLではなく、/から始まるパスで書く（#1172）"""
        disallows = self._get_disallows()
        self.assertTrue(disallows)
        for disallow in disallows:
            self.assertTrue(disallow.startswith("/"), disallow)

    def test_disallow_matches_target_pages(self):
        """曲の編集・削除、編集者、設定のページは巡回を制限し、曲のページは制限しない（#1172）"""
        for path in [
            reverse("subekashi:song_edit", args=[1]),
            reverse("subekashi:song_delete", args=[1]),
            reverse("subekashi:editor", args=[1]),
            reverse("subekashi:setting"),
        ]:
            self.assertTrue(self._is_disallowed(path), path)

        for path in [
            reverse("subekashi:top"),
            reverse("subekashi:songs"),
            reverse("subekashi:song", args=[1]),
            reverse("subekashi:song_history", args=[1]),
        ]:
            self.assertFalse(self._is_disallowed(path), path)


def assert_song_removed_page(test, response):
    # ユーザーが削除した曲（#1239）は404ではなく、曲名と削除を取り消すボタンのあるページを表示する（#1264）
    test.assertEqual(response.status_code, 410)
    test.assertTemplateUsed(response, "subekashi/song_removed.html")
    test.assertContains(response, "のページは削除されました", status_code=410)


@contextmanager
def manifest_static_storage(paths):
    # 本番と同じManifestStaticFilesStorageにし、pathsをハッシュ付きのファイル名としてmanifestに持たせる
    with tempfile.TemporaryDirectory() as static_root:
        with open(os.path.join(static_root, "staticfiles.json"), "w", encoding="utf-8") as f:
            json.dump({"version": "1.1", "paths": paths}, f)
        with override_settings(STATIC_ROOT=static_root, STORAGES=MANIFEST_STORAGE):
            yield


class SitemapViewTest(TestCase):
    """sitemap (/sitemap.xml) のテスト"""

    def test_redirects_to_unhashed_sitemap(self):
        """sitemap.xmlは起動中に再生成されるため、manifestにハッシュ付きのファイル名があってもハッシュなしのURLへリダイレクトする（#834）"""
        with manifest_static_storage({"subekashi/sitemap.xml": "subekashi/sitemap.0123456789ab.xml"}):
            response = self.client.get("/sitemap.xml")
        self.assertRedirects(response, f"{settings.ROOT_URL}/static/subekashi/sitemap.xml", fetch_redirect_response=False)


@override_settings(STORAGES=STATIC_STORAGE)
class FaviconTest(TestCase):
    """faviconとweb app manifestのテスト（#1171）"""

    def setUp(self):
        self.client = Client()

    def test_favicon_redirects_to_ico(self):
        response = self.client.get("/favicon.ico")
        self.assertRedirects(response, "/static/subekashi/image/favicon.ico", fetch_redirect_response=False)

    def test_favicon_redirects_to_hashed_ico_in_production(self):
        """本番のManifestStaticFilesStorageでは、base.htmlの<link rel="icon">と同じハッシュ付きのURLへリダイレクトする（#834）"""
        with manifest_static_storage({"subekashi/image/favicon.ico": "subekashi/image/favicon.0123456789ab.ico"}):
            response = self.client.get("/favicon.ico")
        self.assertRedirects(response, "/static/subekashi/image/favicon.0123456789ab.ico", fetch_redirect_response=False)

    def test_favicon_ico_has_sizes(self):
        with Image.open(finders.find("subekashi/image/favicon.ico")) as ico:
            self.assertEqual(ico.ico.sizes(), {(16, 16), (32, 32), (48, 48)})

    def test_apple_touch_icon_size(self):
        with Image.open(finders.find("subekashi/image/apple-touch-icon.png")) as image:
            self.assertEqual(image.size, (180, 180))

    def test_base_html_links(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<link rel="icon" href="/static/subekashi/image/favicon.ico" sizes="16x16 32x32 48x48">')
        self.assertContains(response, '<link rel="apple-touch-icon" href="/static/subekashi/image/apple-touch-icon.png" sizes="180x180">')
        self.assertContains(response, '<link rel="manifest" href="/static/subekashi/site.webmanifest">')
        self.assertNotContains(response, "shortcut icon")

    def test_manifest(self):
        with open(finders.find("subekashi/site.webmanifest"), encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertEqual(manifest["name"], "全て歌詞の所為です。")
        self.assertEqual(manifest["short_name"], "すべかし")
        self.assertEqual(manifest["theme_color"], "#000000")
        self.assertEqual(manifest["background_color"], "#111111")
        self.assertEqual([icon["sizes"] for icon in manifest["icons"]], ["192x192", "512x512"])

    def test_manifest_icons_exist_with_declared_size(self):
        # iconsのsrcはmanifestのURL（/static/subekashi/）からの相対パス
        with open(finders.find("subekashi/site.webmanifest"), encoding="utf-8") as f:
            manifest = json.load(f)

        for icon in manifest["icons"]:
            with self.subTest(src=icon["src"]):
                path = finders.find(f"subekashi/{icon['src']}")
                self.assertIsNotNone(path)
                with Image.open(path) as image:
                    self.assertEqual(f"{image.width}x{image.height}", icon["sizes"])
                    self.assertEqual(Image.MIME[image.format], icon["type"])


@override_settings(STORAGES=STATIC_STORAGE)
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


@override_settings(STORAGES=STATIC_STORAGE)
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


@override_settings(STORAGES=STATIC_STORAGE)
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


@override_settings(STORAGES=STATIC_STORAGE)
class SettingViewTest(TestCase):
    """SettingView (/setting/) のテスト"""

    def setUp(self):
        self.client = Client()

    def _get_form_button_options(self, response):
        setting = next(setting for setting in response.context["settings"]["search"] if setting["id"] == "form_button")
        return [(option["value"], option["text"], option["selected"]) for option in setting["options"]]

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:setting"))
        self.assertEqual(response.status_code, 200)

    def test_form_button_defaults_to_icon_and_text(self):
        """検索画面のフォームボタンの設定は、cookieが無い場合「アイコンと文字」が選択される（#1164）"""
        response = self.client.get(reverse("subekashi:setting"))

        self.assertContains(response, '<label>フォームボタン</label>')
        self.assertContains(response, '<select id="form_button" class="setting-input">')
        self.assertEqual(self._get_form_button_options(response), [
            ("icon", "アイコンのみ", False),
            ("icon_text", "アイコンと文字", True),
        ])

    def test_form_button_reflects_cookie(self):
        """検索画面のフォームボタンの設定は、cookieの値が選択される（#1164）"""
        self.client.cookies["form_button"] = "icon"
        response = self.client.get(reverse("subekashi:setting"))

        self.assertEqual(self._get_form_button_options(response), [
            ("icon", "アイコンのみ", True),
            ("icon_text", "アイコンと文字", False),
        ])

    def _get_font_options(self, response):
        setting = next(setting for setting in response.context["settings"]["display"] if setting["id"] == "font")
        return [(option["value"], option["text"], option["selected"]) for option in setting["options"]]

    def test_font_defaults_to_imitate(self):
        """表示設定のフォントは「源全ゴシック」「k8x12S」から選べ、cookieが無い場合は「源全ゴシック」が選択される（#584）"""
        response = self.client.get(reverse("subekashi:setting"))

        self.assertContains(response, '<label>フォント</label>')
        self.assertContains(response, '<select id="font" class="setting-input">')
        self.assertEqual(self._get_font_options(response), [
            ("imitate", "源全ゴシック", True),
            ("k8x12s", "k8x12S", False),
        ])

    def test_font_reflects_cookie(self):
        """表示設定のフォントは、cookieの値が選択される。不正な値は「源全ゴシック」が選択される（#584）"""
        expected = {
            "imitate": [("imitate", "源全ゴシック", True), ("k8x12s", "k8x12S", False)],
            "k8x12s": [("imitate", "源全ゴシック", False), ("k8x12s", "k8x12S", True)],
            "<script>": [("imitate", "源全ゴシック", True), ("k8x12s", "k8x12S", False)],
        }
        for value, options in expected.items():
            with self.subTest(value=value):
                self.client.cookies["font"] = value
                response = self.client.get(reverse("subekashi:setting"))

                self.assertEqual(self._get_font_options(response), options)

    def _get_search_display_options(self, response):
        setting = next(setting for setting in response.context["settings"]["top"] if setting["id"] == "is_shown_search")
        return [(option["value"], option["text"], option["selected"]) for option in setting["options"]]

    def test_search_display_defaults_to_keyword_only(self):
        """トップ画面の検索の表示の設定は「全て表示」「キーワードのみ」「非表示」から選べ、cookieが無い場合は「キーワードのみ」が選択される（#585）"""
        response = self.client.get(reverse("subekashi:setting"))

        self.assertContains(response, '<select id="is_shown_search" class="setting-input">')
        self.assertEqual(self._get_search_display_options(response), [
            ("all", "全て表示", False),
            ("on", "キーワードのみ", True),
            ("off", "非表示", False),
        ])

    def test_search_display_reflects_cookie(self):
        """トップ画面の検索の表示の設定は、cookieの値が選択される。以前の「表示」(on)は「キーワードのみ」になる（#585）"""
        cases = [("all", "全て表示"), ("on", "キーワードのみ"), ("off", "非表示")]
        for value, text in cases:
            with self.subTest(value=value):
                self.client.cookies["is_shown_search"] = value
                response = self.client.get(reverse("subekashi:setting"))

                selected = [option_text for _, option_text, is_selected in self._get_search_display_options(response) if is_selected]
                self.assertEqual(selected, [text])

    def _get_upcoming_options(self, response):
        setting = next(setting for setting in response.context["settings"]["top"] if setting["id"] == "is_shown_upcoming")
        return [(option["value"], option["text"], option["selected"]) for option in setting["options"]]

    def test_upcoming_display_defaults_to_five(self):
        """トップ画面の投稿予定の表示の設定は、新着の表示の次に並び、cookieが無い場合は「5曲表示」が選択される（#376）"""
        response = self.client.get(reverse("subekashi:setting"))

        self.assertContains(response, '<label>投稿予定の表示</label>')
        self.assertContains(response, '<select id="is_shown_upcoming" class="setting-input">')
        self.assertEqual(self._get_upcoming_options(response), [
            ("15", "15曲表示", False),
            ("10", "10曲表示", False),
            ("5", "5曲表示", True),
            ("0", "非表示", False),
        ])
        top_ids = [setting["id"] for setting in response.context["settings"]["top"]]
        self.assertEqual(top_ids.index("is_shown_upcoming"), top_ids.index("is_shown_new") + 1)

    def test_upcoming_display_reflects_cookie(self):
        """トップ画面の投稿予定の表示の設定は、cookieの値が選択される（#376）"""
        cases = [("15", "15曲表示"), ("10", "10曲表示"), ("5", "5曲表示"), ("0", "非表示")]
        for value, text in cases:
            with self.subTest(value=value):
                self.client.cookies["is_shown_upcoming"] = value
                response = self.client.get(reverse("subekashi:setting"))

                selected = [option_text for _, option_text, is_selected in self._get_upcoming_options(response) if is_selected]
                self.assertEqual(selected, [text])

    def _get_guide_display_options(self, response):
        setting = next(setting for setting in response.context["settings"]["top"] if setting["id"] == "is_shown_guide")
        return [(option["value"], option["text"], option["selected"]) for option in setting["options"]]

    def test_guide_display_defaults_to_shown(self):
        """トップ画面の初心者向け案内の表示の設定は、ネタ曲の表示の次に置き、cookieが無い場合は「表示」が選択される（#1236）"""
        response = self.client.get(reverse("subekashi:setting"))
        setting_ids = [setting["id"] for setting in response.context["settings"]["top"]]

        self.assertContains(response, '<label>初心者向け案内の表示</label>')
        self.assertContains(response, '<select id="is_shown_guide" class="setting-input">')
        self.assertEqual(setting_ids.index("is_shown_guide"), setting_ids.index("jokerange") + 1)
        self.assertEqual(self._get_guide_display_options(response), [
            ("on", "表示", True),
            ("off", "非表示", False),
        ])

    def test_guide_display_reflects_cookie(self):
        """トップ画面の初心者向け案内の表示の設定は、cookieの値が選択され、off以外の値は「表示」になる（#1236）"""
        cases = [("off", "非表示"), ("on", "表示"), ("<script>", "表示")]
        for value, text in cases:
            with self.subTest(value=value):
                self.client.cookies["is_shown_guide"] = value
                response = self.client.get(reverse("subekashi:setting"))

                selected = [option_text for _, option_text, is_selected in self._get_guide_display_options(response) if is_selected]
                self.assertEqual(selected, [text])

    def test_tutorial_icon_is_shown_only_for_saved_select(self):
        """検索画面のセクションで、選択肢の保存のチュートリアルのアイコンは「検索の選択肢の保存」にのみ付く（#1164）"""
        response = self.client.get(reverse("subekashi:setting"))

        self.assertContains(response, '<label>検索の選択肢の保存<i class="fas fa-info-circle" data-tutorial="select"></i></label>')
        self.assertContains(response, 'data-tutorial="select"', count=1)

    def test_google_preferred_source_link(self):
        """Google検索のセクションに、当サイトをGoogleの優先するソースに追加するページへのリンクが新しいタブで開くように表示される（#1151）"""
        response = self.client.get(reverse("subekashi:setting"))

        self.assertContains(response, '<h2>Google検索</h2>')
        self.assertContains(response, '<a href="https://www.google.com/preferences/source?q=lyrics.imicomweb.com" target="_blank" rel="noopener noreferrer" class="action-button black-action-button">')


@override_settings(STORAGES=STATIC_STORAGE)
class SaveSettingsViewTest(TestCase):
    """SaveSettingsView (/api/setting/save/) のテスト"""

    def setUp(self):
        self.client = Client()

    def _post(self, cookies):
        return self.client.post(
            reverse("subekashi:save_settings"),
            data=json.dumps({"cookies": cookies}),
            content_type="application/json",
        )

    def test_form_button_is_saved(self):
        """検索画面のフォームボタンの設定はcookieに保存される（#1164）"""
        for value in ["icon", "icon_text"]:
            with self.subTest(value=value):
                response = self._post({"form_button": value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.cookies["form_button"].value, value)

    def test_form_button_with_invalid_value_is_not_saved(self):
        """検索画面のフォームボタンの設定に許可されていない値を送信しても、cookieには保存されない（#1164）"""
        for value in ["text", "<script>"]:
            with self.subTest(value=value):
                response = self._post({"form_button": value})

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("form_button", response.cookies)

    def test_saved_form_button_is_applied_to_songs(self):
        """設定画面で保存したフォームボタンの設定は、検索画面のフォームを切り替えるラジオボタンに反映される（#1164）"""
        self._post({"form_button": "icon"})
        response = self.client.get(reverse("subekashi:songs"))

        self.assertContains(response, '<div class="radio-group icon-only" id="search-form-radios">')

        self._post({"form_button": "icon_text"})
        response = self.client.get(reverse("subekashi:songs"))

        self.assertContains(response, '<div class="radio-group" id="search-form-radios">')

    def test_is_shown_search_is_saved(self):
        """トップ画面の検索の表示の設定はcookieに保存される（#585）"""
        for value in ["all", "on", "off"]:
            with self.subTest(value=value):
                response = self._post({"is_shown_search": value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.cookies["is_shown_search"].value, value)

    def test_is_shown_search_with_invalid_value_is_not_saved(self):
        """トップ画面の検索の表示の設定に許可されていない値を送信しても、cookieには保存されない（#585）"""
        for value in ["keyword", "<script>"]:
            with self.subTest(value=value):
                response = self._post({"is_shown_search": value})

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("is_shown_search", response.cookies)

    def test_saved_is_shown_search_is_applied_to_top(self):
        """設定画面で保存した検索の表示の設定が、トップ画面の検索フォームに反映される（#585）"""
        self._post({"is_shown_search": "all"})
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, 'id="search-form-radios"')

        self._post({"is_shown_search": "on"})
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, 'id="keyword"')
        self.assertNotContains(response, 'id="search-form-radios"')

        self._post({"is_shown_search": "off"})
        response = self.client.get(reverse("subekashi:top"))
        self.assertNotContains(response, 'id="search-form"')

    def test_is_shown_guide_is_saved(self):
        """トップ画面の初心者向け案内の表示の設定はcookieに保存され、許可されていない値は保存されない（#1236）"""
        for value in ["on", "off"]:
            with self.subTest(value=value):
                response = self._post({"is_shown_guide": value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.cookies["is_shown_guide"].value, value)

        for value in ["hidden", "<script>"]:
            with self.subTest(value=value):
                response = self._post({"is_shown_guide": value})

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("is_shown_guide", response.cookies)

    def test_saved_is_shown_guide_is_applied_to_top(self):
        """設定画面で保存した初心者向け案内の表示の設定が、トップ画面に反映される。閉じた案内を設定画面から再び表示できる（#1236）"""
        self._post({"is_shown_guide": "off"})
        response = self.client.get(reverse("subekashi:top"))
        self.assertNotContains(response, 'id="guide"')

        self._post({"is_shown_guide": "on"})
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, 'id="guide"')

    def test_font_is_saved(self):
        """表示設定のフォントはcookieに保存され、許可されていない値は保存されない（#584）"""
        for value in ["imitate", "k8x12s"]:
            with self.subTest(value=value):
                response = self._post({"font": value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.cookies["font"].value, value)

        for value in ["k8x12", "<script>"]:
            with self.subTest(value=value):
                response = self._post({"font": value})

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("font", response.cookies)

    def test_saved_font_is_applied_to_html(self):
        """設定画面で保存したフォントは、全てのページの<html>のdata-fontに反映される。cookieが無い場合や不正な値は源全ゴシック（imitate）になる（#584）"""
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<html lang="ja" data-font="imitate">')

        response = self._post({"font": "k8x12s"})
        self.client.cookies["font"] = response.cookies["font"].value
        for name in ["subekashi:top", "subekashi:songs", "subekashi:setting"]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, '<html lang="ja" data-font="k8x12s">')

        self.client.cookies["font"] = '"><script>alert(1)</script>'
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<html lang="ja" data-font="imitate">')
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_header_logo_follows_font_setting(self):
        """ヘッダーのロゴの文言は、設定したフォントに合わせるため、フォントを固定せずmainfontクラスで表示する（#584）"""
        response = self.client.get(reverse("subekashi:top"))

        self.assertContains(response, 'class="mainfont">全て歌詞の所為です。</a>')
        self.assertNotContains(response, "imitatefont")

    def test_is_shown_upcoming_is_saved(self):
        """トップ画面の投稿予定の表示の設定はcookieに保存される（#376）"""
        for value in ["0", "5", "10", "15"]:
            with self.subTest(value=value):
                response = self._post({"is_shown_upcoming": value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.cookies["is_shown_upcoming"].value, value)

    def test_is_shown_upcoming_with_invalid_value_is_not_saved(self):
        """トップ画面の投稿予定の表示の設定に許可されていない値を送信しても、cookieには保存されない（#376）"""
        for value in ["3", "on", "<script>"]:
            with self.subTest(value=value):
                response = self._post({"is_shown_upcoming": value})

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("is_shown_upcoming", response.cookies)


@override_settings(STORAGES=STATIC_STORAGE, RATELIMIT_ENABLE=False)
class UpcomingSongsFlowTest(TestCase):
    """トップ画面の投稿予定から検索画面への遷移のフロー（#376）"""

    def setUp(self):
        self.client = Client()
        today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        self.yesterday_song = self._create_song("昨日の投稿", today_start - timedelta(days=1))
        self.today_song = self._create_song("今日の投稿", today_start)
        self.later_song = self._create_song("明後日の投稿予定", today_start + timedelta(days=2))
        self.sooner_song = self._create_song("明日の投稿予定", today_start + timedelta(days=1))

    def _create_song(self, title, upload_time):
        song = Song.objects.create(title=title, upload_time=upload_time)
        link = SongLink.objects.create(url=f"https://youtu.be/{song.id:011d}")
        link.songs.add(song)
        return song

    def _get_titles(self, cards):
        return re.findall(r'title="([^"]+)"><i class="fas fa-music">', "".join(cards))

    def test_more_link_searches_upcoming_songs_without_saving_sort(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertEqual(list(response.context["upcomingInsL"]), [self.sooner_song, self.later_song])
        more_url = re.search(r'<a href="(/songs/\?upload_time_gte=[^"]+)"', response.content.decode()).group(1)

        # 検索画面では、投稿日/以降に今日の日付が入り、投稿日/早い順が選択されるが、保存した並び替えは変わらない
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_sort"] = "-view"
        response = self.client.get(more_url)
        today = timezone.localdate().isoformat()
        self.assertEqual(response.context["form_values"]["upload_time_gte"], today)
        self.assertEqual(response.context["sort"], "upload_time")
        self.assertNotIn("search_sort", response.cookies)

        # 検索画面のフォームの値（songs.jsのformToQuery）で検索すると、今日以降に投稿（予定）の曲が投稿日の早い順に表示される
        response = self.client.get(reverse("subekashi:song_cards"), {"upload_time_gte": today, "sort": "upload_time", "is_limited": "False"})
        self.assertEqual(self._get_titles(response.json()), ["今日の投稿", "明日の投稿予定", "明後日の投稿予定"])

        # 検索画面をもう一度開くと、保存した並び替えが選択される
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(response.context["sort"], "-view")


@override_settings(STORAGES=STATIC_STORAGE)
class ActionButtonMarkupTest(TestCase):
    """action-buttonの要素のテスト（#450）

    divで作っていたdummybuttonをaction-buttonに改名し、画面遷移はhref付きの<a class="action-button">、
    JSで処理するボタンは<button type="button" class="action-button">で実装する。ボタンの文言はspanにする。
    """

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="action-buttonテスト作者")
        self.song = Song.objects.create(title="action-buttonテスト曲")
        self.song.authors.add(self.author)
        self.alias = AuthorAlias.objects.create(name="action-buttonテスト別名", author=self.author, alias_type="past")
        self.editor = Editor.objects.create(ip="127.0.0.5", is_open=True)

    def _get_pages(self):
        pages = [
            (reverse("subekashi:top"), {}),
            (reverse("subekashi:song", args=[self.song.id]), {}),
            (reverse("subekashi:song_history", args=[self.song.id]), {}),
            (reverse("subekashi:song_edit", args=[self.song.id]), {"toast": "new"}),
            (reverse("subekashi:histories"), {}),
            (reverse("subekashi:editor", args=[self.editor.id]), {}),
            (reverse("subekashi:author", args=[self.author.id]), {}),
            (reverse("subekashi:author_aliases", args=[self.author.id]), {}),
            (reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]), {}),
            (reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id]), {}),
            (reverse("subekashi:author_unify_name_confirm", args=[self.author.id]), {"name": self.alias.name}),
            (reverse("subekashi:ai_result"), {}),
        ]
        for url, params in pages:
            response = self.client.get(url, params)
            self.assertEqual(response.status_code, 200)
            yield url, response.content.decode()

    def _find_buttons(self, content):
        return re.findall(
            r'<(?:a href="[^"]*"|button type="(?:button|submit)"[^>]*) class="action-button[^"]*">(.*?)</(?:a|button)>',
            content,
        )

    def test_action_button_is_not_div(self):
        for url, content in self._get_pages():
            with self.subTest(url=url):
                self.assertTrue(self._find_buttons(content))
                self.assertNotRegex(content, r'<div class="action-button[ "]')
                self.assertNotIn("dummybutton", content)

    def test_action_button_label_is_span(self):
        # buttonの中にpは入れられない（HTMLの仕様違反）ため、aも含めて文言はspanに統一する
        for url, content in self._get_pages():
            with self.subTest(url=url):
                for inner in self._find_buttons(content):
                    self.assertRegex(inner, r'<span[^>]*>[^<]+</span>$')
                    self.assertNotIn("<p", inner)

    def test_link_action_button_is_a_with_href(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        edit_url = reverse("subekashi:song_edit", args=[self.song.id])
        history_url = reverse("subekashi:song_history", args=[self.song.id])
        self.assertContains(response, f'<a href="{edit_url}" class="action-button">')
        self.assertContains(response, f'<a href="{history_url}" class="action-button">')

    def test_black_link_action_button_is_a_with_href(self):
        response = self.client.get(reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id]))
        aliases_url = reverse("subekashi:author_aliases", args=[self.author.id])
        self.assertContains(response, f'<a href="{aliases_url}" class="action-button black-action-button">')

    def test_history_action_buttons_are_button(self):
        for url in [
            reverse("subekashi:histories"),
            reverse("subekashi:editor", args=[self.editor.id]),
            reverse("subekashi:song_history", args=[self.song.id]),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '<button type="button" id="history-reload" class="action-button">')
                self.assertContains(response, '<button type="button" id="history-open-all" class="action-button">')

    def test_alias_reload_button_is_button(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, '<button type="button" id="alias-reload" class="action-button black-action-button">')

    def test_ai_result_buttons_are_button(self):
        response = self.client.get(reverse("subekashi:ai_result"))
        self.assertContains(response, '<button type="button" id="copy" class="action-button">')
        self.assertContains(response, '<button type="button" id="regenerate" class="action-button">')

    @patch("subekashi.middleware.maintenance._load_maintenance", return_value={"IS_MAINTENANCE": True})
    def test_maintenance_reload_button_is_button(self, _):
        response = self.client.get(reverse("subekashi:ai_result"))
        self.assertTemplateUsed(response, "subekashi/maintenance.html")
        self.assertContains(response, '<button type="button" id="maintenance-reload" class="action-button"><i class="fas fa-redo"></i><span>再読み込み</span></button>')


@override_settings(STORAGES=STATIC_STORAGE, RATELIMIT_ENABLE=False)
class OgpMetaTagTest(TestCase):
    """OGPのメタタグのテスト（#1058）"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="OGPテスト曲")

    def _get_og_image_url(self, response):
        match = re.search(r'<meta property="og:image" content="([^"]+)">', response.content.decode())
        self.assertIsNotNone(match)
        return match.group(1)

    def _get_og_image_title(self, response):
        match = re.fullmatch(
            rf"{re.escape(settings.ROOT_URL)}/ogp/([^/]+)\.png\?v={OGP_VERSION}",
            self._get_og_image_url(response),
        )
        self.assertIsNotNone(match)
        return load_ogp_token(match.group(1))

    def test_og_tags_use_property_attribute(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<meta property="og:type" content="website">')
        self.assertNotContains(response, 'name="og:')

    def test_og_image_is_page_ogp_image_url(self):
        # URLの末尾に画像のバージョン（?v=）が付く
        response = self.client.get(reverse("subekashi:top"))
        self.assertEqual(self._get_og_image_title(response), "トップ")

    def test_twitter_image_is_same_as_og_image(self):
        response = self.client.get(reverse("subekashi:top"))
        og_image_url = self._get_og_image_url(response)
        self.assertContains(response, f'<meta name="twitter:image" content="{og_image_url}">')

    def test_og_image_title_is_each_page_metatitle(self):
        editor = Editor.objects.create(ip="127.0.0.9")
        self.song.authors.add(Author.objects.create(name="OGPテスト作者"))
        for url, title in [
            (reverse("subekashi:song", args=[self.song.id]), "OGPテスト曲 / OGPテスト作者"),
            (reverse("subekashi:stats"), "統計"),
            # EditorViewはmetatitleにEditorのインスタンスを渡している
            (reverse("subekashi:editor", args=[editor.id]), f"全て{editor.id}の所為です。"),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(self._get_og_image_title(response), title)

    def test_og_image_url_returns_png(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        og_image_path = self._get_og_image_url(response).removeprefix(settings.ROOT_URL)

        image_response = self.client.get(og_image_path)

        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response["Content-Type"], "image/png")

    def test_404_page_has_no_ogp_tags(self):
        # SongViewが表示する404.htmlと、存在しないURLでhandler404が表示する404.html
        for url in ["/songs/999999999/", "/no-such-page/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertNotContains(response, 'property="og:', status_code=404)
                self.assertNotContains(response, 'name="twitter:', status_code=404)
                self.assertContains(response, '<meta name="description"', status_code=404)

    def test_500_page_has_no_ogp_tags(self):
        html = render_to_string("subekashi/500.html", {"metatitle": "全て五百の所為です。"}, request=RequestFactory().get("/"))
        self.assertNotIn('property="og:', html)
        self.assertNotIn('name="twitter:', html)

    @override_settings(ROOT_URL="https://example.com")
    def test_og_url_uses_root_url_setting(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<meta property="og:url" content="https://example.com/">')

    def test_static_og_image_file_exists(self):
        self.assertIsNotNone(finders.find("subekashi/image/ogp.png"))

    def test_og_image_size_and_alt(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<meta property="og:image:width" content="1200">')
        self.assertContains(response, '<meta property="og:image:height" content="630">')
        self.assertContains(response, '<meta property="og:image:alt" content="トップ | 全て歌詞の所為です。">')

    def test_twitter_card_is_summary_large_image(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<meta name="twitter:card" content="summary_large_image">')

    def test_site_name_and_locale(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<meta property="og:site_name" content="全て歌詞の所為です。">')
        self.assertContains(response, '<meta property="og:locale" content="ja_JP">')

    def test_og_url_is_each_page_url(self):
        for url in [
            reverse("subekashi:top"),
            reverse("subekashi:songs"),
            reverse("subekashi:song", args=[self.song.id]),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, f'<meta property="og:url" content="{settings.ROOT_URL}{url}">')

    def test_og_url_excludes_query_string(self):
        response = self.client.get(reverse("subekashi:songs"), {"keyword": "OGP"})
        self.assertContains(response, f'<meta property="og:url" content="{settings.ROOT_URL}/songs/">')

    def test_og_title_and_description(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertContains(response, '<meta property="og:title" content="トップ | 全て歌詞の所為です。">')
        self.assertContains(response, '<meta property="og:description" content="全て歌詞の所為です。は界隈曲をまとめたサイトです。">')


@override_settings(STORAGES=STATIC_STORAGE, RATELIMIT_ENABLE=False)
class OgpImageViewTest(TestCase):
    """ogp_image (/ogp/<token>.png) のテスト（#1058）"""

    def setUp(self):
        cache.clear()
        self.url = reverse("subekashi:ogp_image", args=[make_ogp_token("トップ")])

    def test_returns_1200x630_png(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(Image.open(io.BytesIO(response.content)).size, (1200, 630))

    def test_cache_control_is_long_term(self):
        response = self.client.get(self.url)
        self.assertEqual(response["Cache-Control"], f"public, max-age={LONG_TERM_COOKIE_AGE}")

    def test_version_query_is_accepted(self):
        response = self.client.get(self.url, {"v": OGP_VERSION})
        self.assertEqual(response.status_code, 200)

    def test_rendered_image_is_cached(self):
        with patch("subekashi.views.ogp.render_ogp_image", wraps=render_ogp_image) as render:
            first = self.client.get(self.url)
            second = self.client.get(self.url)

        self.assertEqual(render.call_count, 1)
        self.assertEqual(first.content, second.content)

    def test_if_none_match_returns_304(self):
        image_etag = self.client.get(self.url)["ETag"]

        with patch("subekashi.views.ogp.render_ogp_image") as render:
            response = self.client.get(self.url, HTTP_IF_NONE_MATCH=image_etag)

        self.assertEqual(response.status_code, 304)
        self.assertEqual(response["ETag"], image_etag)
        self.assertEqual(response["Cache-Control"], f"public, max-age={LONG_TERM_COOKIE_AGE}")
        render.assert_not_called()

    def test_etag_differs_by_title(self):
        other_url = reverse("subekashi:ogp_image", args=[make_ogp_token("統計")])
        self.assertNotEqual(self.client.get(self.url)["ETag"], self.client.get(other_url)["ETag"])

    def test_returns_static_image_when_font_cannot_be_loaded(self):
        with patch("subekashi.lib.ogp.get_font", side_effect=OSError("unknown file format")):
            response = self.client.get(self.url)

        with open(finders.find("subekashi/image/ogp.png"), "rb") as f:
            self.assertEqual(response.content, f.read())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Cache-Control"], f"public, max-age={SHORT_TERM_COOKIE_AGE}")
        self.assertFalse(response.has_header("ETag"))

        # 共通の画像はキャッシュしないため、フォントを読めるようになれば次のリクエストで生成される
        self.assertNotEqual(self.client.get(self.url).content, response.content)

    def test_empty_title_returns_404(self):
        token = signing.dumps("", salt=OGP_SALT, compress=True)
        response = self.client.get(f"/ogp/{token}.png")
        self.assertEqual(response.status_code, 404)

    def test_invalid_token_returns_404(self):
        response = self.client.get("/ogp/invalid-token.png")
        self.assertEqual(response.status_code, 404)

    def test_token_with_other_salt_returns_404(self):
        # 署名の鍵が同じでもsaltが異なるトークン（他の用途で作られたもの）は受け付けない
        token = signing.dumps("トップ", compress=True)
        response = self.client.get(f"/ogp/{token}.png")
        self.assertEqual(response.status_code, 404)


@override_settings(STORAGES=STATIC_STORAGE)
@patch("django_ratelimit.core.time")
class OgpImageRateLimitTest(TestCase):
    """ogp_image (/ogp/<token>.png) のレート制限のテスト（#1058）

    新しく描画するときだけ、X-Real-IPごとに毎秒5回までに制限する（キャッシュ済みの画像は数えない）。
    PythonAnywhereではREMOTE_ADDRがロードバランサーのIPになるため、X-Real-IPを使う。
    1秒の区切りをまたいでカウントがリセットされないよう、django_ratelimitの時刻を固定する。
    """

    def setUp(self):
        cache.clear()
        self.urls = [reverse("subekashi:ogp_image", args=[make_ogp_token(f"曲{i}")]) for i in range(7)]

    def _get(self, url, ip):
        return self.client.get(url, HTTP_X_REAL_IP=ip)

    def test_sixth_new_image_in_a_second_returns_429(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        for url in self.urls[:5]:
            self.assertEqual(self._get(url, "203.0.113.1").status_code, 200)

        response = self._get(self.urls[5], "203.0.113.1")

        # SNSのクローラーに失敗をキャッシュされないよう、キャッシュさせない
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "1")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_cached_image_is_not_limited(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        for url in self.urls[:5]:
            self._get(url, "203.0.113.1")
        self.assertEqual(self._get(self.urls[5], "203.0.113.1").status_code, 429)
        self.assertEqual(self._get(self.urls[0], "203.0.113.1").status_code, 200)

    def test_limit_is_per_x_real_ip(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        for url in self.urls[:5]:
            self._get(url, "203.0.113.1")
        self.assertEqual(self._get(self.urls[5], "203.0.113.2").status_code, 200)
        self.assertEqual(self._get(self.urls[6], "203.0.113.1").status_code, 429)

    def test_head_request_is_also_limited(self, mock_time):
        mock_time.time.return_value = 1_800_000_000
        for url in self.urls[:5]:
            self.client.head(url, HTTP_X_REAL_IP="203.0.113.1")
        self.assertEqual(self._get(self.urls[5], "203.0.113.1").status_code, 429)
