"""
モデルの基本動作テスト

Song, Author, AuthorAlias, SongLink の CRUD・制約・メソッドを検証する。
"""
from django.db import IntegrityError
from django.test import TestCase
from subekashi.models import Author, AuthorAlias, Song, SongLink


class AuthorModelTest(TestCase):
    """Author モデルのテスト"""

    def test_create_author(self):
        author = Author.objects.create(name="テスト作者")
        self.assertEqual(author.name, "テスト作者")
        self.assertIsNotNone(author.pk)

    def test_str_returns_name(self):
        author = Author.objects.create(name="テスト作者")
        self.assertEqual(str(author), "テスト作者")

    def test_name_unique_constraint(self):
        Author.objects.create(name="重複作者")
        with self.assertRaises(IntegrityError):
            Author.objects.create(name="重複作者")

    def test_get_by_name_existing(self):
        Author.objects.create(name="検索対象作者")
        author = Author.get_by_name("検索対象作者")
        self.assertIsNotNone(author)
        self.assertEqual(author.name, "検索対象作者")

    def test_get_by_name_nonexistent_returns_none(self):
        result = Author.get_by_name("存在しない作者")
        self.assertIsNone(result)


class AuthorAliasModelTest(TestCase):
    """AuthorAlias モデルのテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="エイリアステスト作者")

    def test_create_alias(self):
        alias = AuthorAlias.objects.create(
            name="別名A",
            author=self.author,
            alias_type="abbr",
        )
        self.assertEqual(alias.name, "別名A")
        self.assertEqual(alias.author, self.author)

    def test_str_returns_name(self):
        alias = AuthorAlias.objects.create(name="別名B", author=self.author)
        self.assertEqual(str(alias), "別名B")

    def test_name_unique_constraint(self):
        AuthorAlias.objects.create(name="重複別名", author=self.author)
        author2 = Author.objects.create(name="別の作者")
        with self.assertRaises(IntegrityError):
            AuthorAlias.objects.create(name="重複別名", author=author2)

    def test_cascade_delete_with_author(self):
        AuthorAlias.objects.create(name="削除テスト別名", author=self.author)
        self.author.delete()
        self.assertEqual(AuthorAlias.objects.filter(name="削除テスト別名").count(), 0)

    def test_default_alias_type_is_other(self):
        alias = AuthorAlias.objects.create(name="デフォルト別名", author=self.author)
        self.assertEqual(alias.alias_type, "other")


class SongModelTest(TestCase):
    """Song モデルのテスト"""

    def setUp(self):
        self.author1 = Author.objects.create(name="曲テスト作者1")
        self.author2 = Author.objects.create(name="曲テスト作者2")

    def test_create_song(self):
        song = Song.objects.create(title="テスト曲")
        self.assertEqual(song.title, "テスト曲")
        self.assertIsNotNone(song.pk)

    def test_str_returns_title(self):
        song = Song.objects.create(title="タイトルテスト")
        self.assertEqual(str(song), "タイトルテスト")

    def test_default_flags(self):
        song = Song.objects.create(title="デフォルトフラグ曲")
        self.assertFalse(song.is_original)
        self.assertFalse(song.is_joke)
        self.assertFalse(song.is_deleted)
        self.assertFalse(song.is_draft)
        self.assertFalse(song.is_inst)
        self.assertTrue(song.is_subeana)

    def test_add_single_author(self):
        song = Song.objects.create(title="単一作者曲")
        song.authors.add(self.author1)
        self.assertEqual(song.authors.count(), 1)

    def test_add_multiple_authors(self):
        song = Song.objects.create(title="合作曲")
        song.authors.add(self.author1, self.author2)
        self.assertEqual(song.authors.count(), 2)

    def test_authors_str_single_author(self):
        song = Song.objects.create(title="単一作者曲")
        song.authors.add(self.author1)
        result = song.authors_str()
        self.assertEqual(result, "曲テスト作者1")

    def test_authors_str_multiple_authors(self):
        song = Song.objects.create(title="合作曲")
        song.authors.add(self.author1, self.author2)
        result = song.authors_str()
        self.assertIn("曲テスト作者1", result)
        self.assertIn("曲テスト作者2", result)

    def test_authors_str_no_authors(self):
        song = Song.objects.create(title="作者なし曲")
        self.assertEqual(song.authors_str(), "")

    def test_authors_str_custom_separator(self):
        song = Song.objects.create(title="セパレータテスト曲")
        song.authors.add(self.author1, self.author2)
        result = song.authors_str(separator=" / ")
        self.assertIn(" / ", result)

    def test_lyrics_crlf_normalized_to_lf_on_save(self):
        song = Song.objects.create(title="改行テスト曲", lyrics="行1\r\n行2\r\n行3")
        song.refresh_from_db()
        self.assertNotIn("\r\n", song.lyrics)
        self.assertIn("行1\n行2\n行3", song.lyrics)

    def test_imitates_self_reference(self):
        song1 = Song.objects.create(title="模倣元曲")
        song2 = Song.objects.create(title="模倣曲")
        song2.imitates.add(song1)
        self.assertIn(song1, song2.imitates.all())

    def test_imitates_reverse_relation(self):
        song1 = Song.objects.create(title="模倣元曲")
        song2 = Song.objects.create(title="模倣曲")
        song2.imitates.add(song1)
        self.assertIn(song2, song1.imitateds.all())

    def test_get_for_author(self):
        song1 = Song.objects.create(title="作者A曲1")
        song2 = Song.objects.create(title="作者A曲2")
        other_song = Song.objects.create(title="他作者の曲")
        song1.authors.add(self.author1)
        song2.authors.add(self.author1)
        other_song.authors.add(self.author2)

        qs = Song.get_for_author(self.author1.id)
        self.assertIn(song1, qs)
        self.assertIn(song2, qs)
        self.assertNotIn(other_song, qs)

    def test_get_for_range_subeana(self):
        subeana_song = Song.objects.create(title="すべあな曲", is_subeana=True)
        other_song = Song.objects.create(title="非すべあな曲", is_subeana=False)
        qs = Song.get_for_range("subeana", "all")
        self.assertIn(subeana_song, qs)
        self.assertNotIn(other_song, qs)

    def test_get_for_range_joke_off(self):
        normal_song = Song.objects.create(title="通常曲", is_joke=False)
        joke_song = Song.objects.create(title="ネタ曲", is_joke=True)
        qs = Song.get_for_range("all", "off")
        self.assertIn(normal_song, qs)
        self.assertNotIn(joke_song, qs)


class SongLinkModelTest(TestCase):
    """SongLink モデルのテスト"""

    def setUp(self):
        self.song = Song.objects.create(title="リンクテスト曲")

    def test_create_song_link(self):
        link = SongLink.objects.create(url="https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(link.url, "https://youtu.be/dQw4w9WgXcQ")
        self.assertIsNotNone(link.pk)

    def test_str_returns_url(self):
        link = SongLink.objects.create(url="https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(str(link), "https://youtu.be/dQw4w9WgXcQ")

    def test_url_unique_constraint(self):
        SongLink.objects.create(url="https://youtu.be/aaaaaaaaaaa")
        with self.assertRaises(IntegrityError):
            SongLink.objects.create(url="https://youtu.be/aaaaaaaaaaa")

    def test_add_song_to_link(self):
        link = SongLink.objects.create(url="https://youtu.be/bbbbbbbbbbb")
        link.songs.add(self.song)
        self.assertIn(self.song, link.songs.all())

    def test_link_accessible_from_song(self):
        link = SongLink.objects.create(url="https://youtu.be/ccccccccccc")
        link.songs.add(self.song)
        self.assertIn(link, self.song.links.all())

    def test_default_allow_dup_is_false(self):
        link = SongLink.objects.create(url="https://youtu.be/ddddddddddd")
        self.assertFalse(link.allow_dup)

    def test_set_allow_dup_for_url(self):
        SongLink.objects.create(url="https://youtu.be/eeeeeeeeeee")
        result = SongLink.set_allow_dup_for_url("https://youtu.be/eeeeeeeeeee")
        self.assertIsNotNone(result)
        self.assertTrue(result.allow_dup)

    def test_set_allow_dup_for_nonexistent_url_returns_none(self):
        result = SongLink.set_allow_dup_for_url("https://youtu.be/notexist1234")
        self.assertIsNone(result)
