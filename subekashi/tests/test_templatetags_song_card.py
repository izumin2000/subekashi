"""
song_card テンプレートタグのテスト

get_author(): 作者0人・1人・2人以上（合作）の表示分岐を検証する。
get_url(): 曲のフラグのアイコンと、URLのアイコン・URL未登録の表示分岐、両者の間の縦線を検証する。
PC幅で隠すインスト曲のアイコンと、スマホ幅で三点リーダーにまとめるアイコンのクラスも検証する（#1229）。
get_lyrics(): 歌詞・インスト曲・歌詞未登録の表示分岐と、歌詞の登録が不要な曲に「歌詞未登録」を出さないことを検証する（#1253）。
is_subeana_author(): 全てあなたの所為です。の曲（合作を含む）の判定と、曲カードの背景色のクラスを検証する（#1219）。
SEND_DISCORD=False のためDiscordへの実送信は発生しない。
"""
from django.test import TestCase
from django.urls import reverse

from subekashi.constants.constants import SONG_CATEGORIES, SUBEANA_AUTHOR_ID
from subekashi.models import Author, Song, SongLink
from subekashi.templatetags.song_card import get_author, get_lyrics, get_url, is_subeana_author, render_song_card


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
            ({"is_questionable": True}, "fas fa-question", "界隈曲?"),
            ({"is_draft": True}, "fas fa-user-edit", "下書き"),
            ({"is_original": True}, "fas fa-external-link-alt", "オリジナル模倣"),
            ({"is_joke": True}, "far fa-meh-rolling-eyes", "ネタ曲"),
            ({"is_inst": True, "lyrics": "歌詞"}, "fas fa-comment-slash", "インスト曲"),
            ({"is_subeana": False}, "fas fa-fish", "非すべあな模倣曲"),
            ({"is_deleted": True}, "far fa-eye-slash", "非公開/削除済み"),
            ({"is_special": True}, "fas fa-magic", "スペシャルデザイン"),
            ({"is_limited": True}, "fas fa-low-vision", "限定公開"),
        ]
        for fields, icon, label in cases:
            with self.subTest(fields=fields):
                song = Song.objects.create(title="フラグの曲", **fields)
                self._add_link(song, f"https://youtu.be/song{song.id:07d}")
                result = get_url(song)
                self.assertIn(f'<i class="{icon}" title="{label}"></i>', result)
                self.assertEqual(result.count("title="), 1)

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

    def test_separator_between_deleted_and_link(self):
        song = Song.objects.create(title="非公開でURLありの曲", is_deleted=True)
        self._add_link(song)
        result = get_url(song)
        self.assertEqual(result.count("song-card-separator"), 1)
        self.assertLess(result.index("fa-eye-slash"), result.index("song-card-separator"))
        self.assertLess(result.index("song-card-separator"), result.index("fa-youtube"))
        self.assertNotIn("URL未登録", result)

    def test_separator_with_multiple_links(self):
        song = Song.objects.create(title="複数URLの下書き", is_draft=True)
        youtube = self._add_link(song)
        x = self._add_link(song, "https://x.com/subekashi/status/1")
        result = get_url(song)
        self.assertEqual(result.count("song-card-separator"), 1)
        self.assertLess(result.index("fa-user-edit"), result.index("song-card-separator"))
        self.assertLess(result.index("song-card-separator"), result.index(f'href="{youtube.url}"'))
        self.assertLess(result.index("song-card-separator"), result.index(f'href="{x.url}"'))

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

    def test_inst_icon_in_lyrics_is_sp_only(self):
        song = Song.objects.create(title="歌詞なしのインスト曲", is_inst=True, is_deleted=True)
        result = get_url(song)
        self.assertIn('<i class="fas fa-comment-slash song-card-sp-only" title="インスト曲"></i>', result)
        self.assertIn('<i class="far fa-eye-slash" title="非公開/削除済み"></i>', result)

    def test_questionable_inst_icon_is_not_sp_only(self):
        song = Song.objects.create(title="界隈曲?のインスト曲", is_inst=True, is_questionable=True)
        result = get_url(song)
        self.assertIn('<i class="fas fa-comment-slash" title="インスト曲"></i>', result)
        self.assertNotIn("song-card-sp-only", result)

    def test_separator_is_sp_only_when_only_inst_in_lyrics(self):
        song = Song.objects.create(title="歌詞なしのインスト曲", is_inst=True)
        self._add_link(song)
        result = get_url(song)
        self.assertIn('<span class="song-card-separator song-card-sp-only"></span>', result)

    def test_separator_is_shown_when_inst_in_lyrics_with_other_flag(self):
        song = Song.objects.create(title="歌詞なしのネタのインスト曲", is_joke=True, is_inst=True)
        self._add_link(song)
        result = get_url(song)
        self.assertIn('<span class="song-card-separator"></span>', result)

    def test_two_flags_are_not_folded(self):
        song = Song.objects.create(title="フラグが2個の曲", is_draft=True, is_limited=True)
        self._add_link(song)
        result = get_url(song)
        self.assertIn('<i class="fas fa-user-edit" title="下書き"></i>', result)
        self.assertIn('<i class="fas fa-low-vision" title="限定公開"></i>', result)
        self.assertNotIn("fa-ellipsis-h", result)
        self.assertNotIn("song-card-pc-only", result)

    def test_three_flags_are_folded_on_sp(self):
        song = Song.objects.create(title="フラグが3個の曲", is_draft=True, is_joke=True, is_limited=True)
        self._add_link(song)
        result = get_url(song)
        self.assertIn('<i class="fas fa-user-edit" title="下書き"></i>', result)
        self.assertIn('<i class="far fa-meh-rolling-eyes song-card-pc-only" title="ネタ曲"></i>', result)
        self.assertIn('<i class="fas fa-low-vision song-card-pc-only" title="限定公開"></i>', result)
        self.assertIn('<i class="fas fa-ellipsis-h song-card-sp-only" title="ネタ曲・限定公開"></i>', result)
        self.assertLess(result.index("fa-low-vision"), result.index("fa-ellipsis-h"))
        self.assertLess(result.index("fa-ellipsis-h"), result.index('<span class="song-card-separator"></span>'))

    def test_four_flags_are_folded_on_sp(self):
        song = Song.objects.create(title="フラグが4個の曲", is_original=True, is_joke=True, is_deleted=True, is_subeana=False)
        self._add_link(song)
        result = get_url(song)
        self.assertIn('<i class="fas fa-external-link-alt" title="オリジナル模倣"></i>', result)
        self.assertIn('<i class="fas fa-ellipsis-h song-card-sp-only" title="ネタ曲・非すべあな模倣曲・非公開/削除済み"></i>', result)

    def test_folded_inst_icon_in_lyrics_is_not_rendered(self):
        song = Song.objects.create(title="歌詞なしの非公開のインスト曲", is_original=True, is_inst=True, is_deleted=True)
        self._add_link(song)
        result = get_url(song)
        self.assertIn('<i class="fas fa-external-link-alt" title="オリジナル模倣"></i>', result)
        self.assertNotIn("fa-comment-slash", result)
        self.assertIn('<i class="far fa-eye-slash song-card-pc-only" title="非公開/削除済み"></i>', result)
        self.assertIn('<i class="fas fa-ellipsis-h song-card-sp-only" title="インスト曲・非公開/削除済み"></i>', result)
        self.assertIn('<span class="song-card-separator"></span>', result)

    def test_folded_without_link_has_no_separator(self):
        song = Song.objects.create(title="URLなしの非公開の曲", is_original=True, is_joke=True, is_deleted=True)
        result = get_url(song)
        self.assertIn("fa-ellipsis-h", result)
        self.assertNotIn("song-card-separator", result)
        self.assertNotIn("URL未登録", result)


class GetLyricsTest(TestCase):
    """get_lyrics() のテスト"""

    def test_lyrics_returns_lyrics(self):
        song = Song.objects.create(title="歌詞ありの曲", lyrics="テスト歌詞")
        self.assertEqual(get_lyrics(song), '<i class="fas fa-align-center"></i>テスト歌詞')

    def test_lyrics_html_is_escaped(self):
        song = Song.objects.create(title="特殊文字の歌詞の曲", lyrics="<script>")
        result = get_lyrics(song)
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_inst_without_lyrics_returns_inst(self):
        song = Song.objects.create(title="歌詞なしのインスト曲", is_inst=True)
        self.assertEqual(get_lyrics(song), '<i class="fas fa-align-center"></i>インスト曲')

    def test_song_without_lyrics_returns_unregistered_link(self):
        song = Song.objects.create(title="歌詞未登録の曲")
        result = get_lyrics(song)
        self.assertIn("歌詞未登録", result)
        self.assertIn(reverse("subekashi:song_edit", args=[song.id]), result)

    def test_not_song_without_lyrics_returns_empty(self):
        for category in [category for category in SONG_CATEGORIES if category["value"] != "song"]:
            with self.subTest(category=category["value"]):
                song = Song.objects.create(title="歌詞なしの曲以外", category=category["value"])
                self.assertEqual(get_lyrics(song), "")

    def test_questionable_without_lyrics_returns_empty(self):
        song = Song.objects.create(title="歌詞なしの界隈曲?", is_questionable=True)
        self.assertEqual(get_lyrics(song), "")

    def test_not_song_with_lyrics_returns_lyrics(self):
        song = Song.objects.create(title="歌詞ありのカバー", category="cover", lyrics="テスト歌詞")
        self.assertEqual(get_lyrics(song), '<i class="fas fa-align-center"></i>テスト歌詞')

    def test_not_song_inst_without_lyrics_returns_inst(self):
        song = Song.objects.create(title="歌詞なしのインストのアレンジ", category="arrange", is_inst=True)
        self.assertEqual(get_lyrics(song), '<i class="fas fa-align-center"></i>インスト曲')

    def test_unregistered_only_if_lack_by_lyrics(self):
        # URLがあるオリジナル模倣の曲は、未完成かどうかが歌詞の条件だけで決まる
        for category in SONG_CATEGORIES:
            for is_questionable in [False, True]:
                with self.subTest(category=category["value"], is_questionable=is_questionable):
                    song = Song.objects.create(title="URLありで歌詞なしの曲", category=category["value"], is_original=True, is_questionable=is_questionable)
                    SongLink.objects.create(url=f"https://youtu.be/song{song.id:07d}").songs.add(song)
                    self.assertEqual("歌詞未登録" in get_lyrics(song), Song.is_lack(song.id))


class IsSubeanaAuthorTest(TestCase):
    """is_subeana_author() と曲カードの背景色のクラスのテスト（#1219）"""

    def setUp(self):
        self.subeana = Author.objects.create(pk=SUBEANA_AUTHOR_ID, name="全てあなたの所為です。")
        self.other = Author.objects.create(name="テスト作者")

    def _create_song(self, *authors):
        song = Song.objects.create(title="テスト曲")
        song.authors.add(*authors)
        return song

    def test_subeana_author(self):
        self.assertTrue(is_subeana_author(self._create_song(self.subeana)))

    def test_collab_with_subeana_author(self):
        self.assertTrue(is_subeana_author(self._create_song(self.other, self.subeana)))

    def test_other_author(self):
        self.assertFalse(is_subeana_author(self._create_song(self.other)))

    def test_no_author(self):
        self.assertFalse(is_subeana_author(self._create_song()))

    def test_prefetched_authors_do_not_query(self):
        self._create_song(self.subeana)
        song = Song.objects.prefetch_related("authors").get()
        with self.assertNumQueries(0):
            self.assertTrue(is_subeana_author(song))

    def test_song_card_class(self):
        self.assertIn('class="song-card song-card-subeana-author"', render_song_card(self._create_song(self.subeana)))
        self.assertIn('class="song-card"', render_song_card(self._create_song(self.other)))
