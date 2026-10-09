"""
lib/query_filters.py のテスト

楽曲検索フィルター関数の Q オブジェクト生成・適用結果を検証する。
"""
from django.test import TestCase
from subekashi.models import Author, AuthorAlias, Song, SongLink
from subekashi.lib.query_filters import (
    filter_by_keyword,
    filter_by_imitate,
    filter_by_imitated,
    filter_by_guesser,
    filter_by_lack,
    filter_by_collab,
    filter_by_mediatypes,
    filter_by_author,
    filter_by_author_exact,
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


class FilterByKeywordAuthorAliasTest(TestCase):
    """filter_by_keyword() の別名（双方向）対応のテスト

    issue #969本文のシナリオ（foo/foo_sub）に準じるが、owner/targetの名前は
    互いに部分文字列関係にならないものを使う。foo/foo_subのように片方がもう
    片方を含む名前だと、icontains/containsによる素の作者名一致
    (Q(authors__name__contains=keyword)) だけでテストが通ってしまい、
    別名解決コードを経由したかどうかを検証できないため。

    1. Song1 (author: yamada) 追加
    2. Song2 (author: sasaki) 追加
    3. yamadaに別名sasakiを追加（sasakiという名前のAuthorも別途実在する）
    4. keyword=sasakiで検索 → Song1, Song2がヒットすること（正方向）
    5. keyword=yamadaで検索 → 双方向のためSong1, Song2の双方がヒットすること（逆方向）
    """

    def setUp(self):
        self.owner = Author.objects.create(name="yamada")
        self.target = Author.objects.create(name="sasaki")
        self.song1 = Song.objects.create(title="Song1")
        self.song1.authors.add(self.owner)
        self.song2 = Song.objects.create(title="Song2")
        self.song2.authors.add(self.target)
        AuthorAlias.objects.create(name="sasaki", author=self.owner, alias_type="past")

    def test_forward_alias_name_matches_owning_authors_songs(self):
        # 正方向: keyword=sasakiはyamadaの別名にマッチするためSong1もヒットする
        qs = Song.objects.filter(filter_by_keyword("sasaki")).distinct()
        self.assertIn(self.song1, qs)
        self.assertIn(self.song2, qs)

    def test_reverse_alias_matches_target_authors_own_songs(self):
        # 逆方向: keyword=yamadaはsasaki自身の名前とは無関係な文字列であり、
        # 素の作者名一致(authors__name__contains)ではSong2はヒットしない。
        # 別名解決コードの逆方向ロジックによってのみSong2がヒットする。
        qs = Song.objects.filter(filter_by_keyword("yamada")).distinct()
        self.assertIn(self.song1, qs)
        self.assertIn(self.song2, qs)

    def test_unidirectional_when_target_author_not_registered(self):
        # 対象authorがまだ存在しない別名は単方向のまま、別名のnameを検索すればヒットする
        Author.objects.create(name="single")
        single_song = Song.objects.create(title="SingleSong")
        author = Author.objects.get(name="single")
        single_song.authors.add(author)
        AuthorAlias.objects.create(name="single_alias", author=author, alias_type="spell")

        qs = Song.objects.filter(filter_by_keyword("single_alias")).distinct()
        self.assertIn(single_song, qs)


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
        self.song_by_url = Song.objects.create(title="URL推測曲")
        link = SongLink.objects.create(url="https://youtu.be/guessUrl001")
        link.songs.add(self.song_by_url)
        self.unrelated = Song.objects.create(title="関係ない曲")

    def test_filter_by_title(self):
        qs = Song.objects.filter(filter_by_guesser("推測対象")).distinct()
        self.assertIn(self.song_by_title, qs)

    def test_filter_by_author_name(self):
        qs = Song.objects.filter(filter_by_guesser("推測テスト作者")).distinct()
        self.assertIn(self.song_by_author, qs)

    def test_filter_by_url(self):
        # #1117: URLからもヒットする
        qs = Song.objects.filter(filter_by_guesser("https://youtu.be/guessUrl001")).distinct()
        self.assertIn(self.song_by_url, qs)
        self.assertNotIn(self.unrelated, qs)

    def test_filter_by_partial_url(self):
        # #1117: 動画IDのみ（URLの一部）でもヒットする
        qs = Song.objects.filter(filter_by_guesser("guessUrl001")).distinct()
        self.assertIn(self.song_by_url, qs)

    def test_filter_by_unnormalized_youtube_url(self):
        # #1117: clean_urlで正規化されるため、youtube.com/watch?v=形式でもyoutu.be形式のリンクにヒットする
        qs = Song.objects.filter(filter_by_guesser("https://www.youtube.com/watch?v=guessUrl001")).distinct()
        self.assertIn(self.song_by_url, qs)

    def test_filter_by_url_case_insensitive(self):
        # #1117: URLは大文字小文字を区別しない
        qs = Song.objects.filter(filter_by_guesser("GUESSURL001")).distinct()
        self.assertIn(self.song_by_url, qs)

    def test_filter_by_url_not_match_other_url(self):
        qs = Song.objects.filter(filter_by_guesser("https://youtu.be/otherUrl999")).distinct()
        self.assertNotIn(self.song_by_url, qs)

    def test_filter_by_author_alias_bidirectional(self):
        # owner/targetの名前は部分文字列関係にならないものを使う（素の作者名一致で
        # 偶然パスしてしまい、別名解決コードを経由したか検証できなくなるのを防ぐため）
        owner = Author.objects.create(name="推測ヤマダ")
        target = Author.objects.create(name="推測ササキ")
        song_owner = Song.objects.create(title="推測ヤマダ曲")
        song_owner.authors.add(owner)
        song_target = Song.objects.create(title="推測ササキ曲")
        song_target.authors.add(target)
        AuthorAlias.objects.create(name="推測ササキ", author=owner, alias_type="past")

        # 正方向
        qs = Song.objects.filter(filter_by_guesser("推測ササキ")).distinct()
        self.assertIn(song_owner, qs)
        self.assertIn(song_target, qs)

        # 逆方向: "推測ヤマダ"は"推測ササキ"の部分文字列ではないため、
        # 別名解決コードの逆方向ロジックがなければsong_targetはヒットしない
        qs = Song.objects.filter(filter_by_guesser("推測ヤマダ")).distinct()
        self.assertIn(song_owner, qs)
        self.assertIn(song_target, qs)


class FilterByAuthorTest(TestCase):
    """filter_by_author() のテスト（別名・双方向の部分一致）

    owner/targetの名前は部分文字列関係にならないものを使う（素の作者名一致
    Q(authors__name__icontains=value) で偶然パスしてしまうのを防ぐため）
    """

    def setUp(self):
        self.owner = Author.objects.create(name="ayamada")
        self.target = Author.objects.create(name="asasaki")
        self.song1 = Song.objects.create(title="AuthorSong1")
        self.song1.authors.add(self.owner)
        self.song2 = Song.objects.create(title="AuthorSong2")
        self.song2.authors.add(self.target)
        AuthorAlias.objects.create(name="asasaki", author=self.owner, alias_type="past")

    def test_matches_forward_alias(self):
        # 正方向: "asasaki"はownerの別名にマッチするためSong1もヒットする
        qs = Song.objects.filter(filter_by_author("asasaki")).distinct()
        self.assertIn(self.song1, qs)
        self.assertIn(self.song2, qs)

    def test_matches_reverse_alias(self):
        # 逆方向: "ayamada"はtarget("asasaki")の部分文字列ではないため、
        # 別名解決コードの逆方向ロジックがなければSong2はヒットしない
        qs = Song.objects.filter(filter_by_author("ayamada")).distinct()
        self.assertIn(self.song1, qs)
        self.assertIn(self.song2, qs)


class FilterByAuthorExactTest(TestCase):
    """filter_by_author_exact() のテスト（別名・双方向の完全一致）"""

    def setUp(self):
        self.foo = Author.objects.create(name="efoo")
        self.foo_sub = Author.objects.create(name="efoo_sub")
        self.song1 = Song.objects.create(title="ExactSong1")
        self.song1.authors.add(self.foo)
        self.song2 = Song.objects.create(title="ExactSong2")
        self.song2.authors.add(self.foo_sub)
        AuthorAlias.objects.create(name="efoo_sub", author=self.foo, alias_type="past")

    def test_exact_match_does_not_match_partial(self):
        qs = Song.objects.filter(filter_by_author_exact("efo")).distinct()
        self.assertNotIn(self.song1, qs)
        self.assertNotIn(self.song2, qs)

    def test_exact_match_own_name(self):
        qs = Song.objects.filter(filter_by_author_exact("efoo")).distinct()
        self.assertIn(self.song1, qs)
        self.assertIn(self.song2, qs)

    def test_exact_match_forward_alias(self):
        qs = Song.objects.filter(filter_by_author_exact("efoo_sub")).distinct()
        self.assertIn(self.song1, qs)
        self.assertIn(self.song2, qs)


class FilterByAuthorAliasAnotherTypeExcludedTest(TestCase):
    """alias_type="another"（別名義）は検索フィルターの別名解決対象から除外されることのテスト（#996）

    別名義は同一人物の表記揺れ・旧名等とは異なり、意図的に区別して扱うべきものの
    ため、双方向解決（filter_by_author_alias）の対象外とする。
    """

    def setUp(self):
        self.owner = Author.objects.create(name="another_yamada")
        self.target = Author.objects.create(name="another_sasaki")
        self.song1 = Song.objects.create(title="AnotherSong1")
        self.song1.authors.add(self.owner)
        self.song2 = Song.objects.create(title="AnotherSong2")
        self.song2.authors.add(self.target)
        AuthorAlias.objects.create(name="another_sasaki", author=self.owner, alias_type="another")

    def test_filter_by_author_forward_excludes_another(self):
        qs = Song.objects.filter(filter_by_author("another_sasaki")).distinct()
        self.assertNotIn(self.song1, qs)
        self.assertIn(self.song2, qs)

    def test_filter_by_author_reverse_excludes_another(self):
        qs = Song.objects.filter(filter_by_author("another_yamada")).distinct()
        self.assertIn(self.song1, qs)
        self.assertNotIn(self.song2, qs)

    def test_filter_by_author_exact_excludes_another(self):
        qs = Song.objects.filter(filter_by_author_exact("another_sasaki")).distinct()
        self.assertNotIn(self.song1, qs)
        self.assertIn(self.song2, qs)

    def test_filter_by_keyword_excludes_another(self):
        qs = Song.objects.filter(filter_by_keyword("another_sasaki")).distinct()
        self.assertNotIn(self.song1, qs)
        self.assertIn(self.song2, qs)

    def test_filter_by_guesser_excludes_another(self):
        qs = Song.objects.filter(filter_by_guesser("another_sasaki")).distinct()
        self.assertNotIn(self.song1, qs)
        self.assertIn(self.song2, qs)

    def test_non_another_type_still_matches(self):
        # 同じownerに別名義以外(past)の別名も追加した場合、そちらは通常通りヒットする
        AuthorAlias.objects.create(name="another_yamada_past", author=self.owner, alias_type="past")
        qs = Song.objects.filter(filter_by_author("another_yamada_past")).distinct()
        self.assertIn(self.song1, qs)


class FilterByAuthorAliasGroupTypeExcludedTest(TestCase):
    """alias_type="group"（グループ）は検索フィルターで正方向・逆方向とも一切
    考慮されないことのテスト（仕様変更、#1006）

    メンバー名義で検索してもグループ自身の曲はヒットせず、グループ名義で検索しても
    メンバー個々の曲はヒットしない。#1006時点では暫定的にメンバー→グループの
    片方向のみ考慮していたが、フィードバック元への再確認によりanotherと同様に
    完全除外する方針に変更した（詳細は#1003参照）。
    """

    def setUp(self):
        self.member = Author.objects.create(name="group_member")
        self.group = Author.objects.create(name="group_account")
        self.member_song = Song.objects.create(title="MemberSong")
        self.member_song.authors.add(self.member)
        self.group_song = Song.objects.create(title="GroupSong")
        self.group_song.authors.add(self.group)
        AuthorAlias.objects.create(name="group_account", author=self.member, alias_type="group")

    def test_filter_by_author_forward_excludes_group(self):
        qs = Song.objects.filter(filter_by_author("group_account")).distinct()
        self.assertNotIn(self.member_song, qs)
        self.assertIn(self.group_song, qs)

    def test_filter_by_author_reverse_excludes_group(self):
        qs = Song.objects.filter(filter_by_author("group_member")).distinct()
        self.assertIn(self.member_song, qs)
        self.assertNotIn(self.group_song, qs)

    def test_filter_by_author_exact_excludes_group(self):
        qs = Song.objects.filter(filter_by_author_exact("group_account")).distinct()
        self.assertNotIn(self.member_song, qs)
        self.assertIn(self.group_song, qs)

    def test_filter_by_keyword_excludes_group(self):
        qs = Song.objects.filter(filter_by_keyword("group_account")).distinct()
        self.assertNotIn(self.member_song, qs)
        self.assertIn(self.group_song, qs)

    def test_filter_by_guesser_excludes_group(self):
        qs = Song.objects.filter(filter_by_guesser("group_account")).distinct()
        self.assertNotIn(self.member_song, qs)
        self.assertIn(self.group_song, qs)

    def test_non_group_type_still_matches(self):
        # 同じmemberにグループ以外(past)の別名も追加した場合、そちらは通常通りヒットする
        AuthorAlias.objects.create(name="group_member_past", author=self.member, alias_type="past")
        qs = Song.objects.filter(filter_by_author("group_member_past")).distinct()
        self.assertIn(self.member_song, qs)


class FilterByAuthorAliasTransitiveResolutionTest(TestCase):
    """#1003で確認された具体例（A/B/C/D/E）が検索フィルターの仕様表通りになることの結合テスト（#1006）

    名義A(tamura)に「別名義B(inoue)」「以前の名称C(kobayashi)」「以前の名称D(yoshida)」
    「グループE(watanabe)」を登録した場合、以下の検索結果になることを確認する。

    | 検索語 | ヒットする曲の作者 |
    | --- | --- |
    | A | A, C, D |
    | B | B のみ |
    | C | A, C, D |
    | D | A, C, D |
    | E | E のみ |

    グループEはanotherと同様に検索では完全に除外されるため、A/C/Dを検索してもEは
    ヒットしない（仕様変更、#1006）。
    """

    def setUp(self):
        self.a = Author.objects.create(name="tamura")
        self.b = Author.objects.create(name="inoue")
        self.c = Author.objects.create(name="kobayashi")
        self.d = Author.objects.create(name="yoshida")
        self.e = Author.objects.create(name="watanabe")
        AuthorAlias.objects.create(name="inoue", author=self.a, alias_type="another")
        AuthorAlias.objects.create(name="kobayashi", author=self.a, alias_type="past")
        AuthorAlias.objects.create(name="yoshida", author=self.a, alias_type="past")
        AuthorAlias.objects.create(name="watanabe", author=self.a, alias_type="group")

        self.song_a = Song.objects.create(title="SongA")
        self.song_a.authors.add(self.a)
        self.song_b = Song.objects.create(title="SongB")
        self.song_b.authors.add(self.b)
        self.song_c = Song.objects.create(title="SongC")
        self.song_c.authors.add(self.c)
        self.song_d = Song.objects.create(title="SongD")
        self.song_d.authors.add(self.d)
        self.song_e = Song.objects.create(title="SongE")
        self.song_e.authors.add(self.e)

    def search(self, value):
        return set(Song.objects.filter(filter_by_author_exact(value)).distinct())

    def test_search_a_hits_a_c_d_not_b_not_e(self):
        self.assertEqual(self.search("tamura"), {self.song_a, self.song_c, self.song_d})

    def test_search_b_hits_only_b(self):
        self.assertEqual(self.search("inoue"), {self.song_b})

    def test_search_c_hits_a_c_d_not_b_not_e(self):
        self.assertEqual(self.search("kobayashi"), {self.song_a, self.song_c, self.song_d})

    def test_search_d_hits_a_c_d_not_b_not_e(self):
        self.assertEqual(self.search("yoshida"), {self.song_a, self.song_c, self.song_d})

    def test_search_e_hits_only_e(self):
        self.assertEqual(self.search("watanabe"), {self.song_e})


class FilterByAuthorAliasMultiHopTest(TestCase):
    """中継点になる別名を複数ホップ、正方向・逆方向の両方で辿れることのテスト（#1162）

    A -past-> B -spell-> C -abbr-> D とつながり、DとEは別名義（another）でのみつながる。
    """

    def setUp(self):
        self.a = Author.objects.create(name="hop_a")
        self.b = Author.objects.create(name="hop_b")
        self.c = Author.objects.create(name="hop_c")
        self.d = Author.objects.create(name="hop_d")
        self.e = Author.objects.create(name="hop_e")
        AuthorAlias.objects.create(name="hop_b", author=self.a, alias_type="past")
        AuthorAlias.objects.create(name="hop_c", author=self.b, alias_type="spell")
        AuthorAlias.objects.create(name="hop_d", author=self.c, alias_type="abbr")
        AuthorAlias.objects.create(name="hop_e", author=self.d, alias_type="another")

        self.songs = {}
        for author in (self.a, self.b, self.c, self.d, self.e):
            song = Song.objects.create(title=f"Song_{author.name}")
            song.authors.add(author)
            self.songs[author.name] = song

    def search(self, value):
        return set(Song.objects.filter(filter_by_author_exact(value)).distinct())

    def test_forward_chain_reaches_d_not_e(self):
        expected = {self.songs[name] for name in ("hop_a", "hop_b", "hop_c", "hop_d")}
        self.assertEqual(self.search("hop_a"), expected)

    def test_reverse_chain_reaches_a_not_e(self):
        expected = {self.songs[name] for name in ("hop_a", "hop_b", "hop_c", "hop_d")}
        self.assertEqual(self.search("hop_d"), expected)

    def test_another_is_not_bridged(self):
        self.assertEqual(self.search("hop_e"), {self.songs["hop_e"]})


class FilterByAuthorAliasQueryCountTest(TestCase):
    """別名を辿る処理のクエリ数が、起点の名前の数によらず一定であることのテスト（#1162）

    検索語にマッチする作者名・別名の取得（2クエリ）と、中継点になる別名の一括取得（1クエリ）
    のみで、起点の名前ごとにクエリを発行しない。
    """

    def test_single_seed(self):
        author = Author.objects.create(name="seed_author_0")
        AuthorAlias.objects.create(name="seed_alias_0", author=author, alias_type="past")
        with self.assertNumQueries(3):
            filter_by_author("seed_author")

    def test_many_seeds(self):
        for i in range(30):
            author = Author.objects.create(name=f"seed_author_{i}")
            AuthorAlias.objects.create(name=f"seed_alias_{i}", author=author, alias_type="past")
        with self.assertNumQueries(3):
            filter_by_author("seed_author")


class FilterByLackTest(TestCase):
    """filter_by_lack() のテスト

    filter_by_lack() は以下の3条件のいずれかを満たす曲を「未完成」と判定する:
      (A) is_deleted=False かつ SongLink が存在しない（is_questionable は問わない）
      (B) is_questionable=False かつ is_original=False かつ is_subeana=True かつ imitates が空 かつ author_id=1 なし
      (C) is_questionable=False かつ is_inst=False かつ lyrics が空文字列

    各テストで「意図しない条件」に引っかからないよう、検証したい条件以外は
    明示的に打ち消したフィールド値を設定する。
    """

    def test_song_without_url_and_not_deleted_is_lack(self):
        # 条件(A): URLなし・削除されていない → 未完成
        # 条件(C)に引っかからないよう lyrics を設定し、is_original=True で条件(B)を除外
        song = Song.objects.create(title="URLなし曲", is_deleted=False, lyrics="歌詞あり", is_original=True)
        qs = Song.objects.filter(filter_by_lack())
        self.assertIn(song, qs)

    def test_song_with_url_is_not_lack(self):
        # 条件(A)を満たさない: URLあり・削除なし・歌詞あり・is_original=True(条件B除外)
        song = Song.objects.create(title="URLあり曲", lyrics="歌詞あり", is_original=True)
        link = SongLink.objects.create(url="https://youtu.be/hasurlsong1")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertNotIn(song, qs)

    def test_song_without_lyrics_and_not_inst_is_lack(self):
        # 条件(C): インストでない かつ 歌詞なし → 未完成
        # is_original=True で条件(B)を除外
        song = Song.objects.create(title="歌詞なし曲", is_inst=False, lyrics="", is_original=True)
        qs = Song.objects.filter(filter_by_lack())
        self.assertIn(song, qs)

    def test_inst_song_without_lyrics_is_not_lack(self):
        # 条件(C)を満たさない: is_inst=True なら歌詞なしでも未完成ではない
        # URLあり(条件A除外)・is_original=True(条件B除外)
        song = Song.objects.create(title="インスト曲", is_inst=True, lyrics="", is_original=True)
        link = SongLink.objects.create(url="https://youtu.be/instsong00001")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertNotIn(song, qs)

    def test_deleted_song_is_not_caught_by_url_check(self):
        # 条件(A)を満たさない: is_deleted=True なら URL がなくても条件(A)の対象外
        # is_original=True(条件B除外)・歌詞あり(条件C除外)・URLなし（条件Aを意図的に満たさせる状況）
        song = Song.objects.create(title="削除済み曲", is_deleted=True, lyrics="歌詞あり", is_original=True)
        # URL を持たないまま → 条件(A)は「is_deleted=False かつ URLなし」なので is_deleted=True は除外される
        qs = Song.objects.filter(filter_by_lack())
        self.assertNotIn(song, qs)

    def test_questionable_song_matching_condition_a_is_lack(self):
        # 条件(A)は is_questionable を問わないため、URLなし・削除されていなければ未完成
        song = Song.objects.create(
            title="界隈曲URLなしテスト", is_questionable=True, is_deleted=False, lyrics="歌詞あり", is_original=True,
        )
        qs = Song.objects.filter(filter_by_lack())
        self.assertIn(song, qs)

    def test_questionable_song_not_matching_condition_b_or_c_is_not_lack(self):
        # 条件(B)(C)は is_questionable=False が必須のため、is_questionable=True なら
        # 条件(A)に該当しない限り未完成扱いにならない
        song = Song.objects.create(
            title="界隈曲完成扱いテスト", is_questionable=True, is_deleted=False, lyrics="", is_inst=False, is_original=False,
        )
        link = SongLink.objects.create(url="https://youtu.be/questionable0001")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertNotIn(song, qs)

    def test_subeana_song_without_special_author_is_lack(self):
        # 条件(B): is_subeana=True かつ 特殊作者(id=1)なし → 未完成
        # URLあり(条件A除外)・歌詞あり(条件C除外)
        song = Song.objects.create(
            title="すべあな曲特殊作者なしテスト", is_original=False, is_subeana=True, lyrics="歌詞あり",
        )
        link = SongLink.objects.create(url="https://youtu.be/subeananoauthor01")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertIn(song, qs)

    def test_subeana_song_with_special_author_is_not_lack(self):
        # 条件(B)を満たさない: 特殊作者(id=1)が紐づいている場合は未完成ではない
        author = Author.objects.create(pk=1, name="全てあなたの所為です。")
        song = Song.objects.create(
            title="すべあな曲特殊作者ありテスト", is_original=False, is_subeana=True, lyrics="歌詞あり",
        )
        song.authors.add(author)
        link = SongLink.objects.create(url="https://youtu.be/subeanawithauthor01")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertNotIn(song, qs)

    def test_non_subeana_song_without_special_author_is_not_lack(self):
        # 条件(B)を満たさない: is_subeana=False の場合は特殊作者の有無に関わらず未完成ではない
        song = Song.objects.create(
            title="非すべあな曲テスト", is_original=False, is_subeana=False, lyrics="歌詞あり",
        )
        link = SongLink.objects.create(url="https://youtu.be/nonsubeana00001")
        link.songs.add(song)
        qs = Song.objects.filter(filter_by_lack()).distinct()
        self.assertNotIn(song, qs)


class FilterByMediatypesTest(TestCase):
    """filter_by_mediatypes() のテスト

    "other"（URL未登録）はSongLinkが1件も存在しないことを表すため、
    links__url__regex では判定できず ~Exists() で判定する必要がある。
    また非公開/削除済み（is_deleted=True）の曲は対象外とする。
    """

    def setUp(self):
        self.song_without_link = Song.objects.create(title="URL未登録曲")
        self.deleted_song_without_link = Song.objects.create(title="削除済みURL未登録曲", is_deleted=True)
        self.song_with_youtube_link = Song.objects.create(title="YouTube曲")
        link = SongLink.objects.create(url="https://youtu.be/mediatype12345")
        link.songs.add(self.song_with_youtube_link)

    def test_other_matches_song_without_any_link(self):
        qs = Song.objects.filter(filter_by_mediatypes("other")).distinct()
        self.assertIn(self.song_without_link, qs)

    def test_other_does_not_match_song_with_link(self):
        qs = Song.objects.filter(filter_by_mediatypes("other")).distinct()
        self.assertNotIn(self.song_with_youtube_link, qs)

    def test_other_does_not_match_deleted_song(self):
        qs = Song.objects.filter(filter_by_mediatypes("other")).distinct()
        self.assertNotIn(self.deleted_song_without_link, qs)

    def test_youtube_matches_song_with_youtube_link(self):
        qs = Song.objects.filter(filter_by_mediatypes("youtube")).distinct()
        self.assertIn(self.song_with_youtube_link, qs)
        self.assertNotIn(self.song_without_link, qs)

    def test_youtube_and_other_combined_matches_both(self):
        qs = Song.objects.filter(filter_by_mediatypes("youtube,other")).distinct()
        self.assertIn(self.song_with_youtube_link, qs)
        self.assertIn(self.song_without_link, qs)

    def test_vimesis_matches_song_with_vimesis_link(self):
        # Issue #1056: ドメイン境界チェックを含む正規表現がDBのREGEXP経由でも
        # 正しく機能することを確認する
        song_with_vimesis_link = Song.objects.create(title="Vimesis曲")
        link = SongLink.objects.create(url="https://main.vimesis.com/channel/@subekashi")
        link.songs.add(song_with_vimesis_link)

        qs = Song.objects.filter(filter_by_mediatypes("vimesis")).distinct()
        self.assertIn(song_with_vimesis_link, qs)
        self.assertNotIn(self.song_with_youtube_link, qs)

    def test_vimesis_does_not_match_spoofed_domain(self):
        # vimesis.com.attacker.example のようなドメインを持つリンクが
        # vimesisメディアとして誤って絞り込まれないことを確認する
        spoofed_song = Song.objects.create(title="なりすましドメイン曲")
        link = SongLink.objects.create(url="https://vimesis.com.attacker.example/")
        link.songs.add(spoofed_song)

        qs = Song.objects.filter(filter_by_mediatypes("vimesis")).distinct()
        self.assertNotIn(spoofed_song, qs)


class MakeIsLackAnnotationTest(TestCase):
    """make_is_lack_annotation() のテスト"""

    def test_lack_song_annotated_true(self):
        song = Song.objects.create(title="未完成曲", is_inst=False, lyrics="")
        qs = Song.objects.annotate(is_lack=make_is_lack_annotation())
        annotated = qs.get(pk=song.pk)
        self.assertTrue(annotated.is_lack)

    def test_complete_song_annotated_false(self):
        # URLあり(条件A除外)・歌詞あり(条件C除外)・is_original=True(条件B除外)
        song = Song.objects.create(title="完成曲", lyrics="歌詞あり", is_original=True)
        link = SongLink.objects.create(url="https://youtu.be/complete00001")
        link.songs.add(song)
        qs = Song.objects.annotate(is_lack=make_is_lack_annotation())
        annotated = qs.get(pk=song.pk)
        self.assertFalse(annotated.is_lack)

    def test_questionable_song_matching_condition_a_annotated_true(self):
        # 条件(A)は is_questionable を問わないため、URLなし・削除されていなければ is_lack=True
        song = Song.objects.create(
            title="界隈曲アノテーションURLなしテスト", is_questionable=True, lyrics="歌詞あり", is_original=True,
        )
        qs = Song.objects.annotate(is_lack=make_is_lack_annotation())
        annotated = qs.get(pk=song.pk)
        self.assertTrue(annotated.is_lack)

    def test_questionable_song_not_matching_condition_b_or_c_annotated_false(self):
        # 条件(B)(C)は is_questionable=False が必須のため、is_questionable=True かつ
        # 条件(A)に該当しなければ is_lack=False
        song = Song.objects.create(title="界隈曲アノテーションテスト", is_questionable=True, is_inst=False, lyrics="")
        link = SongLink.objects.create(url="https://youtu.be/questionable0002")
        link.songs.add(song)
        qs = Song.objects.annotate(is_lack=make_is_lack_annotation())
        annotated = qs.get(pk=song.pk)
        self.assertFalse(annotated.is_lack)

    def test_subeana_song_without_special_author_annotated_true(self):
        # 条件(B): is_subeana=True かつ 特殊作者(id=1)なし → is_lack=True
        # URLあり(条件A除外)・歌詞あり(条件C除外)
        song = Song.objects.create(
            title="すべあな曲アノテーション特殊作者なしテスト", is_original=False, is_subeana=True, lyrics="歌詞あり",
        )
        link = SongLink.objects.create(url="https://youtu.be/subeananoauthor02")
        link.songs.add(song)
        qs = Song.objects.annotate(is_lack=make_is_lack_annotation())
        annotated = qs.get(pk=song.pk)
        self.assertTrue(annotated.is_lack)

    def test_subeana_song_with_special_author_annotated_false(self):
        # 条件(B)を満たさない: 特殊作者(id=1)が紐づいている場合は is_lack=False
        author = Author.objects.create(pk=1, name="全てあなたの所為です。")
        song = Song.objects.create(
            title="すべあな曲アノテーション特殊作者ありテスト", is_original=False, is_subeana=True, lyrics="歌詞あり",
        )
        song.authors.add(author)
        link = SongLink.objects.create(url="https://youtu.be/subeanawithauthor02")
        link.songs.add(song)
        qs = Song.objects.annotate(is_lack=make_is_lack_annotation())
        annotated = qs.get(pk=song.pk)
        self.assertFalse(annotated.is_lack)


class FilterByCollabTest(TestCase):
    """filter_by_collab() のテスト（作者が2人以上の曲を合作とする、#943）"""

    def setUp(self):
        authors = [Author.objects.create(name=f"合作テスト作者{i}") for i in range(3)]
        self.no_author = Song.objects.create(title="作者なし曲")
        self.single = Song.objects.create(title="単独曲")
        self.single.authors.add(authors[0])
        self.collab2 = Song.objects.create(title="2人の合作曲")
        self.collab2.authors.add(authors[0], authors[1])
        self.collab3 = Song.objects.create(title="3人の合作曲")
        self.collab3.authors.add(*authors)

    def test_songs_with_two_or_more_authors_are_collab(self):
        # 作者数で集計したサブクエリで絞り込むため、作者が3人でも重複しない
        ids = list(Song.objects.filter(filter_by_collab()).values_list("id", flat=True))
        self.assertCountEqual(ids, [self.collab2.id, self.collab3.id])

    def test_exclude_returns_songs_with_one_or_no_author(self):
        ids = list(Song.objects.exclude(filter_by_collab()).values_list("id", flat=True))
        self.assertCountEqual(ids, [self.no_author.id, self.single.id])
