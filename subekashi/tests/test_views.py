"""
ビューの HTTP レスポンステスト

各ページの基本的なアクセス可否・ステータスコード・リダイレクト先を検証する。
ManifestStaticFilesStorage はテストに不要なため StaticFilesStorage に差し替える。
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from subekashi.models import Author, Song


STATIC_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class TopViewTest(TestCase):
    """TopView (/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertEqual(response.status_code, 200)


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


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongNewViewTest(TestCase):
    """SongNewView (/songs/new/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_new"))
        self.assertEqual(response.status_code, 200)


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


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class HistoriesViewTest(TestCase):
    """HistoriesView (/histories/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:histories"))
        self.assertEqual(response.status_code, 200)


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
