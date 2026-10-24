"""
REST API ビューのテスト

SongAPI・EditorIsOpenView のレスポンス形式・ステータスコードを検証する。
SongThrottle はビュークラスに直接定義されているため、patch で無効化する。
ApiThrottleClientIPTest・ApiThrottleIdentTest では、スロットリングを X-Real-IP ごとに数えることを検証する（#1192）。
NewsAPIViewTest では、API_KEY を知っている人だけがニュースを登録できることを検証する（#925）。
SongLinkAPITest では、表記の違うビリビリ動画のURLでも同じ動画のURLが見つかることを検証する（#1246）。
"""
import json
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import URLResolver
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.views import APIView
from article.models import Article
from subekashi import urls as subekashi_urls
from subekashi.lib.song_search import DEFAULT_SIZE
from django.db import connection
from django.test.utils import CaptureQueriesContext
from subekashi.models import Ai, Author, Prush, Song, SongLink, Word
from subekashi.views.api.song import SongAPI


STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=STATIC_STORAGE)
@patch("subekashi.views.api.song.SongAPI.throttle_classes", [])
class SongAPIListTest(TestCase):
    """SongAPI GET /api/song/ のテスト"""

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(name="APIテスト作者")
        self.song1 = Song.objects.create(title="APIテスト曲1", lyrics="歌詞1")
        self.song2 = Song.objects.create(title="APIテスト曲2", lyrics="歌詞2")
        self.song1.authors.add(self.author)
        link = SongLink.objects.create(url="https://youtu.be/apitesturl01")
        link.songs.add(self.song1)

    def test_list_returns_200(self):
        response = self.client.get("/api/song/")
        self.assertEqual(response.status_code, 200)

    def test_response_contains_result_key(self):
        response = self.client.get("/api/song/")
        data = response.json()
        self.assertIn("result", data)

    def test_response_contains_statistics_keys(self):
        response = self.client.get("/api/song/")
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("page", data)
        self.assertIn("max_page", data)

    def test_count_matches_total_songs(self):
        response = self.client.get("/api/song/")
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_list_excludes_removed_song(self):
        # ユーザーが削除した曲（#1239）は返さない
        Song.objects.create(title="APIテスト削除した曲", is_removed=True)
        data = self.client.get("/api/song/").json()
        self.assertEqual(data["count"], 2)
        self.assertNotIn("APIテスト削除した曲", [song["title"] for song in data["result"]])

    def test_keyword_filter_narrows_results(self):
        response = self.client.get("/api/song/", {"keyword": "APIテスト曲1"})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["result"][0]["title"], "APIテスト曲1")

    def test_categorys_filter_supports_multiple_values(self):
        """#423: categorysはmediatypesと同様にカンマ区切りで複数のカテゴリを指定できること"""
        Song.objects.filter(pk=self.song1.pk).update(category="arrange")
        Song.objects.create(title="APIテスト曲3", category="meme")
        response = self.client.get("/api/song/", {"categorys": "arrange,meme"})
        titles = [song["title"] for song in response.json()["result"]]
        self.assertCountEqual(titles, ["APIテスト曲1", "APIテスト曲3"])

    def test_categorys_filter_supports_excluded_categorys(self):
        """#423: categorysで先頭に~を付けたカテゴリの曲は除くこと"""
        Song.objects.filter(pk=self.song1.pk).update(category="arrange")
        Song.objects.create(title="APIテスト曲3", category="meme")
        response = self.client.get("/api/song/", {"categorys": "~song,~meme"})
        titles = [song["title"] for song in response.json()["result"]]
        self.assertEqual(titles, ["APIテスト曲1"])

    def test_prush_filter_is_exact_match(self):
        """#1064: prushはプレラの名前の完全一致で絞り込むこと（「夏プレラ」で「晩夏プレラ6」の曲を含めない）"""
        Song.objects.filter(pk=self.song1.pk).update(prush=Prush.objects.create(name="夏プレラ"))
        Song.objects.filter(pk=self.song2.pk).update(prush=Prush.objects.create(name="晩夏プレラ6"))
        response = self.client.get("/api/song/", {"prush": "夏プレラ"})
        self.assertEqual([song["title"] for song in response.json()["result"]], ["APIテスト曲1"])
        response = self.client.get("/api/song/", {"prush": "プレラ"})
        self.assertEqual(response.json()["count"], 0)

    def test_result_contains_prush_name(self):
        """#1064: プレラはidではなく名前で返し、プレラが無い曲はnullを返すこと"""
        Song.objects.filter(pk=self.song1.pk).update(prush=Prush.objects.create(name="年末プレラ５"))
        result = {song["title"]: song["prush"] for song in self.client.get("/api/song/").json()["result"]}
        self.assertEqual(result, {"APIテスト曲1": "年末プレラ５", "APIテスト曲2": None})

    def test_prush_is_not_queried_per_song(self):
        """#1064: プレラの名前を返すために、曲ごとにプレラを取得しないこと（select_related）"""
        for i in range(3):
            Song.objects.create(title=f"APIテスト追加{i}", prush=Prush.objects.create(name=f"プレラ{i}"))
        for params in [{}, {"keyword": "APIテスト追加"}, {"prush": "プレラ0"}]:
            with self.subTest(params=params):
                with CaptureQueriesContext(connection) as context:
                    response = self.client.get("/api/song/", params)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(any(song["prush"] for song in response.json()["result"]))
                prush_queries = [query["sql"] for query in context.captured_queries if "FROM `subekashi_prush`" in query["sql"]]
                self.assertEqual(prush_queries, [])

    def test_result_contains_category(self):
        response = self.client.get("/api/song/", {"categorys": "song"})
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual({song["category"] for song in data["result"]}, {"song"})

    def test_is_lack_false_excludes_lack_songs(self):
        """is_lack=False で未完成の曲が除外されること（#970）"""
        # song1: URLあり・歌詞ありのオリジナル模倣曲（完成）、song2: URLなし（未完成）
        self.song1.is_original = True
        self.song1.save()
        response = self.client.get("/api/song/", {"is_lack": "False"})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["result"][0]["title"], "APIテスト曲1")

    def test_is_special_filter_narrows_results(self):
        """is_special=True でスペシャルデザインの曲のみ返されること（#939）"""
        self.song2.is_special = True
        self.song2.save()
        response = self.client.get("/api/song/", {"is_special": "True"})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["result"][0]["title"], "APIテスト曲2")

    def test_sort_by_imitated_count(self):
        """sort=-imitated_count で模倣曲の数が多い順に返されること（#542）"""
        self.song1.imitates.add(self.song2)
        response = self.client.get("/api/song/", {"sort": "-imitated_count"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([song["title"] for song in response.json()["result"]], ["APIテスト曲2", "APIテスト曲1"])

    def test_is_collab_filter_narrows_results(self):
        """is_collab=True で合作の曲（作者が2人以上の曲）のみ返されること（#943）"""
        self.song2.authors.add(self.author, Author.objects.create(name="APIテスト作者2"))
        response = self.client.get("/api/song/", {"is_collab": "True"})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["result"][0]["title"], "APIテスト曲2")

    def test_guesser_filter_matches_url(self):
        # #1117: song guesserはURLからもヒットする
        response = self.client.get("/api/song/", {"guesser": "https://www.youtube.com/watch?v=apitesturl01"})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["result"][0]["title"], "APIテスト曲1")

    def test_pagination_size_is_respected(self):
        response = self.client.get("/api/song/", {"size": "1"})
        data = response.json()
        self.assertEqual(len(data["result"]), 1)
        self.assertEqual(data["max_page"], 2)

    def test_invalid_sort_returns_400(self):
        response = self.client.get("/api/song/", {"sort": "invalid_field_xyz"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_sort_response_contains_error_key(self):
        response = self.client.get("/api/song/", {"sort": "invalid_field_xyz"})
        data = response.json()
        self.assertIn("error", data)

    def test_result_items_have_expected_fields(self):
        response = self.client.get("/api/song/")
        data = response.json()
        self.assertTrue(data["result"], "result が空です")
        item = data["result"][0]
        self.assertIn("id", item)
        self.assertIn("title", item)
        self.assertIn("authors", item)
        self.assertIn("url", item)

    def test_url_field_is_list(self):
        response = self.client.get("/api/song/")
        data = response.json()
        for item in data["result"]:
            self.assertIsInstance(item["url"], list)


@override_settings(STORAGES=STATIC_STORAGE)
@patch("subekashi.views.api.song.SongAPI.throttle_classes", [])
class SongAPIRetrieveTest(TestCase):
    """SongAPI GET /api/song/<id>/ のテスト"""

    def setUp(self):
        self.client = APIClient()
        self.song = Song.objects.create(title="個別取得テスト曲", lyrics="歌詞")

    def test_retrieve_existing_song_returns_200(self):
        response = self.client.get(f"/api/song/{self.song.id}/")
        self.assertEqual(response.status_code, 200)

    def test_retrieve_returns_correct_title(self):
        response = self.client.get(f"/api/song/{self.song.id}/")
        data = response.json()
        self.assertEqual(data["title"], "個別取得テスト曲")

    def test_retrieve_nonexistent_song_returns_404(self):
        response = self.client.get("/api/song/99999/")
        self.assertEqual(response.status_code, 404)

    def test_retrieve_removed_song_returns_404(self):
        # ユーザーが削除した曲（#1239）は返さない
        self.song.is_removed = True
        self.song.save()
        response = self.client.get(f"/api/song/{self.song.id}/")
        self.assertEqual(response.status_code, 404)

    def test_response_does_not_contain_is_removed(self):
        # 削除した曲は返さず常にFalseになるため、is_removedは含めない
        data = self.client.get(f"/api/song/{self.song.id}/").json()
        self.assertNotIn("is_removed", data)
        self.assertIn("is_deleted", data)
        self.assertIn("imitateds", data)
        self.assertIn("url", data)

    def test_imitates_and_imitateds_exclude_removed_song(self):
        removed = Song.objects.create(title="個別取得テストの削除した曲", is_removed=True)
        self.song.imitates.add(removed)
        removed.imitates.add(self.song)
        data = self.client.get(f"/api/song/{self.song.id}/").json()
        self.assertEqual(data["imitates"], [])
        self.assertEqual(data["imitateds"], [])


@override_settings(STORAGES=STATIC_STORAGE)
@patch("subekashi.views.api.song_edit_init.SongEditInitView.throttle_classes", [])
class SongEditInitViewTest(TestCase):
    """SongEditInitView GET /api/song_edit_init/ のテスト

    song_edit.jsは模倣一覧の表示と送信する模倣曲IDのどちらも、このAPIのimitate_songsを元にする（#1135）。
    """

    def setUp(self):
        self.client = APIClient()
        self.song = Song.objects.create(title="編集初期化テスト曲")

    def _get_imitate_ids(self):
        response = self.client.get("/api/song_edit_init/", {"song_id": self.song.id, "fetch_imitate": "1"})
        self.assertEqual(response.status_code, 200)
        return [song["id"] for song in response.json()["imitate_songs"]]

    def test_imitate_songs_is_empty_list_when_no_imitates(self):
        # song_edit.jsはimitate_songsを配列として扱うため、Noneではなく空リストを返す
        self.assertEqual(self._get_imitate_ids(), [])

    def test_imitate_songs_returns_all_imitates_over_default_size(self):
        # 検索のデフォルト件数で打ち切られると、保存時に残りの模倣情報が消えてしまう
        imitates = [Song.objects.create(title=f"模倣元{i}") for i in range(DEFAULT_SIZE + 1)]
        self.song.imitates.set(imitates)
        self.assertCountEqual(self._get_imitate_ids(), [song.id for song in imitates])

    def test_imitate_songs_includes_deleted_and_draft_songs(self):
        # 削除済み・下書きの曲が除外されると、保存時にその模倣情報が消えてしまう
        deleted_song = Song.objects.create(title="削除済み模倣元", is_deleted=True)
        draft_song = Song.objects.create(title="下書き模倣元", is_draft=True)
        self.song.imitates.set([deleted_song, draft_song])
        self.assertCountEqual(self._get_imitate_ids(), [deleted_song.id, draft_song.id])

    def test_imitate_songs_excludes_removed_song(self):
        # ユーザーが削除した曲（#1239）は模倣元に表示しない。保存しても模倣関係は消えない（UpdateSongTest）
        removed_song = Song.objects.create(title="削除した模倣元", is_removed=True)
        imitate_song = Song.objects.create(title="模倣元")
        self.song.imitates.set([removed_song, imitate_song])
        self.assertEqual(self._get_imitate_ids(), [imitate_song.id])

    def test_imitate_songs_prush_is_not_queried_per_song(self):
        """#1064: 模倣元の曲のプレラの名前を返すために、曲ごとにプレラを取得しないこと（select_related）"""
        self.song.imitates.set([Song.objects.create(title=f"模倣元{i}", prush=Prush.objects.create(name=f"プレラ{i}")) for i in range(3)])
        author = Author.objects.create(name="編集初期化テスト作者")
        for i in range(3):
            Song.objects.create(title="同じタイトルの曲", prush=Prush.objects.create(name=f"別のプレラ{i}")).authors.add(author)
        params = {"song_id": self.song.id, "fetch_imitate": "1", "title": "同じタイトルの曲", "authors": author.name}
        with CaptureQueriesContext(connection) as context:
            response = self.client.get("/api/song_edit_init/", params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(song["prush"] for song in response.json()["imitate_songs"]), ["プレラ0", "プレラ1", "プレラ2"])
        self.assertEqual(sorted(song["prush"] for song in response.json()["title_author_songs"]), ["別のプレラ0", "別のプレラ1", "別のプレラ2"])
        prush_queries = [query["sql"] for query in context.captured_queries if "FROM `subekashi_prush`" in query["sql"]]
        self.assertEqual(prush_queries, [])

    def test_nonexistent_song_id_returns_none_instead_of_500(self):
        response = self.client.get("/api/song_edit_init/", {"song_id": 99999, "fetch_imitate": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["imitate_songs"])

    def test_non_numeric_song_id_returns_none_instead_of_500(self):
        response = self.client.get("/api/song_edit_init/", {"song_id": "abc", "fetch_imitate": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["imitate_songs"])

    def test_superscript_digit_song_id_returns_none_instead_of_500(self):
        # "²"はstr.isdigit()がTrueになるがint()で変換できない
        response = self.client.get("/api/song_edit_init/", {"song_id": "²", "fetch_imitate": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["imitate_songs"])

    def test_out_of_range_song_id_returns_none_instead_of_500(self):
        response = self.client.get("/api/song_edit_init/", {"song_id": "9" * 30, "fetch_imitate": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["imitate_songs"])


@override_settings(STORAGES=STATIC_STORAGE)
@patch("subekashi.views.api.songlink.SongLinkAPI.throttle_classes", [])
class SongLinkAPITest(TestCase):
    """SongLinkAPI GET /api/songlink/ のテスト

    song_edit.js・song_new.jsは、入力したURLが登録済みかをこのAPIで判定する。
    """

    def setUp(self):
        self.client = APIClient()
        self.song = Song.objects.create(title="URLテスト曲")
        self.link = SongLink.objects.create(url="https://bilibili.com/video/BV1qV411J7Kq")
        self.link.songs.add(self.song)

    def _get_link_ids(self, url):
        response = self.client.get("/api/songlink/", {"url": url})
        self.assertEqual(response.status_code, 200)
        return [link["id"] for link in response.json()["result"]]

    def _get_song_ids(self, url):
        response = self.client.get("/api/songlink/", {"url": url})
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(len(result), 1)
        return [song["id"] for song in result[0]["songs"]]

    def test_bilibili_url_is_found_by_av_and_unformatted_url(self):
        # #1246: av番号・www・末尾の/・クエリの付いたURLでも、同じ動画のURLが見つかる
        for url in [
            "https://bilibili.com/video/BV1qV411J7Kq",
            "https://www.bilibili.com/video/av417727107/",
            "https://m.bilibili.com/video/BV1qV411J7Kq/?spm_id_from=333.999.0.0&p=1",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self._get_link_ids(url), [self.link.id])

    def test_bilibili_url_of_other_page_is_not_found(self):
        # #1246: 2パート目以降は別の曲のことがあるため、別のURLとして扱う
        self.assertEqual(self._get_link_ids("https://www.bilibili.com/video/BV1qV411J7Kq?p=2"), [])

    def test_songs_contains_linked_song(self):
        self.assertEqual(self._get_song_ids(self.link.url), [self.song.id])

    def test_songs_excludes_removed_song(self):
        # ユーザーが削除した曲（#1239）は含めない
        removed = Song.objects.create(title="URLテストの削除した曲", is_removed=True)
        self.link.songs.add(removed)
        self.assertEqual(self._get_song_ids(self.link.url), [self.song.id])

    def test_url_of_only_removed_song_has_no_songs(self):
        # ユーザーが削除した曲（#1239）だけに紐づくURLは、曲の登録・編集画面で登録できるURLとして扱われる
        removed = Song.objects.create(title="URLテストの削除した曲", is_removed=True)
        link = SongLink.objects.create(url="https://youtu.be/songlink001")
        link.songs.add(removed)
        self.assertEqual(self._get_song_ids(link.url), [])


@override_settings(STORAGES=STATIC_STORAGE)
class EditorIsOpenViewTest(TestCase):
    """EditorIsOpenView /api/editor/is_open のテスト

    このエンドポイントは PUT のみ受け付け、暗号化済み IP を必要とする。
    ここでは GET が 405 を返すこと、無効なペイロードが 400 を返すことを確認する。
    """

    def setUp(self):
        self.client = APIClient()

    def test_get_returns_405(self):
        """GET は許可されていないため 405 が返る"""
        response = self.client.get("/api/editor/is_open")
        self.assertEqual(response.status_code, 405)

    def test_put_without_body_returns_400(self):
        """ペイロードなしの PUT は 400 が返る"""
        response = self.client.put("/api/editor/is_open", data={}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_put_with_short_ip_returns_400(self):
        """ip が短すぎる場合は 400 が返る"""
        response = self.client.put(
            "/api/editor/is_open",
            data={"ip": "short", "is_open": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


@override_settings(STORAGES=STATIC_STORAGE, API_KEY="test-api-key")
class NewsAPIViewTest(TestCase):
    """NewsAPIView POST /api/news/ のテスト（#925）"""

    def setUp(self):
        self.client = APIClient()

    def _post(self, data, api_key="test-api-key", client=None):
        headers = {} if api_key is None else {"HTTP_X_API_KEY": api_key}
        return (client or self.client).post("/api/news/", data=data, format="json", **headers)

    def test_post_creates_news(self):
        before = timezone.now()
        response = self._post({"article_id": "testNews", "title": "テストのニュース\n"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"article_id": "testNews", "title": "テストのニュース"})
        article = Article.objects.get(article_id="testNews")
        self.assertEqual(article.title, "テストのニュース")
        self.assertEqual(article.tag, "news")
        self.assertEqual(article.author, "全て歌詞の所為です。")
        self.assertTrue(article.is_open)
        self.assertTrue(article.is_md)
        self.assertFalse(article.handle_as_news)
        self.assertGreaterEqual(article.post_time, before)
        self.assertIn(article, Article.get_top_news_articles())

    def test_markdown_title_is_converted_to_html(self):
        response = self._post({"article_id": "testNews", "title": "[リンク](https://example.com)が公開される"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Article.objects.get(article_id="testNews").title,
            '<a href="https://example.com">リンク</a>が公開される',
        )

    def test_posted_news_is_shown_on_top(self):
        self._post({"article_id": "testNews", "title": "[リンク](https://example.com)が公開される"})

        response = self.client.get("/")

        self.assertContains(response, '<span><a href="https://example.com">リンク</a>が公開される</span>')

    def test_post_without_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        response = self._post({"article_id": "testNews", "title": "テストのニュース"}, client=client)
        self.assertEqual(response.status_code, 201)

    def test_without_api_key_returns_403(self):
        response = self._post({"article_id": "testNews", "title": "テストのニュース"}, api_key=None)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Article.objects.filter(article_id="testNews").exists())

    def test_wrong_api_key_returns_403(self):
        response = self._post({"article_id": "testNews", "title": "テストのニュース"}, api_key="wrong-api-key")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Article.objects.filter(article_id="testNews").exists())

    def test_logged_in_superuser_without_api_key_returns_403(self):
        user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(user)
        response = self._post({"article_id": "testNews", "title": "テストのニュース"}, api_key=None)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Article.objects.filter(article_id="testNews").exists())

    @override_settings(API_KEY="")
    def test_empty_api_key_setting_rejects_empty_header(self):
        response = self._post({"article_id": "testNews", "title": "テストのニュース"}, api_key="")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Article.objects.filter(article_id="testNews").exists())

    def test_get_returns_405(self):
        response = self.client.get("/api/news/", HTTP_X_API_KEY="test-api-key")
        self.assertEqual(response.status_code, 405)

    def test_existing_article_id_returns_400(self):
        post_time = timezone.now() - timedelta(days=1)
        Article.objects.create(article_id="testNews", title="既存の記事", tag="blog", post_time=post_time)

        response = self._post({"article_id": "testNews", "title": "テストのニュース"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("article_id", response.json())
        article = Article.objects.get(article_id="testNews")
        self.assertEqual(article.title, "既存の記事")
        self.assertEqual(article.tag, "blog")
        self.assertEqual(article.post_time, post_time)

    def test_invalid_article_id_returns_400(self):
        for article_id in ["", "test/news", "テスト", "a" * 101]:
            with self.subTest(article_id=article_id):
                response = self._post({"article_id": article_id, "title": "テストのニュース"})
                self.assertEqual(response.status_code, 400)
                self.assertIn("article_id", response.json())
        self.assertFalse(Article.objects.exists())

    def test_blank_title_returns_400(self):
        for data in [{"article_id": "testNews"}, {"article_id": "testNews", "title": " \n"}]:
            with self.subTest(data=data):
                response = self._post(data)
                self.assertEqual(response.status_code, 400)
                self.assertIn("title", response.json())
        self.assertFalse(Article.objects.exists())

    def test_title_too_long_after_conversion_returns_400(self):
        response = self._post({"article_id": "testNews", "title": "**a**" * 100})

        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.json())
        self.assertFalse(Article.objects.exists())


@patch("subekashi.views.api.word.WordCandidatesView.throttle_classes", [])
class WordCandidatesViewTest(TestCase):
    """WordCandidatesView GET /api/word/candidates/ のテスト"""

    def setUp(self):
        self.client = APIClient()

    def test_missing_params_returns_400(self):
        response = self.client.get("/api/word/candidates/")
        self.assertEqual(response.status_code, 400)

    def test_returns_matching_candidates(self):
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="疾走する")

        response = self.client.get("/api/word/candidates/", {"word": "走る", "hinshi": "動詞", "katsuyou": "基本形"})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.json()["candidates"], ["駆ける", "疾走する"])

    def test_no_matching_word_returns_empty_list(self):
        response = self.client.get("/api/word/candidates/", {"word": "存在しない単語", "hinshi": "動詞", "katsuyou": "基本形"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candidates"], [])

    def test_returns_candidates_from_other_words_with_same_hinshi(self):
        # wordがword.json由来のデータに存在しなくても、hinshi・katsuyouが一致する
        # 他のwordの候補を横断的に返す
        Word.objects.create(word="歩く", hinshi="動詞", katsuyou="基本形", candidate="進む")

        response = self.client.get("/api/word/candidates/", {"word": "走る", "hinshi": "動詞", "katsuyou": "基本形"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candidates"], ["進む"])

    def test_excludes_candidates_with_different_katsuyou(self):
        Word.objects.create(word="読ん", hinshi="動詞", katsuyou="連用タ接続", candidate="話し")

        response = self.client.get("/api/word/candidates/", {"word": "読む", "hinshi": "動詞", "katsuyou": "基本形"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candidates"], [])

    def test_limits_to_ten_candidates(self):
        for i in range(15):
            Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate=f"候補{i}")

        response = self.client.get("/api/word/candidates/", {"word": "走る", "hinshi": "動詞", "katsuyou": "基本形"})

        self.assertEqual(len(response.json()["candidates"]), 10)


@patch("subekashi.views.api.ai.AiWordSwapView.throttle_classes", [])
class AiWordSwapViewTest(TestCase):
    """AiWordSwapView POST /api/ai/swap/ のテスト"""

    def setUp(self):
        self.client = APIClient()
        # 「私は走る」 -> 私(名詞,index0) は(助詞,index1) 走る(動詞,基本形,index2)
        self.base = Ai.objects.create(lyrics="私は走る", score=0, genetype="janome")
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

    def test_valid_swap_creates_new_ai_record(self):
        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "駆ける"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        new_id = response.json()["id"]
        new_ai = Ai.objects.get(pk=new_id)
        self.assertEqual(new_ai.lyrics, "私は駆ける")
        self.assertEqual(new_ai.score, 0)
        self.assertEqual(new_ai.genetype, "janome")

    def test_response_includes_retokenized_tokens(self):
        # janomeは文脈依存の統計的トークナイザのため、入れ替え後の歌詞を
        # クライアント側が古いtoken_indexのまま使い回すとズレる可能性がある。
        # レスポンスに再トークナイズ済みのtokensを含め、クライアントが
        # その行の表示を丸ごと作り直せるようにしている
        # 「駆ける」自身もWord候補を持たせ、再トークナイズ結果が
        # 使い回しではなく実際に新しい歌詞を解析した結果であることを確認する
        Word.objects.create(word="駆ける", hinshi="動詞", katsuyou="基本形", candidate="走る")

        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "駆ける"},
            format="json",
        )

        tokens = response.json()["tokens"]
        surfaces = [t["surface"] for t in tokens]
        self.assertEqual(surfaces, ["私", "は", "駆ける"])
        by_surface = {t["surface"]: t for t in tokens}
        self.assertTrue(by_surface["駆ける"]["is_replaceable"])
        self.assertEqual(by_surface["駆ける"]["katsuyou"], "基本形")
        self.assertEqual(by_surface["駆ける"]["index"], 2)
        self.assertFalse(by_surface["私"]["is_replaceable"])

    def test_original_ai_record_is_unchanged(self):
        self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "駆ける"},
            format="json",
        )

        self.base.refresh_from_db()
        self.assertEqual(self.base.lyrics, "私は走る")

    def test_nonexistent_base_id_returns_404(self):
        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": 999999, "token_index": 2, "candidate": "駆ける"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_base_with_legacy_model_genetype_returns_404(self):
        # 単語入れ替えはgenetype="janome"のAiレコードからのみ許可する。
        # UI上は最高評価の歌詞（/ai/）やレガシーgenetype="model"のレコードには
        # 入れ替えボタンを出していないが、base_idが分かればAPIを直叩きされる
        # 可能性があるため、サーバー側でもgenetypeを検証する
        legacy_base = Ai.objects.create(lyrics="全て走る所為です", score=5, genetype="model")

        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": legacy_base.id, "token_index": 2, "candidate": "駆ける"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_out_of_range_token_index_returns_400(self):
        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 99, "candidate": "駆ける"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_non_replaceable_token_returns_400(self):
        # index1 は助詞「は」で置き換え対象外
        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 1, "candidate": "が"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_candidate_not_in_word_table_returns_400(self):
        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "でっちあげ候補"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_candidate_with_different_katsuyou_returns_400(self):
        # hinshiは一致するが活用形（katsuyou）が違う候補は、文法が破綻するため拒否する
        Word.objects.create(word="読ん", hinshi="動詞", katsuyou="連用タ接続", candidate="話し")

        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "話し"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_candidate_not_created_when_invalid(self):
        count_before = Ai.objects.count()
        self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "でっちあげ候補"},
            format="json",
        )
        self.assertEqual(Ai.objects.count(), count_before)

    def test_duplicate_swap_does_not_create_new_record(self):
        # 同じ入れ替え結果が既に存在する場合は、重複作成せず既存レコードを返す
        first = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "駆ける"},
            format="json",
        )
        count_after_first = Ai.objects.count()

        second = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "駆ける"},
            format="json",
        )

        self.assertEqual(Ai.objects.count(), count_after_first)
        self.assertEqual(first.json()["id"], second.json()["id"])
        # 新規作成時は201、既存レコードの再利用時は200を返す（REST的な正確性のため）
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)

    def test_existing_record_with_different_genetype_is_not_reused(self):
        # lyricsが同じでもgenetypeが違う既存レコード（例: model起源のたまたま
        # 同じ文字列）を誤って返さず、janome genetypeの新規レコードを作成する
        Ai.objects.create(lyrics="私は駆ける", score=5, genetype="model")

        response = self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "駆ける"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        new_ai = Ai.objects.get(pk=response.json()["id"])
        self.assertEqual(new_ai.genetype, "janome")
        self.assertEqual(new_ai.score, 0)
        self.assertEqual(Ai.objects.filter(lyrics="私は駆ける").count(), 2)


@override_settings(STORAGES=STATIC_STORAGE)
@patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=1_800_000_000)
class ApiThrottleClientIPTest(TestCase):
    """APIのスロットリングを X-Real-IP ごとに数えることのテスト（#1192）

    DRFの既定のget_identはX-Forwarded-Forの全体を識別子にするため、クライアントが値を変えるだけで制限を回避できる。
    subekashi.lib.throttlingのクラスでX-Real-IP（無ければREMOTE_ADDR）を使うことを、SongAPI（毎秒2回まで）で確認する。
    1秒の区切りをまたいでカウントがリセットされないよう、DRFのスロットリングの時刻を固定する。
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def _get(self, **extra):
        return self.client.get("/api/song/", **extra)

    def assertLimited(self, response):
        self.assertEqual(response.status_code, 429)

    def test_third_request_in_a_second_is_limited(self, mock_timer):
        for _ in range(2):
            self.assertEqual(self._get(HTTP_X_REAL_IP="203.0.113.1").status_code, 200)
        self.assertLimited(self._get(HTTP_X_REAL_IP="203.0.113.1"))

    def test_limit_is_per_x_real_ip(self, mock_timer):
        for _ in range(2):
            self._get(HTTP_X_REAL_IP="203.0.113.1")
        self.assertEqual(self._get(HTTP_X_REAL_IP="203.0.113.2").status_code, 200)
        self.assertLimited(self._get(HTTP_X_REAL_IP="203.0.113.1"))

    def test_x_forwarded_for_does_not_bypass_limit(self, mock_timer):
        for i in range(2):
            self._get(HTTP_X_REAL_IP="203.0.113.1", HTTP_X_FORWARDED_FOR=f"198.51.100.{i}")
        self.assertLimited(self._get(HTTP_X_REAL_IP="203.0.113.1", HTTP_X_FORWARDED_FOR="198.51.100.9"))

    def test_remote_addr_is_used_without_x_real_ip(self, mock_timer):
        for _ in range(2):
            self._get(REMOTE_ADDR="198.51.100.1")
        self.assertEqual(self._get(REMOTE_ADDR="198.51.100.2").status_code, 200)
        self.assertLimited(self._get(REMOTE_ADDR="198.51.100.1"))


class ApiThrottleIdentTest(SimpleTestCase):
    """subekashi.urls の全てのDRFのビューのスロットリングが X-Real-IP で数えることのテスト（#1192）

    ビューを追加したときに、DRFのスロットリングのクラスをそのまま使っていないかを確認する。
    """

    def _api_view_classes(self, patterns):
        classes = set()
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                classes |= self._api_view_classes(pattern.url_patterns)
                continue
            view_class = getattr(pattern.callback, "cls", None)
            if view_class and issubclass(view_class, APIView):
                classes.add(view_class)
        return classes

    def test_all_throttles_identify_by_x_real_ip(self):
        view_classes = self._api_view_classes(subekashi_urls.urlpatterns)
        self.assertIn(SongAPI, view_classes)
        request = RequestFactory().get(
            "/api/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="203.0.113.1", HTTP_X_FORWARDED_FOR="198.51.100.1",
        )
        for view_class in view_classes:
            self.assertTrue(view_class.throttle_classes, view_class.__name__)
            for throttle_class in view_class.throttle_classes:
                with self.subTest(view=view_class.__name__, throttle=throttle_class.__name__):
                    self.assertEqual(throttle_class().get_ident(request), "203.0.113.1")
