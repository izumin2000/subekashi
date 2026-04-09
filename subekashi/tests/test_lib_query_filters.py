"""
lib/query_filters.py のテスト

楽曲検索フィルター関数の Q オブジェクト生成・適用結果を検証する。
"""
from django.test import TestCase
from subekashi.models import Author, Song, SongLink
from subekashi.lib.query_filters import (
    filter_by_keyword,
    filter_by_imitate,
    filter_by_imitated,
    filter_by_guesser,
    filter_by_lack,
    make_is_lack_annotation,
)


class FilterByKeywordTest(TestCase):
    """filter_by_keyword() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="キーワードテスト作者")
        self.song_by_title = Song.objects.create(title="テストタイトルキーワード")
        self.song_by_author = Song.objects.create(title="別タイトルの曲")
        self.song_by_author.authors.add(self.author)
        self.song_by_lyrics = Song.objects.create(title="歌詞検索曲", lyrics="テスト歌詞内容")
        self.song_by_url = Song.objects.create(title="URL検索曲")
        link = SongLink.objects.create(url="https://youtu.be/keyword12345")
        link.songs.add(self.song_by_url)
        self.unrelated_song = Song.objects.create(title="関係ない曲", lyrics="関係ない歌詞")

    def test_filter_by_title_match(self):
        qs = Song.objects.filter(filter_by_keyword("テストタイトル"))
        self.assertIn(self.song_by_title, qs)
        self.assertNotIn(self.unrelated_song, qs)

    def test_filter_by_author_name(self):
        qs = Song.objects.filter(filter_by_keyword("キーワードテスト作者")).distinct()
        self.assertIn(self.song_by_author, qs)

    def test_filter_by_lyrics(self):
        qs = Song.objects.filter(filter_by_keyword("テスト歌詞内容"))
        self.assertIn(self.song_by_lyrics, qs)

    def test_filter_by_url(self):
        qs = Song.objects.filter(filter_by_keyword("keyword12345")).distinct()
        self.assertIn(self.song_by_url, qs)

    def test_no_match_returns_empty(self):
        qs = Song.objects.filter(filter_by_keyword("存在しないキーワードXYZ999"))
        self.assertEqual(qs.count(), 0)


class FilterByImitateTest(TestCase):
    """filter_by_imitate() のテスト"""

    def setUp(self):
        self.original = Song.objects.create(title="模倣元曲")
        self.imitate = Song.objects.create(title="模倣曲")
        self.imitate.imitates.add(self.original)
        self.unrelated = Song.objects.create(title="関係ない曲")

    def test_filter_returns_songs_that_imitate_target(self):
        qs = Song.objects.filter(filter_by_imitate(self.original.id))
        self.assertIn(self.imitate, qs)
        self.assertNotIn(self.unrelated, qs)

    def test_filter_by_nonexistent_id_returns_empty(self):
        qs = Song.objects.filter(filter_by_imitate(99999))
        self.assertEqual(qs.count(), 0)


class FilterByImitatedTest(TestCase):
    """filter_by_imitated() のテスト"""

    def setUp(self):
        self.original = Song.objects.create(title="模倣元曲")
        self.imitate1 = Song.objects.create(title="模倣曲1")
        self.imitate2 = Song.objects.create(title="模倣曲2")
        self.imitate1.imitates.add(self.original)
        self.imitate2.imitates.add(self.original)
        self.unrelated = Song.objects.create(title="関係ない曲")

    def test_filter_returns_songs_imitated_by_target(self):
        qs = Song.objects.filter(filter_by_imitated(self.imitate1.id))
        self.assertIn(self.original, qs)
        self.assertNotIn(self.unrelated, qs)


class FilterByGuesserTest(TestCase):
    """filter_by_guesser() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="推測テスト作者")
        self.song_by_title = Song.objects.create(title="推測対象タイトル")
        self.song_by_author = Song.objects.create(title="別曲")
        self.song_by_author.authors.add(self.author)
        self.unrelated = Song.objects.create(title="関係ない曲")

    def test_filter_by_title(self):
        qs = Song.objects.filter(filter_by_guesser("推測対象")).distinct()
        self.assertIn(self.song_by_title, qs)

    def test_filter_by_author_name(self):
        qs = Song.objects.filter(filter_by_guesser("推測テスト作者")).distinct()
        self.assertIn(self.song_by_author, qs)


class FilterByLackTest(TestCase):
    """filter_by_lack() のテスト"""

    def test_song_without_url_and_not_deleted_is_lack(self):
        song = Song.objects.create(title="URLなし曲", is_deleted=False)
        qs = Song.objects.filter(filter_by_lack())
        self.assertIn(song, qs)

    def test_song_with_url_is_not_lack(self):
        # is_original=True にすると「すべあな模倣曲条件」に引っかからない
        song = Song.objects.create(title="URLあり曲", lyrics="歌詞あり", is_original=True)
        link = SongLink.objects.create(url="https://youtu.be/hasurlsong1")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertNotIn(song, qs)

    def test_song_without_lyrics_and_not_inst_is_lack(self):
        song = Song.objects.create(title="歌詞なし曲", is_inst=False, lyrics="")
        qs = Song.objects.filter(filter_by_lack())
        self.assertIn(song, qs)

    def test_inst_song_without_lyrics_is_not_lack(self):
        # is_original=True にすると「すべあな模倣曲条件」に引っかからない
        song = Song.objects.create(title="インスト曲", is_inst=True, lyrics="", is_original=True)
        link = SongLink.objects.create(url="https://youtu.be/instsong00001")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertNotIn(song, qs)

    def test_deleted_song_is_not_caught_by_url_check(self):
        # is_original=True にすると「すべあな模倣曲条件」に引っかからない
        song = Song.objects.create(title="削除済み曲", is_deleted=True, lyrics="歌詞あり", is_original=True)
        link = SongLink.objects.create(url="https://youtu.be/deletedsong1")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertNotIn(song, qs)


class MakeIsLackAnnotationTest(TestCase):
    """make_is_lack_annotation() のテスト"""

    def test_lack_song_annotated_true(self):
        song = Song.objects.create(title="未完成曲", is_inst=False, lyrics="")
        qs = Song.objects.annotate(is_lack=make_is_lack_annotation())
        annotated = qs.get(pk=song.pk)
        self.assertTrue(annotated.is_lack)

    def test_complete_song_annotated_false(self):
        # is_original=True にすると「すべあな模倣曲条件」に引っかからない
        song = Song.objects.create(title="完成曲", lyrics="歌詞あり", is_original=True)
        link = SongLink.objects.create(url="https://youtu.be/complete00001")
        link.songs.add(song)
        qs = Song.objects.annotate(is_lack=make_is_lack_annotation())
        annotated = qs.get(pk=song.pk)
        self.assertFalse(annotated.is_lack)
