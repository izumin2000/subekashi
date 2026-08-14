"""
モデルの基本動作テスト

Song, Author, AuthorAlias, SongLink の CRUD・制約・メソッドを検証する。
"""
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from subekashi.models import Author, AuthorAlias, Contact, Editor, History, Song, SongLink
from subekashi.models.author import EffectiveAlias, TransitiveAlias


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

    def test_default_alias_type_is_another(self):
        alias = AuthorAlias.objects.create(name="デフォルト別名", author=self.author)
        self.assertEqual(alias.alias_type, "another")

    def test_group_is_valid_alias_type_choice(self):
        # #1004で追加。合作アカウント等を表す種別
        self.assertIn("group", dict(AuthorAlias.CHOICES))
        alias = AuthorAlias.objects.create(name="グループ別名", author=self.author, alias_type="group")
        self.assertEqual(alias.alias_type, "group")


class AuthorEffectiveAliasesTest(TestCase):
    """Author.get_effective_aliases() の双方向解決ロジックのテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="foo")

    def test_no_aliases_returns_empty_list(self):
        self.assertEqual(self.author.get_effective_aliases(), [])

    def test_forward_alias_when_target_author_not_exist(self):
        # 別名の対象となる名前のauthorがまだ存在しない場合は正方向のみ
        alias = AuthorAlias.objects.create(name="foo_sub", author=self.author, alias_type="past")

        effective = self.author.get_effective_aliases()

        self.assertEqual(len(effective), 1)
        self.assertEqual(effective[0].name, "foo_sub")
        self.assertEqual(effective[0].alias_type, "past")
        self.assertEqual(effective[0].source, alias)
        self.assertFalse(effective[0].is_reverse)

    def test_becomes_bidirectional_when_target_author_registered(self):
        # 単方向のaliasを登録した後にnameが一致するauthorを登録すると双方向になる
        alias = AuthorAlias.objects.create(name="foo_sub", author=self.author, alias_type="past")
        foo_sub = Author.objects.create(name="foo_sub")

        # fooからは正方向のfoo_subが見える
        foo_effective = self.author.get_effective_aliases()
        self.assertEqual(len(foo_effective), 1)
        self.assertEqual(foo_effective[0].name, "foo_sub")
        self.assertFalse(foo_effective[0].is_reverse)

        # foo_subからは逆方向のfooが見える
        foo_sub_effective = foo_sub.get_effective_aliases()
        self.assertEqual(len(foo_sub_effective), 1)
        self.assertEqual(foo_sub_effective[0].name, "foo")
        self.assertEqual(foo_sub_effective[0].alias_type, "past")
        self.assertEqual(foo_sub_effective[0].source, alias)
        self.assertTrue(foo_sub_effective[0].is_reverse)

    def test_mixes_forward_and_reverse_aliases(self):
        # foo自身に登録された別名(正方向) + 他authorがfooをnameに持つ別名(逆方向)を両方含む
        AuthorAlias.objects.create(name="foo_forward", author=self.author, alias_type="spell")
        other_author = Author.objects.create(name="bar")
        AuthorAlias.objects.create(name="foo", author=other_author, alias_type="sns")

        effective = self.author.get_effective_aliases()
        names = {(e.name, e.is_reverse) for e in effective}

        self.assertEqual(len(effective), 2)
        self.assertIn(("foo_forward", False), names)
        self.assertIn(("bar", True), names)

    def test_reverse_excludes_own_aliases(self):
        # 自分自身が持つAuthorAliasのnameが自分自身のname("foo")と一致する場合、
        # exclude(author=self)がないと逆方向クエリにも同じaliasがヒットし二重計上されてしまう
        AuthorAlias.objects.create(name="foo", author=self.author, alias_type="spell")

        effective = self.author.get_effective_aliases()

        self.assertEqual(len(effective), 1)
        self.assertFalse(effective[0].is_reverse)

    def test_alias_type_display_returns_human_readable_label(self):
        AuthorAlias.objects.create(name="foo_past", author=self.author, alias_type="past")

        effective = self.author.get_effective_aliases()

        self.assertEqual(effective[0].alias_type_display, "以前の名称")

    def test_alias_type_display_falls_back_to_raw_value_for_unknown_type(self):
        # CHOICESにない値が入るケース（DBレベルではchoicesは強制されないため起こりうる）でも例外を出さない
        alias = AuthorAlias.objects.create(name="foo_unknown", author=self.author, alias_type="past")
        effective_alias = EffectiveAlias(name="foo_unknown", alias_type="unknown_type", source=alias)

        self.assertEqual(effective_alias.alias_type_display, "unknown_type")


class AuthorTransitiveAliasesTest(TestCase):
    """Author.get_transitive_aliases() の推移的関係解決ロジックのテスト（#1005）

    #1003で確認された具体例（名義Aに別名義B・以前の名称C・以前の名称D・グループEを登録）を
    そのまま再現し、各起点からの見え方が仕様表の通りになることを確認する。
    """

    def setUp(self):
        self.a = Author.objects.create(name="author_a")
        self.b = Author.objects.create(name="author_b")
        self.c = Author.objects.create(name="author_c")
        self.d = Author.objects.create(name="author_d")
        self.e = Author.objects.create(name="author_e")
        AuthorAlias.objects.create(name="author_b", author=self.a, alias_type="another")
        AuthorAlias.objects.create(name="author_c", author=self.a, alias_type="past")
        AuthorAlias.objects.create(name="author_d", author=self.a, alias_type="past")
        AuthorAlias.objects.create(name="author_e", author=self.a, alias_type="group")

    def as_tuples(self, transitive_aliases):
        return {(t.name, t.alias_type_display, t.is_direct, t.is_reverse) for t in transitive_aliases}

    def test_no_aliases_returns_empty_list(self):
        lone = Author.objects.create(name="lone")
        self.assertEqual(lone.get_transitive_aliases(), [])

    def test_author_a_sees_all_four_directly(self):
        result = self.as_tuples(self.a.get_transitive_aliases())
        self.assertEqual(result, {
            ("author_b", "別名義", True, False),
            ("author_c", "以前の名称", True, False),
            ("author_d", "以前の名称", True, False),
            ("author_e", "所属グループ", True, False),
        })

    def test_author_b_sees_only_a_another_does_not_bridge(self):
        result = self.as_tuples(self.b.get_transitive_aliases())
        self.assertEqual(result, {
            ("author_a", "別名義", True, True),
        })

    def test_author_c_sees_a_and_transitively_b_d_e_via_past(self):
        result = self.as_tuples(self.c.get_transitive_aliases())
        self.assertEqual(result, {
            ("author_a", "その後の名称", True, True),
            ("author_b", "別名義", False, False),
            ("author_d", "以前の名称", False, False),
            ("author_e", "所属グループ", False, False),
        })

    def test_author_d_sees_a_and_transitively_b_c_e_via_past(self):
        result = self.as_tuples(self.d.get_transitive_aliases())
        self.assertEqual(result, {
            ("author_a", "その後の名称", True, True),
            ("author_b", "別名義", False, False),
            ("author_c", "以前の名称", False, False),
            ("author_e", "所属グループ", False, False),
        })

    def test_author_e_sees_only_a_group_does_not_bridge(self):
        result = self.as_tuples(self.e.get_transitive_aliases())
        self.assertEqual(result, {
            ("author_a", "所属している名義", True, True),
        })

    def test_cycle_terminates_without_duplicates(self):
        x = Author.objects.create(name="cycle_x")
        y = Author.objects.create(name="cycle_y")
        AuthorAlias.objects.create(name="cycle_y", author=x, alias_type="spell")
        AuthorAlias.objects.create(name="cycle_x", author=y, alias_type="spell")

        result = x.get_transitive_aliases()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "cycle_y")
        self.assertEqual(result[0].alias_type, "spell")

    def test_alias_type_display_falls_back_to_raw_value_for_unknown_type(self):
        alias = AuthorAlias.objects.create(name="foo_unknown", author=self.a, alias_type="past")
        transitive_alias = TransitiveAlias(name="foo_unknown", alias_type="unknown_type", source=alias)

        self.assertEqual(transitive_alias.alias_type_display, "unknown_type")

    def test_alias_type_display_past_forward_stays_zenno_no_meisho(self):
        # #1019: 正方向（自分がpastの別名を登録している側）は従来通り「以前の名称」のまま
        alias = AuthorAlias.objects.create(name="foo_past_forward", author=self.a, alias_type="past")
        transitive_alias = TransitiveAlias(name="foo_past_forward", alias_type="past", source=alias, is_reverse=False)

        self.assertEqual(transitive_alias.alias_type_display, "以前の名称")

    def test_alias_type_display_past_reverse_shows_sonogo_no_meisho(self):
        # #1019: 逆方向（相手が自分をpastの別名として登録している側）は「その後の名称」と表示する
        alias = AuthorAlias.objects.create(name="foo_past_reverse", author=self.a, alias_type="past")
        transitive_alias = TransitiveAlias(name="foo_past_reverse", alias_type="past", source=alias, is_reverse=True)

        self.assertEqual(transitive_alias.alias_type_display, "その後の名称")


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
        self.assertFalse(song.is_questionable)

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


class ContactModelTest(TestCase):
    """Contact モデルのテスト"""

    def test_create_contact_creates_record(self):
        contact = Contact.create_contact("テスト問い合わせ内容")
        self.assertIsNotNone(contact.pk)
        self.assertEqual(contact.detail, "テスト問い合わせ内容")

    def test_create_contact_sets_post_time_to_today(self):
        contact = Contact.create_contact("テスト問い合わせ内容")
        self.assertEqual(contact.post_time, timezone.localdate())

    def test_create_contact_answer_is_empty(self):
        contact = Contact.create_contact("テスト問い合わせ内容")
        self.assertFalse(contact.answer)

    def test_get_answered_excludes_unanswered(self):
        Contact.objects.create(detail="未回答", post_time=timezone.localdate())
        result = Contact.get_answered()
        self.assertEqual(list(result), [])

    def test_get_answered_includes_answered(self):
        contact = Contact.objects.create(
            detail="回答済み", post_time=timezone.localdate(), answer="回答内容"
        )
        result = Contact.get_answered()
        self.assertIn(contact, result)

    def test_get_answered_orders_by_id_desc(self):
        first = Contact.objects.create(
            detail="1件目", post_time=timezone.localdate(), answer="回答1"
        )
        second = Contact.objects.create(
            detail="2件目", post_time=timezone.localdate(), answer="回答2"
        )
        result = list(Contact.get_answered())
        self.assertEqual(result, [second, first])


class HistoryModelTest(TestCase):
    """History モデルのテスト（author向け拡張分）"""

    def setUp(self):
        self.editor = Editor.objects.create(ip="127.0.0.1")
        self.author = Author.objects.create(name="履歴テスト作者")
        self.song = Song.objects.create(title="履歴テスト曲")

    def test_create_for_author_sets_author_and_leaves_song_null(self):
        history = History.create_for_author(
            author=self.author,
            title="別名を追加",
            history_type="edit",
            changes=[["変更前", "変更後"], ["", "別名A"]],
            editor=self.editor,
        )
        self.assertEqual(history.author, self.author)
        self.assertIsNone(history.song)
        self.assertEqual(history.history_type, "edit")

    def test_create_for_song_leaves_author_null(self):
        history = History.create_for_song(
            song=self.song,
            title="曲を編集",
            history_type="edit",
            changes=[["変更前", "変更後"], ["旧タイトル", "新タイトル"]],
            editor=self.editor,
        )
        self.assertEqual(history.song, self.song)
        self.assertIsNone(history.author)

    def test_author_set_null_on_author_delete(self):
        history = History.create_for_author(
            author=self.author,
            title="作者削除テスト",
            history_type="delete",
            changes=["理由", "テスト"],
            editor=self.editor,
        )
        self.author.delete()
        history.refresh_from_db()
        self.assertIsNone(history.author)

    def test_get_for_author_returns_only_matching_author_histories(self):
        other_author = Author.objects.create(name="別の作者")
        target_history = History.create_for_author(
            author=self.author, title="対象", history_type="edit", changes=None, editor=self.editor,
        )
        History.create_for_author(
            author=other_author, title="対象外", history_type="edit", changes=None, editor=self.editor,
        )

        results = list(History.get_for_author(self.author))

        self.assertEqual(results, [target_history])

    def test_get_for_author_orders_by_create_time_desc(self):
        older = History.create_for_author(
            author=self.author, title="古い", history_type="edit", changes=None, editor=self.editor,
        )
        older.create_time = timezone.now() - timezone.timedelta(days=1)
        older.save()
        newer = History.create_for_author(
            author=self.author, title="新しい", history_type="edit", changes=None, editor=self.editor,
        )

        results = list(History.get_for_author(self.author))

        self.assertEqual(results, [newer, older])
