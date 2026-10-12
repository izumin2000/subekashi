"""
song_card テンプレートタグのテスト

get_author(): 作者0人・1人・2人以上（合作）の表示分岐を検証する。
get_url(): 曲のフラグのアイコンと、URLのアイコン・URL未登録の表示分岐、両者の間の縦線を検証する。
SEND_DISCORD=False のためDiscordへの実送信は発生しない。
"""
from django.test import TestCase
from django.urls import reverse

from subekashi.models import Author, Song, SongLink
from subekashi.templatetags.song_card import get_author, get_url


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


class GetUrlTest(TestCase):
    """get_url() のテスト"""

    def _add_link(self, song, url="https://youtu.be/abcdefghijk"):
        link = SongLink.objects.create(url=url)
        link.songs.add(song)
        return link

    def test_no_link_returns_unregistered_link(self):
        song = Song.objects.create(title="URL未登録の曲")
        result = get_url(song)
        self.assertIn("URL未登録", result)
        self.assertIn(reverse("subekashi:song_edit", args=[song.id]), result)
        self.assertNotIn("title=", result)

    def test_link_returns_media_icon(self):
        song = Song.objects.create(title="URLありの曲")
        link = self._add_link(song)
        result = get_url(song)
        self.assertIn(f'href="{link.url}"', result)
        self.assertIn("fa-youtube", result)
        self.assertNotIn("URL未登録", result)

    def test_flag_icons(self):
        cases = [
            ({"is_questionable": True}, "fa-question", "界隈曲?"),
            ({"is_draft": True}, "fa-user-edit", "下書き"),
            ({"is_original": True}, "fa-external-link-alt", "オリジナル模倣"),
            ({"is_joke": True}, "fa-meh-rolling-eyes", "ネタ曲"),
            ({"is_inst": True}, "fa-comment-slash", "インスト曲"),
            ({"is_subeana": False}, "fa-fish", "非すべあな模倣曲"),
            ({"is_deleted": True}, "fa-eye-slash", "非公開/削除済み"),
            ({"is_special": True}, "fa-magic", "スペシャルデザイン"),
            ({"is_limited": True}, "fa-low-vision", "限定公開"),
        ]
        for fields, icon, label in cases:
            with self.subTest(fields=fields):
                song = Song.objects.create(title="フラグの曲", **fields)
                self._add_link(song, f"https://youtu.be/song{song.id:07d}")
                result = get_url(song)
                self.assertIn(icon, result)
                self.assertIn(f'title="{label}"', result)

    def test_no_flag_has_no_flag_icon(self):
        song = Song.objects.create(title="フラグなしの曲")
        self._add_link(song)
        result = get_url(song)
        self.assertNotIn("title=", result)

    def test_questionable_non_subeana_has_no_fish_icon(self):
        song = Song.objects.create(title="界隈曲?の曲", is_questionable=True, is_subeana=False)
        self._add_link(song)
        result = get_url(song)
        self.assertIn("fa-question", result)
        self.assertNotIn("fa-fish", result)

    def test_flag_icons_are_before_link_icons(self):
        song = Song.objects.create(title="複数フラグの曲", is_draft=True, is_limited=True)
        self._add_link(song)
        result = get_url(song)
        self.assertLess(result.index("fa-user-edit"), result.index("fa-low-vision"))
        self.assertLess(result.index("fa-low-vision"), result.index("fa-youtube"))

    def test_deleted_without_link_does_not_return_unregistered(self):
        song = Song.objects.create(title="非公開の曲", is_deleted=True)
        result = get_url(song)
        self.assertIn("fa-eye-slash", result)
        self.assertNotIn("URL未登録", result)

    def test_flag_without_link_returns_icon_and_unregistered(self):
        song = Song.objects.create(title="URL未登録の下書き", is_draft=True)
        result = get_url(song)
        self.assertIn("fa-user-edit", result)
        self.assertIn("URL未登録", result)
        self.assertLess(result.index("fa-user-edit"), result.index("URL未登録"))

    def test_separator_between_flag_and_link(self):
        song = Song.objects.create(title="下書きの曲", is_draft=True)
        self._add_link(song)
        result = get_url(song)
        self.assertEqual(result.count("song-card-separator"), 1)
        self.assertLess(result.index("fa-user-edit"), result.index("song-card-separator"))
        self.assertLess(result.index("song-card-separator"), result.index("fa-youtube"))

    def test_separator_between_flag_and_unregistered(self):
        song = Song.objects.create(title="URL未登録の下書き", is_draft=True)
        result = get_url(song)
        self.assertLess(result.index("song-card-separator"), result.index("URL未登録"))

    def test_no_separator_without_flag(self):
        song = Song.objects.create(title="フラグなしの曲")
        self._add_link(song)
        self.assertNotIn("song-card-separator", get_url(song))

    def test_no_separator_without_link(self):
        song = Song.objects.create(title="非公開でURLなしの曲", is_deleted=True)
        self.assertNotIn("song-card-separator", get_url(song))
