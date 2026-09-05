"""
モデルの基本動作テスト

Song, Author, AuthorAlias, SongLink の CRUD・制約・メソッドを検証する。
"""
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from subekashi.models import Ai, Author, AuthorAlias, Contact, Editor, History, Song, SongLink, Stats, Word
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

    def test_different_case_names_can_coexist(self):
        """一意制約はバイト完全一致で判定され、大文字小文字違いは別レコードとして許容される（#1092）"""
        Author.objects.create(name="MoAI")
        Author.objects.create(name="moai")
        self.assertEqual(Author.objects.filter(name__in=["MoAI", "moai"]).count(), 2)

    def test_iexact_search_is_case_insensitive(self):
        """#1092: MySQL移行に伴う照合順序変更後も大文字小文字を区別しない検索ができること"""
        author = Author.objects.create(name="MoAI")
        self.assertEqual(Author.objects.filter(name__iexact="moai").first(), author)

    def test_icontains_search_is_case_insensitive(self):
        author = Author.objects.create(name="MoAI Project")
        self.assertIn(author, Author.objects.filter(name__icontains="moai"))

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

    def test_icontains_search_is_case_insensitive(self):
        """#1092: MySQL移行に伴う照合順序変更後も大文字小文字を区別しない検索ができること"""
        alias = AuthorAlias.objects.create(name="MoAI Alias", author=self.author)
        self.assertIn(alias, AuthorAlias.objects.filter(name__icontains="moai"))

    def test_name_unique_constraint(self):
        # unique_authoralias_name_except_groupは条件付きUniqueConstraint（部分インデックス）
        # のため、未サポートのMySQLでは0049マイグレーションの生成列ワークアラウンドで
        # 同等のDB制約を代替している（#593）
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

    def test_group_name_can_be_shared_by_multiple_authors(self):
        # alias_type="group"は、複数のauthorが同じ名前で登録できる（#1044）
        author2 = Author.objects.create(name="別の作者(group)")
        AuthorAlias.objects.create(name="合作グループ", author=self.author, alias_type="group")
        alias2 = AuthorAlias.objects.create(name="合作グループ", author=author2, alias_type="group")
        self.assertEqual(alias2.name, "合作グループ")
        self.assertEqual(AuthorAlias.objects.filter(name="合作グループ").count(), 2)

    def test_same_author_cannot_create_duplicate_group_name(self):
        # 同じauthorによる同じグループ名の重複作成はDB制約でも防がれる（#1044）
        # unique_authoralias_name_author_for_groupは条件付きUniqueConstraintのため、
        # 未サポートのMySQLでは0049マイグレーションの生成列ワークアラウンドで代替している（#593）
        AuthorAlias.objects.create(name="重複グループ", author=self.author, alias_type="group")
        with self.assertRaises(IntegrityError):
            AuthorAlias.objects.create(name="重複グループ", author=self.author, alias_type="group")

    def test_non_group_name_still_globally_unique(self):
        # group以外の種別は、DB制約レベルでも従来通りグローバルにユニークのまま（#1044）
        # unique_authoralias_name_except_groupは条件付きUniqueConstraintのため、
        # 未サポートのMySQLでは0049マイグレーションの生成列ワークアラウンドで代替している（#593）
        author2 = Author.objects.create(name="別の作者(非group)")
        AuthorAlias.objects.create(name="通常別名", author=self.author, alias_type="spell")
        with self.assertRaises(IntegrityError):
            AuthorAlias.objects.create(name="通常別名", author=author2, alias_type="spell")


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

    def test_author_id_resolves_for_reverse_and_bridging_forward_entries(self):
        # #1023: 逆方向、および正方向かつ中継可能な種別（past等）のエントリは、
        # get_transitive_aliases()自体が追加クエリなしに解決したauthor_idを持つ
        by_name = {t.name: t.author_id for t in self.a.get_transitive_aliases()}
        self.assertEqual(by_name["author_c"], self.c.id)
        self.assertEqual(by_name["author_d"], self.d.id)

        by_name = {t.name: t.author_id for t in self.c.get_transitive_aliases()}
        self.assertEqual(by_name["author_a"], self.a.id)
        self.assertEqual(by_name["author_d"], self.d.id)

        by_name = {t.name: t.author_id for t in self.b.get_transitive_aliases()}
        self.assertEqual(by_name["author_a"], self.a.id)

        by_name = {t.name: t.author_id for t in self.e.get_transitive_aliases()}
        self.assertEqual(by_name["author_a"], self.a.id)

    def test_author_id_is_none_for_non_bridging_forward_entries(self):
        # #1023: 正方向かつalias_typeがanother/group（中継不可）のエントリは、
        # get_transitive_aliases()内では解決されずauthor_idがNoneのままになる
        by_name = {t.name: t.author_id for t in self.a.get_transitive_aliases()}
        self.assertIsNone(by_name["author_b"])
        self.assertIsNone(by_name["author_e"])

        by_name = {t.name: t.author_id for t in self.c.get_transitive_aliases()}
        self.assertIsNone(by_name["author_b"])
        self.assertIsNone(by_name["author_e"])

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

    def test_group_name_shared_by_multiple_authors_each_see_only_their_own_entry(self):
        # #1044: 複数のauthorが同じグループ名を登録できるようになったが、groupは
        # 中継不可（NON_BRIDGING_ALIAS_TYPES）のため、あるauthorの一覧には自分自身が
        # 登録したグループ名のみが表示され、同じグループ名を登録した他authorの存在は
        # 見えない（グループメンバー一覧UIは#1044のスコープ外として意図的に対象外）
        group_x = Author.objects.create(name="group_member_x")
        group_y = Author.objects.create(name="group_member_y")
        AuthorAlias.objects.create(name="shared_group", author=group_x, alias_type="group")
        AuthorAlias.objects.create(name="shared_group", author=group_y, alias_type="group")

        result_x = self.as_tuples(group_x.get_transitive_aliases())
        self.assertEqual(result_x, {("shared_group", "所属グループ", True, False)})

        result_y = self.as_tuples(group_y.get_transitive_aliases())
        self.assertEqual(result_y, {("shared_group", "所属グループ", True, False)})

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

    def test_iexact_search_is_case_insensitive(self):
        """#1092: MySQL移行に伴う照合順序変更後も大文字小文字を区別しない検索ができること"""
        link = SongLink.objects.create(url="https://youtu.be/AbCdEfGhIjK")
        self.assertEqual(SongLink.objects.filter(url__iexact="https://youtu.be/abcdefghijk").first(), link)

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

    def test_create_for_song_truncates_long_title(self):
        # Song.title（max_length=500）を含む動的titleがHistory.title（max_length=100）を
        # 超えることがあるため、MySQL移行時にData too long for columnエラーにならないよう
        # 保存前に切り詰める（#1085）
        long_title = "あ" * 200
        history = History.create_for_song(
            song=self.song,
            title=long_title,
            history_type="new",
            changes=None,
            editor=self.editor,
        )
        self.assertEqual(len(history.title), 100)
        self.assertEqual(history.title, "あ" * 100)

    def test_create_for_author_truncates_long_title(self):
        long_title = "い" * 200
        history = History.create_for_author(
            author=self.author,
            title=long_title,
            history_type="edit",
            changes=None,
            editor=self.editor,
        )
        self.assertEqual(len(history.title), 100)
        self.assertEqual(history.title, "い" * 100)

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


class AiModelTest(TestCase):
    """Ai モデルのテスト"""

    def test_duplicate_janome_lyrics_raises_integrity_error(self):
        # genetype="janome"は(lyrics)がユニーク（#593、MySQL移行時は要注意）
        # unique_janome_lyricsは条件付きUniqueConstraintのため、未サポートのMySQLでは
        # 0049マイグレーションの生成列ワークアラウンドで同等のDB制約を代替している（#593）
        Ai.objects.create(lyrics="私は走る", score=0, genetype="janome")

        with self.assertRaises(IntegrityError):
            Ai.objects.create(lyrics="私は走る", score=0, genetype="janome")

    def test_duplicate_lyrics_with_different_genetype_is_allowed(self):
        # ユニーク制約はgenetype="janome"のみが対象。他genetype（レガシーの
        # "model"等）とは重複してもよい
        Ai.objects.create(lyrics="私は走る", score=0, genetype="model")

        try:
            Ai.objects.create(lyrics="私は走る", score=0, genetype="janome")
        except IntegrityError:
            self.fail("genetypeが異なる場合はIntegrityErrorが発生してはならない")

    def test_bulk_create_with_ignore_conflicts_skips_duplicate_janome_lyrics(self):
        # manage.py aiは実行中の別プロセスとの競合に備えてignore_conflicts=True
        # でbulk_createしている（PR #1068のレビュー対応）。unique_janome_lyrics
        # 制約に抵触する行があっても、bulk_create全体が失敗せず、その1件だけが
        # スキップされ他の正当な行は作成されることを確認する
        # unique_janome_lyricsは条件付きUniqueConstraintのため、未サポートのMySQLでは
        # 0049マイグレーションの生成列ワークアラウンドで同等のDB制約を代替している（#593）
        Ai.objects.create(lyrics="既に存在する歌詞", score=3, genetype="janome")

        Ai.objects.bulk_create(
            [
                Ai(lyrics="既に存在する歌詞", score=0, genetype="janome"),
                Ai(lyrics="新しい歌詞", score=0, genetype="janome"),
            ],
            ignore_conflicts=True,
        )

        self.assertEqual(Ai.objects.filter(lyrics="既に存在する歌詞", genetype="janome").count(), 1)
        self.assertEqual(Ai.objects.get(lyrics="既に存在する歌詞", genetype="janome").score, 3)
        self.assertTrue(Ai.objects.filter(lyrics="新しい歌詞", genetype="janome").exists())


class WordModelTest(TestCase):
    """Word モデルのテスト"""

    def test_str_returns_word_hinshi_candidate(self):
        word = Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")
        self.assertEqual(str(word), "走る(動詞) -> 駆ける")

    def test_unique_constraint(self):
        Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")
        with self.assertRaises(IntegrityError):
            Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")

    def test_get_candidates_returns_matching_words(self):
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="疾走する")

        candidates = Word.get_candidates("走る", "動詞", "基本形")

        self.assertCountEqual(candidates, ["駆ける", "疾走する"])

    def test_get_candidates_excludes_different_hinshi(self):
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        candidates = Word.get_candidates("走る", "名詞", "基本形")

        self.assertEqual(candidates, [])

    def test_get_candidates_excludes_different_katsuyou(self):
        # hinshiが一致していても、katsuyou（活用形）が違う候補は文法が
        # 破綻するため除外する
        Word.objects.create(word="読む", hinshi="動詞", katsuyou="基本形", candidate="話す")
        Word.objects.create(word="読ん", hinshi="動詞", katsuyou="連用タ接続", candidate="話し")

        candidates = Word.get_candidates("読む", "動詞", "基本形")

        self.assertEqual(candidates, ["話す"])

    def test_get_candidates_includes_other_words_with_same_hinshi_and_katsuyou(self):
        # wordが一致しなくても、hinshi・katsuyouが一致すれば候補プールに含める
        # （SubeteJanomeNoSeidesu由来のword.jsonに元の単語が無くても候補を出せるようにするため）
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")
        Word.objects.create(word="歩く", hinshi="動詞", katsuyou="基本形", candidate="進む")

        candidates = Word.get_candidates("走る", "動詞", "基本形")

        self.assertCountEqual(candidates, ["駆ける", "進む"])

    def test_get_candidates_deduplicates_candidate_values(self):
        # 異なるwordから同じcandidate文字列が出てくる場合は重複排除する
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")
        Word.objects.create(word="歩く", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        candidates = Word.get_candidates("走る", "動詞", "基本形")

        self.assertEqual(candidates, ["駆ける"])

    def test_get_candidates_limits_result_count(self):
        for i in range(15):
            Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate=f"候補{i}")

        candidates = Word.get_candidates("走る", "動詞", "基本形", limit=10)

        self.assertEqual(len(candidates), 10)

    def test_get_candidates_is_randomized(self):
        # 表示件数(10件)を超える候補がある場合、毎回異なる組み合わせが返る
        for i in range(20):
            Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate=f"候補{i}")

        results = {tuple(Word.get_candidates("走る", "動詞", "基本形", limit=10)) for _ in range(20)}

        self.assertGreater(len(results), 1)

    def test_is_valid_candidate_true_for_existing_combination(self):
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        self.assertTrue(Word.is_valid_candidate("走る", "動詞", "基本形", "駆ける"))

    def test_is_valid_candidate_false_for_unknown_candidate(self):
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        self.assertFalse(Word.is_valid_candidate("走る", "動詞", "基本形", "でっちあげ"))

    def test_is_valid_candidate_false_for_wrong_hinshi(self):
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        self.assertFalse(Word.is_valid_candidate("走る", "名詞", "基本形", "駆ける"))

    def test_is_valid_candidate_false_for_wrong_katsuyou(self):
        # hinshiは一致していても、katsuyouが違う候補は無効
        Word.objects.create(word="読ん", hinshi="動詞", katsuyou="連用タ接続", candidate="話し")

        self.assertFalse(Word.is_valid_candidate("読む", "動詞", "基本形", "話し"))

    def test_is_valid_candidate_true_for_other_word_with_same_hinshi_and_katsuyou(self):
        # 元のwordが違っても、hinshi・katsuyouが一致すれば有効な候補として扱う
        Word.objects.create(word="歩く", hinshi="動詞", katsuyou="基本形", candidate="駆ける")

        self.assertTrue(Word.is_valid_candidate("走る", "動詞", "基本形", "駆ける"))

    def test_is_valid_candidate_true_beyond_display_limit(self):
        # get_candidates()の表示上限(10件)を超えた候補でも、実在すれば有効と判定する
        for i in range(10):
            Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate=f"候補{i}")
        Word.objects.create(word="走る", hinshi="動詞", katsuyou="基本形", candidate="11番目")

        self.assertTrue(Word.is_valid_candidate("走る", "動詞", "基本形", "11番目"))

    def test_is_valid_candidate_false_for_self_reference(self):
        # word == candidate（自己参照）は、DB上に存在するか否かに関わらず無効
        self.assertFalse(Word.is_valid_candidate("走る", "動詞", "基本形", "走る"))

    def test_word_equal_candidate_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            Word.objects.create(word="走る", hinshi="動詞", candidate="走る")


class StatsModelTest(TestCase):
    """Stats モデルのテスト"""

    def test_create_stats(self):
        stats = Stats.objects.create(year=2026, month=1, song_count=10, total_view=100)
        self.assertEqual(stats.year, 2026)
        self.assertEqual(stats.month, 1)
        self.assertEqual(stats.song_count, 10)
        self.assertEqual(stats.total_view, 100)

    def test_default_values(self):
        stats = Stats.objects.create(year=2026, month=1)
        self.assertEqual(stats.song_count, 0)
        self.assertEqual(stats.total_view, 0)
        self.assertEqual(stats.total_like, 0)
        self.assertEqual(stats.total_authors, 0)
        self.assertEqual(stats.total_imitateds, 0)

    def test_str(self):
        stats = Stats.objects.create(year=2026, month=3)
        self.assertEqual(str(stats), "2026-03 (all)")

    def test_songrange_defaults_to_all(self):
        stats = Stats.objects.create(year=2026, month=1)
        self.assertEqual(stats.songrange, "all")

    def test_year_month_songrange_unique_constraint(self):
        Stats.objects.create(year=2026, month=1, songrange="all")
        with self.assertRaises(IntegrityError):
            Stats.objects.create(year=2026, month=1, songrange="all")

    def test_year_month_allows_different_songrange(self):
        Stats.objects.create(year=2026, month=1, songrange="all")
        Stats.objects.create(year=2026, month=1, songrange="subeana")
        self.assertEqual(Stats.objects.filter(year=2026, month=1).count(), 2)

    def test_get_monthly_series_ordered(self):
        Stats.objects.create(year=2026, month=3)
        Stats.objects.create(year=2025, month=12)
        Stats.objects.create(year=2026, month=1)

        series = list(Stats.get_monthly_series())

        self.assertEqual([(s.year, s.month) for s in series], [(2025, 12), (2026, 1), (2026, 3)])

    def test_get_monthly_series_filters_by_songrange(self):
        Stats.objects.create(year=2026, month=1, songrange="all")
        Stats.objects.create(year=2026, month=1, songrange="subeana")

        series = list(Stats.get_monthly_series("subeana"))

        self.assertEqual(len(series), 1)
        self.assertEqual(series[0].songrange, "subeana")
