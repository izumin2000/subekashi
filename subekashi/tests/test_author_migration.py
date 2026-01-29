"""
Author DB移行の機能テスト

このテストは、ChannelからAuthorへの移行が正常に完了し、
全ての機能が正しく動作することを確認します。
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from subekashi.models import Song, Author
from subekashi.lib.author_helpers import get_or_create_authors


class AuthorModelTest(TestCase):
    """Authorモデルのテスト"""

    def setUp(self):
        """テスト用のデータを準備"""
        self.author1 = Author.objects.create(name="テスト作者1")
        self.author2 = Author.objects.create(name="テスト作者2")

    def test_author_creation(self):
        """Authorオブジェクトが正しく作成されるか"""
        self.assertEqual(self.author1.name, "テスト作者1")
        self.assertEqual(Author.objects.count(), 2)

    def test_author_str_method(self):
        """Author.__str__()が正しく動作するか"""
        self.assertEqual(str(self.author1), "テスト作者1")


class SongAuthorRelationshipTest(TestCase):
    """SongとAuthorの関係のテスト"""

    def setUp(self):
        """テスト用のデータを準備"""
        self.author1 = Author.objects.create(name="テスト作者1")
        self.author2 = Author.objects.create(name="テスト作者2")
        self.song = Song.objects.create(
            title="テスト曲",
            lyrics="テスト歌詞"
        )

    def test_single_author_assignment(self):
        """単一作者の割り当て"""
        self.song.authors.add(self.author1)
        self.assertEqual(self.song.authors.count(), 1)
        self.assertEqual(self.song.authors.first(), self.author1)

    def test_multiple_authors_assignment(self):
        """複数作者（合作）の割り当て"""
        self.song.authors.add(self.author1, self.author2)
        self.assertEqual(self.song.authors.count(), 2)
        self.assertIn(self.author1, self.song.authors.all())
        self.assertIn(self.author2, self.song.authors.all())

    def test_authors_str_method(self):
        """Song.authors_str()メソッドのテスト"""
        self.song.authors.add(self.author1, self.author2)
        authors_str = self.song.authors_str()
        self.assertIn("テスト作者1", authors_str)
        self.assertIn("テスト作者2", authors_str)


class AuthorHelpersTest(TestCase):
    """author_helpersモジュールのテスト"""

    def test_get_or_create_authors_new(self):
        """新しいAuthorを作成"""
        author_names = ["新作者1", "新作者2"]
        authors = get_or_create_authors(author_names)

        self.assertEqual(len(authors), 2)
        self.assertEqual(Author.objects.count(), 2)
        self.assertEqual(authors[0].name, "新作者1")
        self.assertEqual(authors[1].name, "新作者2")

    def test_get_or_create_authors_existing(self):
        """既存のAuthorを取得"""
        Author.objects.create(name="既存作者")
        author_names = ["既存作者"]
        authors = get_or_create_authors(author_names)

        self.assertEqual(len(authors), 1)
        self.assertEqual(Author.objects.count(), 1)
        self.assertEqual(authors[0].name, "既存作者")

    def test_get_or_create_authors_empty_strings(self):
        """空文字列を含むリストの処理"""
        author_names = ["作者1", "", "作者2", ""]
        authors = get_or_create_authors(author_names)

        self.assertEqual(len(authors), 2)
        self.assertEqual(Author.objects.count(), 2)


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class AuthorViewTest(TestCase):
    """作者ページのビューテスト"""

    def setUp(self):
        """テスト用のデータを準備"""
        self.client = Client()
        self.author = Author.objects.create(name="テスト作者")
        self.song1 = Song.objects.create(title="曲1", lyrics="歌詞1")
        self.song2 = Song.objects.create(title="曲2", lyrics="歌詞2")
        self.song1.authors.add(self.author)
        self.song2.authors.add(self.author)

    def test_author_page_displays_songs(self):
        """作者ページで作者の曲一覧が表示されるか"""
        url = reverse('subekashi:author', args=[self.author.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "テスト作者")
        self.assertContains(response, "曲1")
        self.assertContains(response, "曲2")

    def test_author_page_404_for_invalid_id(self):
        """存在しないAuthor IDで404が返るか"""
        url = reverse('subekashi:author', args=[99999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class ChannelRedirectTest(TestCase):
    """後方互換性のためのリダイレクトテスト"""

    def setUp(self):
        """テスト用のデータを準備"""
        self.client = Client()
        self.author = Author.objects.create(name="リダイレクトテスト作者")

    def test_channel_redirects_to_author(self):
        """/channel/<name>/が/author/<id>/にリダイレクトされるか"""
        url = reverse('subekashi:channel', args=["リダイレクトテスト作者"])
        response = self.client.get(url)

        # リダイレクトが発生することを確認
        self.assertEqual(response.status_code, 302)

        # リダイレクト先が正しいか確認
        expected_url = reverse('subekashi:author', args=[self.author.id])
        self.assertRedirects(response, expected_url)

    def test_channel_404_for_nonexistent_author(self):
        """存在しない作者名で404が返るか"""
        url = reverse('subekashi:channel', args=["存在しない作者"])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class SongDisplayTest(TestCase):
    """曲表示ページのテスト"""

    def setUp(self):
        """テスト用のデータを準備"""
        self.client = Client()
        self.author1 = Author.objects.create(name="表示テスト作者1")
        self.author2 = Author.objects.create(name="表示テスト作者2")
        self.song_single = Song.objects.create(title="単一作者曲", lyrics="歌詞")
        self.song_multi = Song.objects.create(title="合作曲", lyrics="歌詞")
        self.song_single.authors.add(self.author1)
        self.song_multi.authors.add(self.author1, self.author2)

    def test_song_displays_single_author(self):
        """単一作者の曲で作者が表示されるか"""
        url = reverse('subekashi:song', args=[self.song_single.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "表示テスト作者1")

    def test_song_displays_multiple_authors(self):
        """複数作者（合作）の曲で全作者が表示されるか"""
        url = reverse('subekashi:song', args=[self.song_multi.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "表示テスト作者1")
        self.assertContains(response, "表示テスト作者2")
