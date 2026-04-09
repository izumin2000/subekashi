"""
REST API ビューのテスト

SongAPI・EditorIsOpenView のレスポンス形式・ステータスコードを検証する。
SongThrottle はビュークラスに直接定義されているため、patch で無効化する。
"""
import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.throttling import BaseThrottle
from subekashi.models import Author, Editor, Song, SongLink


class NoThrottle(BaseThrottle):
    """テスト用: スロットリングを無効化する"""
    def allow_request(self, request, view):
        return True

    def wait(self):
        return None


STATIC_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
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

    def test_keyword_filter_narrows_results(self):
        response = self.client.get("/api/song/", {"keyword": "APIテスト曲1"})
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
        if data["result"]:
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


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
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


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
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
