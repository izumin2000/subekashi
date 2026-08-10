"""
song_card テンプレートタグのテスト

get_author(): 作者0人・1人・2人以上（合作）の表示分岐を検証する。
SEND_DISCORD=False のためDiscordへの実送信は発生しない。
"""
from django.test import TestCase
from django.urls import reverse

from subekashi.models import Author, Song
from subekashi.templatetags.song_card import get_author


class GetAuthorTest(TestCase):
    """get_author() のテスト"""

    def test_no_author_returns_unknown_author(self):
        song = Song.objects.create(title="作者不明曲")
        result = get_author(song)
        self.assertIn("作者不明", result)

    def test_single_author_returns_author_link(self):
        song = Song.objects.create(title="作者ありの曲")
        author = Author.objects.create(name="テスト作者")
        song.authors.add(author)
        result = get_author(song)
        self.assertIn("テスト作者", result)
        self.assertIn(reverse("subekashi:author", args=[author.id]), result)

    def test_two_authors_returns_collaboration(self):
        song = Song.objects.create(title="合作曲")
        song.authors.add(
            Author.objects.create(name="作者A"),
            Author.objects.create(name="作者B"),
        )
        result = get_author(song)
        self.assertIn("合作", result)

    def test_author_name_html_is_escaped(self):
        song = Song.objects.create(title="特殊文字作者の曲")
        author = Author.objects.create(name="<script>")
        song.authors.add(author)
        result = get_author(song)
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)
