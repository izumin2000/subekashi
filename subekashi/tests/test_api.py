"""
REST API ビューのテスト

SongAPI・EditorIsOpenView のレスポンス形式・ステータスコードを検証する。
SongThrottle はビュークラスに直接定義されているため、patch で無効化する。
"""
import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from subekashi.models import Ai, Author, Song, SongLink, Word


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


@patch("subekashi.views.api.word.WordCandidatesView.throttle_classes", [])
class WordCandidatesViewTest(TestCase):
    """WordCandidatesView GET /api/word/candidates/ のテスト"""

    def setUp(self):
        self.client = APIClient()

    def test_missing_params_returns_400(self):
        response = self.client.get("/api/word/candidates/")
        self.assertEqual(response.status_code, 400)

    def test_returns_matching_candidates(self):
        Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")
        Word.objects.create(word="走る", hinshi="動詞", candidate="疾走する")

        response = self.client.get("/api/word/candidates/", {"word": "走る", "hinshi": "動詞"})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.json()["candidates"], ["駆ける", "疾走する"])

    def test_no_matching_word_returns_empty_list(self):
        response = self.client.get("/api/word/candidates/", {"word": "存在しない単語", "hinshi": "動詞"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["candidates"], [])

    def test_limits_to_ten_candidates(self):
        for i in range(15):
            Word.objects.create(word="走る", hinshi="動詞", candidate=f"候補{i}")

        response = self.client.get("/api/word/candidates/", {"word": "走る", "hinshi": "動詞"})

        self.assertEqual(len(response.json()["candidates"]), 10)


@patch("subekashi.views.api.ai.AiWordSwapView.throttle_classes", [])
class AiWordSwapViewTest(TestCase):
    """AiWordSwapView POST /api/ai/swap/ のテスト"""

    def setUp(self):
        self.client = APIClient()
        # 「私は走る」 -> 私(名詞,index0) は(助詞,index1) 走る(動詞,index2)
        self.base = Ai.objects.create(lyrics="私は走る", score=5, genetype="model")
        Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")

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
        self.assertEqual(new_ai.genetype, "model")

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

    def test_candidate_not_created_when_invalid(self):
        count_before = Ai.objects.count()
        self.client.post(
            "/api/ai/swap/",
            data={"base_id": self.base.id, "token_index": 2, "candidate": "でっちあげ候補"},
            format="json",
        )
        self.assertEqual(Ai.objects.count(), count_before)
