"""
曲のAPIの登録・変更・削除のテスト（#973）

POST /api/song/・PUT・PATCH・DELETE /api/song/<id>/ が、管理サイトで発行したAPIキー（X-API-Keyヘッダー）を持つリクエストだけを受け付け、
画面と同じビュー（SongNewView・SongEditView・SongDeleteView）を実行して、その結果をJSONで返すことを検証する。
Discordへの通知（send_discord）とYouTube Data APIは、ビューのモジュールごとにモックする。
"""
import unicodedata
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from subekashi.constants.constants import BANNED_ERROR
from subekashi.lib.security import encrypt
from subekashi.models import ApiKey, Author, Editor, History, Song, SongLink
from subekashi.views.api.song_write import LOCK_ERROR, NOT_FOUND_ERROR, REMOVED_ERROR, SERVER_ERROR

STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

YOUTUBE_RESPONSE = {"title": "YouTubeの曲", "author": "YouTubeのチャンネル", "upload_time": None, "view": 100, "like": 5}


@override_settings(STORAGES=STATIC_STORAGE)
class SongWriteAPITestCase(TestCase):
    """APIキーの発行・スロットリングとDiscordのモック・リクエストの送信をまとめた、各テストの基底クラス"""

    def setUp(self):
        self.client = APIClient()
        # SongThrottleはビュークラスに直接定義されているため、patchで無効化する
        throttle_patcher = patch("subekashi.views.api.song.SongAPI.throttle_classes", [])
        throttle_patcher.start()
        self.addCleanup(throttle_patcher.stop)
        self.api_key = ApiKey.objects.create(name="テスト用のAPIキー")
        self.discord = {}
        for module in ("song_new", "song_edit", "song_delete"):
            patcher = patch(f"subekashi.views.{module}.send_discord", return_value=True)
            self.discord[module] = patcher.start()
            self.addCleanup(patcher.stop)

    def _request(self, method, path, data=None, api_key=..., client=None, **extra):
        api_key = self.api_key.key if api_key is ... else api_key
        headers = {} if api_key is None else {"HTTP_X_API_KEY": api_key}
        return getattr(client or self.client, method)(path, data=data, format="json", **headers, **extra)

    def _post(self, data=None, **kwargs):
        return self._request("post", "/api/song/", data, **kwargs)

    def _put(self, song_id, data=None, **kwargs):
        return self._request("put", f"/api/song/{song_id}/", data, **kwargs)

    def _patch(self, song_id, data=None, **kwargs):
        return self._request("patch", f"/api/song/{song_id}/", data, **kwargs)

    def _delete(self, song_id, data=None, **kwargs):
        return self._request("delete", f"/api/song/{song_id}/", data, **kwargs)


class SongWriteAPIAuthTest(SongWriteAPITestCase):
    """APIキーの認可のテスト。3つのエンドポイントのどれも、APIキーが無ければ実行しない"""

    def setUp(self):
        super().setUp()
        self.song = Song.objects.create(title="認可テスト曲", lyrics="元の歌詞")
        self.song.authors.set([Author.objects.create(name="認可テスト作者")])

    def _write_requests(self, **kwargs):
        return [
            ("登録", self._post({"title": "認可で登録", "authors": "認可作者"}, **kwargs)),
            ("変更", self._patch(self.song.id, {"lyrics": "認可で変更"}, **kwargs)),
            ("削除", self._delete(self.song.id, {"reason": "認可で削除"}, **kwargs)),
        ]

    def _assert_rejected(self, **kwargs):
        for name, response in self._write_requests(**kwargs):
            with self.subTest(name):
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {"detail": "APIキーが正しくありません"})
        self.assertFalse(Song.objects.filter(title="認可で登録").exists())
        self.song.refresh_from_db()
        self.assertEqual(self.song.lyrics, "元の歌詞")
        self.assertFalse(self.song.is_removed)
        self.assertEqual(History.objects.count(), 0)
        for mock in self.discord.values():
            mock.assert_not_called()

    def test_without_api_key_returns_403(self):
        self._assert_rejected(api_key=None)

    def test_wrong_api_key_returns_403(self):
        self._assert_rejected(api_key="wrong-api-key")

    def test_empty_api_key_returns_403(self):
        self._assert_rejected(api_key="")

    def test_inactive_api_key_returns_403(self):
        self.api_key.is_active = False
        self.api_key.save()
        self._assert_rejected()

    def test_deleted_api_key_returns_403(self):
        self.api_key.delete()
        self.assertEqual(self._post({"title": "認可で登録", "authors": "認可作者"}, api_key="deleted").status_code, 403)

    def test_api_key_with_different_case_returns_403(self):
        self._assert_rejected(api_key=self.api_key.key.swapcase())

    def test_setting_api_key_for_news_does_not_work(self):
        with override_settings(API_KEY="news-api-key"):
            self._assert_rejected(api_key="news-api-key")

    def test_logged_in_superuser_without_api_key_returns_403(self):
        user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(user)
        self._assert_rejected(api_key=None)

    def test_any_valid_api_key_is_accepted(self):
        other_key = ApiKey.objects.create(name="別のAPIキー")
        response = self._post({"title": "別のキーで登録", "authors": "認可作者"}, api_key=other_key.key)
        self.assertEqual(response.status_code, 201)

    def test_valid_api_key_does_not_require_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        user = User.objects.create_superuser("admin", "admin@example.com", "password")
        client.force_login(user)
        for name, response in [
            ("登録", self._post({"title": "CSRFなしで登録", "authors": "認可作者"}, client=client)),
            ("変更", self._patch(self.song.id, {"lyrics": "CSRFなしで変更"}, client=client)),
            ("削除", self._delete(self.song.id, {"reason": "CSRFなしで削除"}, client=client)),
        ]:
            with self.subTest(name):
                self.assertIn(response.status_code, (201, 200, 204))

    def test_get_does_not_require_api_key(self):
        self.assertEqual(self.client.get("/api/song/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/song/{self.song.id}/").status_code, 200)

    def test_put_and_patch_to_list_url_returns_405(self):
        self.assertEqual(self._request("put", "/api/song/", {"title": "x"}).status_code, 405)
        self.assertEqual(self._request("delete", "/api/song/").status_code, 405)

    def test_post_to_detail_url_returns_405(self):
        self.assertEqual(self._request("post", f"/api/song/{self.song.id}/", {"title": "x"}).status_code, 405)

    def test_banned_editor_returns_403(self):
        Editor.objects.create(ip=encrypt("127.0.0.1"), is_banned=True)
        for name, response in self._write_requests():
            with self.subTest(name):
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {"detail": BANNED_ERROR})
        self.assertFalse(Song.objects.filter(title="認可で登録").exists())
        self.song.refresh_from_db()
        self.assertEqual(self.song.lyrics, "元の歌詞")


class SongCreateAPITest(SongWriteAPITestCase):
    """POST /api/song/ のテスト。SongNewView (/songs/new/) のPOSTに対応する"""

    def test_post_creates_song(self):
        response = self._post({"title": "APIで登録した曲", "authors": "API作者A,API作者B"})

        self.assertEqual(response.status_code, 201)
        song = Song.objects.get(title="APIで登録した曲")
        self.assertCountEqual([author.name for author in song.authors.all()], ["API作者A", "API作者B"])
        body = response.json()
        self.assertEqual(body["id"], song.id)
        self.assertEqual(body["title"], "APIで登録した曲")
        self.assertCountEqual([author["name"] for author in body["authors"]], ["API作者A", "API作者B"])
        self.assertEqual(body["url"], [])
        self.discord["song_new"].assert_called_once()

    def test_authors_can_be_a_list(self):
        response = self._post({"title": "作者の配列", "authors": ["配列作者A", "配列作者B"]})

        self.assertEqual(response.status_code, 201)
        self.assertCountEqual([author["name"] for author in response.json()["authors"]], ["配列作者A", "配列作者B"])

    def test_default_values(self):
        response = self._post({"title": "初期値の曲", "authors": "初期値作者"})

        song = Song.objects.get(pk=response.json()["id"])
        self.assertEqual(song.category, "song")
        self.assertTrue(song.is_subeana)
        for flag in ("is_original", "is_deleted", "is_joke", "is_inst", "is_questionable", "is_draft"):
            self.assertFalse(getattr(song, flag), flag)

    def test_post_with_flags_and_category(self):
        response = self._post({
            "title": "フラグ付きの曲",
            "authors": "フラグ作者",
            "category": "cover",
            "is_original": True,
            "is_deleted": True,
            "is_joke": True,
            "is_inst": True,
            "is_subeana": False,
        })

        self.assertEqual(response.status_code, 201)
        song = Song.objects.get(pk=response.json()["id"])
        self.assertEqual(song.category, "cover")
        self.assertTrue(song.is_original)
        self.assertTrue(song.is_deleted)
        self.assertTrue(song.is_joke)
        self.assertTrue(song.is_inst)
        self.assertFalse(song.is_subeana)
        self.assertFalse(song.is_questionable)

    def test_is_questionable_clears_is_original(self):
        """画面と同じく、is_questionableなら、オリジナル模倣はリクエストの値に関わらずFalseになること"""
        response = self._post({"title": "界隈曲?の曲", "authors": "界隈曲?作者", "is_questionable": True, "is_original": True})

        song = Song.objects.get(pk=response.json()["id"])
        self.assertTrue(song.is_questionable)
        self.assertFalse(song.is_original)

    def test_false_string_is_treated_as_false(self):
        response = self._post({"title": "文字列のfalse", "authors": "文字列作者", "is_joke": "false", "is_inst": "true"})

        song = Song.objects.get(pk=response.json()["id"])
        self.assertFalse(song.is_joke)
        self.assertTrue(song.is_inst)

    def test_form_encoded_request_is_accepted(self):
        response = self.client.post(
            "/api/song/",
            {"title": "フォームで登録", "authors": "フォーム作者", "is_joke": "true"},
            HTTP_X_API_KEY=self.api_key.key,
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Song.objects.get(title="フォームで登録").is_joke)

    def test_decomposed_dakuten_is_normalized(self):
        """JSONのリクエストにも、濁点・半濁点の正規化（NormalizePostDataMiddleware）をすること"""
        decomposed_title = unicodedata.normalize("NFD", "がぱ")
        decomposed_authors = unicodedata.normalize("NFD", "ぱぱ")
        self.assertNotEqual(decomposed_title, "がぱ")
        response = self._post({"title": decomposed_title, "authors": decomposed_authors})

        self.assertEqual(response.status_code, 201)
        song = Song.objects.get(pk=response.json()["id"])
        self.assertEqual(song.title, "がぱ")
        self.assertEqual([author.name for author in song.authors.all()], ["ぱぱ"])

    @patch("subekashi.views.song_new.get_youtube_api", return_value=YOUTUBE_RESPONSE)
    def test_post_with_youtube_url_uses_title_and_authors_of_the_video(self, mock_api):
        response = self._post({"url": "https://youtu.be/abcdefghijk", "title": "無視される", "authors": "無視される"})

        self.assertEqual(response.status_code, 201)
        mock_api.assert_called_once_with("abcdefghijk")
        song = Song.objects.get(pk=response.json()["id"])
        self.assertEqual(song.title, "YouTubeの曲")
        self.assertEqual([author.name for author in song.authors.all()], ["YouTubeのチャンネル"])
        self.assertEqual(song.view, 100)
        self.assertEqual(response.json()["url"], ["https://youtu.be/abcdefghijk"])

    def test_history_and_editor_are_recorded_as_in_the_form(self):
        response = self._post({"title": "履歴の曲", "authors": "履歴作者"})

        song = Song.objects.get(pk=response.json()["id"])
        history = History.objects.get(song=song)
        self.assertEqual(history.history_type, "new")
        self.assertEqual(history.title, "履歴の曲を新規作成")
        self.assertEqual(history.editor.ip, encrypt("127.0.0.1"))

    def test_editor_is_identified_by_client_ip(self):
        self._post({"title": "IPの曲", "authors": "IP作者"}, HTTP_X_REAL_IP="203.0.113.7")

        self.assertEqual(History.objects.get(title="IPの曲を新規作成").editor.ip, encrypt("203.0.113.7"))

    def test_missing_authors_returns_400(self):
        response = self._post({"title": "作者なし"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "作者は空白にできません。"})
        self.assertFalse(Song.objects.filter(title="作者なし").exists())

    def test_missing_title_returns_400(self):
        response = self._post({"authors": "タイトルなし作者"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "タイトルが未入力です。"})

    def test_invalid_category_returns_400(self):
        response = self._post({"title": "カテゴリ不正", "authors": "作者", "category": "invalid"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "カテゴリが不正です。"})
        self.assertFalse(Song.objects.filter(title="カテゴリ不正").exists())

    def test_non_youtube_url_returns_400(self):
        response = self._post({"title": "YouTube以外", "authors": "作者", "url": "https://example.com/video"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "URLがYouTubeのURLではありません。"})

    def test_registered_url_returns_400(self):
        link = SongLink.objects.create(url="https://youtu.be/regist00001")
        link.songs.add(Song.objects.create(title="登録済みの曲"))

        response = self._post({"url": "https://youtu.be/regist00001"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "URLは既に登録されています。"})

    @patch("subekashi.views.song_new.get_youtube_api", return_value=YOUTUBE_RESPONSE)
    def test_allow_dup_url_registers_registered_url(self, mock_api):
        link = SongLink.objects.create(url="https://youtu.be/regist00002")
        link.songs.add(Song.objects.create(title="登録済みの曲"))

        response = self._post({"url": "https://youtu.be/regist00002", "allow_dup_url": "https://youtu.be/regist00002"})

        self.assertEqual(response.status_code, 201)
        link.refresh_from_db()
        self.assertTrue(link.allow_dup)
        self.assertEqual(link.songs.count(), 2)

    def test_reject_list_error_is_returned_as_it_is(self):
        """登録の画面はエラーをエスケープして表示するため、APIは文字列をそのまま返すこと"""
        with patch("subekashi.views.song_new.check_reject_list", return_value="<b>拒否</b>さんの曲は登録することができません。"):
            response = self._post({"title": "拒否される曲", "authors": "拒否"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "<b>拒否</b>さんの曲は登録することができません。"})
        self.assertFalse(Song.objects.filter(title="拒否される曲").exists())

    def test_discord_failure_returns_500_and_deletes_song(self):
        self.discord["song_new"].return_value = False

        response = self._post({"title": "通知に失敗する曲", "authors": "通知作者"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": SERVER_ERROR})
        self.assertFalse(Song.objects.filter(title="通知に失敗する曲").exists())

    def test_non_object_body_returns_400(self):
        response = self._post([{"title": "配列", "authors": "作者"}])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "リクエストはJSONのオブジェクトで指定してください。"})

    def test_invalid_flag_returns_400(self):
        response = self._post({"title": "不正なフラグ", "authors": "作者", "is_joke": "yes"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "is_jokeは真偽値で指定してください。"})
        self.assertFalse(Song.objects.filter(title="不正なフラグ").exists())


class SongUpdateAPITest(SongWriteAPITestCase):
    """PUT・PATCH /api/song/<id>/ のテスト。SongEditView (/songs/<id>/edit/) のPOSTに対応する"""

    def setUp(self):
        super().setUp()
        self.author = Author.objects.create(name="元の作者")
        self.imitated = Song.objects.create(title="模倣元の曲")
        self.song = Song.objects.create(
            title="元の曲", lyrics="元の歌詞", category="arrange", is_original=True, is_joke=True, is_inst=True,
        )
        self.song.authors.set([self.author])
        self.song.imitates.set([self.imitated])
        link = SongLink.objects.create(url="https://youtu.be/original001")
        link.songs.add(self.song)

    def _assert_unchanged(self):
        song = Song.objects.get(pk=self.song.pk)
        self.assertEqual(song.title, "元の曲")
        self.assertEqual(song.lyrics, "元の歌詞")
        self.assertEqual(song.category, "arrange")
        self.assertEqual([author.name for author in song.authors.all()], ["元の作者"])
        self.assertEqual(list(song.imitates.all()), [self.imitated])
        self.assertEqual(list(song.links.values_list("url", flat=True)), ["https://youtu.be/original001"])
        self.assertEqual(History.objects.filter(song=song).count(), 0)

    def test_put_updates_song(self):
        response = self._put(self.song.id, {
            "title": "変更後の曲",
            "authors": ["変更後の作者A", "変更後の作者B"],
            "url": ["https://youtu.be/changed0001"],
            "imitate": [self.imitated.id],
            "lyrics": "変更後の歌詞",
            "category": "cover",
            "is_original": False,
            "is_joke": False,
            "is_inst": False,
            "is_draft": True,
        })

        self.assertEqual(response.status_code, 200)
        song = Song.objects.get(pk=self.song.pk)
        self.assertEqual(song.title, "変更後の曲")
        self.assertCountEqual([author.name for author in song.authors.all()], ["変更後の作者A", "変更後の作者B"])
        self.assertEqual(list(song.links.values_list("url", flat=True)), ["https://youtu.be/changed0001"])
        self.assertEqual(song.lyrics, "変更後の歌詞")
        self.assertEqual(song.category, "cover")
        self.assertFalse(song.is_original)
        self.assertFalse(song.is_joke)
        self.assertFalse(song.is_inst)
        self.assertTrue(song.is_draft)
        body = response.json()
        self.assertEqual(body["id"], song.id)
        self.assertEqual(body["title"], "変更後の曲")
        self.assertEqual(body["url"], ["https://youtu.be/changed0001"])
        self.assertEqual(body["lyrics"], "変更後の歌詞")
        self.discord["song_edit"].assert_called_once()

    def test_put_and_patch_keep_unspecified_fields(self):
        """画面のフォームは送らなかった項目を空にするが、APIは指定しなかった項目を今の値のままにすること"""
        for name, request in (("PUT", self._put), ("PATCH", self._patch)):
            with self.subTest(name):
                Song.objects.filter(pk=self.song.pk).update(lyrics="元の歌詞")
                response = request(self.song.id, {"title": f"{name}で変更"})

                self.assertEqual(response.status_code, 200)
                song = Song.objects.get(pk=self.song.pk)
                self.assertEqual(song.title, f"{name}で変更")
                self.assertEqual(song.lyrics, "元の歌詞")
                self.assertEqual(song.category, "arrange")
                self.assertEqual([author.name for author in song.authors.all()], ["元の作者"])
                self.assertEqual(list(song.imitates.all()), [self.imitated])
                self.assertEqual(list(song.links.values_list("url", flat=True)), ["https://youtu.be/original001"])
                self.assertTrue(song.is_original)
                self.assertTrue(song.is_joke)
                self.assertTrue(song.is_inst)
                self.assertTrue(song.is_subeana)

    def test_patch_can_turn_off_a_flag(self):
        response = self._patch(self.song.id, {"is_original": False})

        self.assertEqual(response.status_code, 200)
        song = Song.objects.get(pk=self.song.pk)
        self.assertFalse(song.is_original)
        self.assertTrue(song.is_joke)

    def test_patch_is_questionable_clears_lyrics_and_imitates(self):
        """画面と同じく、is_questionableなら、歌詞・模倣元・オリジナル模倣は空にすること"""
        response = self._patch(self.song.id, {"is_questionable": True})

        self.assertEqual(response.status_code, 200)
        song = Song.objects.get(pk=self.song.pk)
        self.assertTrue(song.is_questionable)
        self.assertEqual(song.lyrics, "")
        self.assertFalse(song.is_original)
        self.assertEqual(song.imitates.count(), 0)

    def test_patch_without_body_keeps_song(self):
        response = self._patch(self.song.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Song.objects.get(pk=self.song.pk).title, "元の曲")
        self.assertEqual(History.objects.filter(song=self.song).count(), 0)

    def test_history_and_editor_are_recorded_as_in_the_form(self):
        self._patch(self.song.id, {"lyrics": "履歴の歌詞"}, HTTP_X_REAL_IP="203.0.113.8")

        history = History.objects.get(song=self.song)
        self.assertEqual(history.history_type, "edit")
        self.assertEqual(history.editor.ip, encrypt("203.0.113.8"))

    def test_decomposed_dakuten_is_normalized(self):
        decomposed_title = unicodedata.normalize("NFD", "がぱ")
        self.assertNotEqual(decomposed_title, "がぱ")
        self._patch(self.song.id, {"title": decomposed_title})

        self.assertEqual(Song.objects.get(pk=self.song.pk).title, "がぱ")

    def test_missing_authors_value_returns_400(self):
        response = self._patch(self.song.id, {"authors": ""})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "作者は空白にできません。"})
        self._assert_unchanged()

    def test_invalid_category_returns_400(self):
        response = self._patch(self.song.id, {"category": "invalid"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "カテゴリが不正です。"})
        self._assert_unchanged()

    def test_registered_url_returns_400(self):
        link = SongLink.objects.create(url="https://youtu.be/regist00003")
        link.songs.add(Song.objects.create(title="他の曲"))

        response = self._patch(self.song.id, {"url": "https://youtu.be/regist00003"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "URLは既に登録されています。"})
        self._assert_unchanged()

    def test_untrusted_url_error_is_plain_text(self):
        """編集の画面はエラーをHTML（お問い合わせへのリンク）で表示するため、APIはタグを除いた文章を返すこと"""
        response = self._patch(self.song.id, {"url": "https://example.com/video"})

        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertIn("https://example.com/video", error)
        self.assertIn("信頼されていないURLと判断されました。", error)
        self.assertNotIn("<", error)
        self.assertNotIn("&", error)
        self._assert_unchanged()

    def test_reject_list_error_is_unescaped(self):
        """編集の画面はエラーをエスケープしたHTMLで表示するため、APIはエスケープを元に戻した文字列を返すこと"""
        with patch("subekashi.views.song_edit.check_reject_list", return_value="<b>拒否</b>さんの曲は登録することができません。"):
            response = self._patch(self.song.id, {"authors": "拒否"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "<b>拒否</b>さんの曲は登録することができません。"})
        self._assert_unchanged()

    def test_invalid_flag_returns_400(self):
        response = self._patch(self.song.id, {"is_joke": 1})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "is_jokeは真偽値で指定してください。"})
        self._assert_unchanged()

    def test_non_object_body_returns_400(self):
        response = self._patch(self.song.id, ["title"])

        self.assertEqual(response.status_code, 400)
        self._assert_unchanged()

    def test_locked_song_returns_403(self):
        Song.objects.filter(pk=self.song.pk).update(is_lock=True)

        response = self._patch(self.song.id, {"title": "ロックされた曲の変更"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": LOCK_ERROR})
        self.assertEqual(Song.objects.get(pk=self.song.pk).title, "元の曲")

    def test_nonexistent_song_returns_404(self):
        for song_id in ("99999", "abc", "9" * 30):
            with self.subTest(song_id):
                response = self._request("patch", f"/api/song/{song_id}/", {"title": "x"})

                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"error": NOT_FOUND_ERROR})

    def test_removed_song_returns_410(self):
        Song.objects.filter(pk=self.song.pk).update(is_removed=True)

        response = self._patch(self.song.id, {"title": "削除された曲の変更"})

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json(), {"error": REMOVED_ERROR})
        self.assertEqual(Song.all_objects.get(pk=self.song.pk).title, "元の曲")

    def test_discord_failure_returns_500(self):
        self.discord["song_edit"].return_value = False

        response = self._patch(self.song.id, {"lyrics": "通知に失敗する変更"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": SERVER_ERROR})


class SongDeleteAPITest(SongWriteAPITestCase):
    """DELETE /api/song/<id>/ のテスト。SongDeleteView (/songs/<id>/delete/) のPOSTに対応する"""

    def setUp(self):
        super().setUp()
        self.song = Song.objects.create(title="削除される曲", lyrics="歌詞")
        self.song.authors.set([Author.objects.create(name="削除される曲の作者")])

    def test_delete_removes_song(self):
        response = self._delete(self.song.id, {"reason": "APIから削除"}, HTTP_X_REAL_IP="203.0.113.9")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Song.objects.filter(pk=self.song.pk).exists())
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)
        history = History.objects.get(song=self.song)
        self.assertEqual(history.history_type, "delete")
        self.assertEqual(history.changes, ["理由", "APIから削除"])
        self.assertEqual(history.editor.ip, encrypt("203.0.113.9"))
        self.discord["song_delete"].assert_called_once()

    def test_deleted_song_is_not_returned_by_get(self):
        self._delete(self.song.id, {"reason": "APIから削除"})

        self.assertEqual(self.client.get(f"/api/song/{self.song.id}/").status_code, 404)

    def test_missing_reason_returns_400(self):
        for data in (None, {}, {"reason": ""}):
            with self.subTest(data):
                response = self._delete(self.song.id, data)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"error": "削除理由を入力してください。"})
                self.assertTrue(Song.objects.filter(pk=self.song.pk).exists())
        self.assertEqual(History.objects.count(), 0)

    def test_locked_song_returns_403(self):
        Song.objects.filter(pk=self.song.pk).update(is_lock=True)

        response = self._delete(self.song.id, {"reason": "ロックされた曲の削除"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": LOCK_ERROR})
        self.assertTrue(Song.objects.filter(pk=self.song.pk).exists())

    def test_nonexistent_song_returns_404(self):
        for song_id in ("99999", "abc", "9" * 30):
            with self.subTest(song_id):
                response = self._request("delete", f"/api/song/{song_id}/", {"reason": "x"})

                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"error": NOT_FOUND_ERROR})

    def test_already_removed_song_returns_410(self):
        self.assertEqual(self._delete(self.song.id, {"reason": "1回目"}).status_code, 204)

        response = self._delete(self.song.id, {"reason": "2回目"})

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json(), {"error": REMOVED_ERROR})
        self.assertEqual(History.objects.filter(song=self.song).count(), 1)

    def test_discord_failure_still_deletes_song(self):
        """画面と同じく、通知に失敗しても曲は削除されているため、削除できたものとして扱うこと"""
        self.discord["song_delete"].return_value = False

        response = self._delete(self.song.id, {"reason": "通知に失敗する削除"})

        self.assertEqual(response.status_code, 204)
        self.assertTrue(Song.all_objects.get(pk=self.song.pk).is_removed)


class SongWriteAPIFlowTest(SongWriteAPITestCase):
    """APIで登録・変更・削除した曲が、画面と公開APIに反映される流れのテスト"""

    def test_song_created_updated_and_deleted_by_api_is_reflected_on_pages(self):
        created = self._post({"title": "流れの曲", "authors": "流れの作者", "lyrics": "無視される"})
        self.assertEqual(created.status_code, 201)
        song_id = created.json()["id"]

        self.assertContains(self.client.get(f"/songs/{song_id}/"), "流れの曲")
        detail = self.client.get(f"/api/song/{song_id}/").json()
        self.assertEqual(detail["title"], "流れの曲")
        self.assertEqual(detail["lyrics"], "")

        updated = self._patch(song_id, {"title": "変更後の流れの曲", "lyrics": "流れの歌詞"})
        self.assertEqual(updated.status_code, 200)
        detail = self.client.get(f"/api/song/{song_id}/").json()
        self.assertEqual(detail["title"], "変更後の流れの曲")
        self.assertEqual(detail["lyrics"], "流れの歌詞")
        self.assertEqual([author["name"] for author in detail["authors"]], ["流れの作者"])

        deleted = self._delete(song_id, {"reason": "流れの削除"})
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/api/song/{song_id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/songs/{song_id}/").status_code, 410)

        histories = History.objects.filter(song_id=song_id).order_by("id")
        self.assertEqual([history.history_type for history in histories], ["new", "edit", "delete"])
        self.assertEqual(len({history.editor_id for history in histories}), 1)
