"""
lib/author_alias_service.py のテスト

別名のDiscord通知テキスト構築関数と、名義の統一（#1137）の変更内容・統一の状態（#1230）の算出を検証する。
"""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from subekashi.models import Author, AuthorAlias, Song
from subekashi.lib.author_alias_service import (
    build_new_alias_discord_text,
    build_edit_alias_discord_text,
    build_delete_alias_discord_text,
    build_unify_name_discord_text,
    build_unify_name_plan,
    get_ununified_source_authors,
)


class BuildNewAliasDiscordTextTest(TestCase):
    """build_new_alias_discord_text() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="通知テスト作者")
        self.alias = AuthorAlias.objects.create(name="通知テスト別名", author=self.author, alias_type="past")

    def test_text_contains_author_name(self):
        text = build_new_alias_discord_text(self.author, self.alias, "editor_ip")
        self.assertIn("通知テスト作者", text)

    def test_text_contains_alias_name(self):
        text = build_new_alias_discord_text(self.author, self.alias, "editor_ip")
        self.assertIn("通知テスト別名", text)

    def test_text_contains_alias_type_display(self):
        text = build_new_alias_discord_text(self.author, self.alias, "editor_ip")
        self.assertIn("以前の名称", text)

    def test_text_contains_editor(self):
        text = build_new_alias_discord_text(self.author, self.alias, "テスト編集者")
        self.assertIn("テスト編集者", text)


class BuildEditAliasDiscordTextTest(TestCase):
    """build_edit_alias_discord_text() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="編集通知テスト作者")

    def test_text_contains_changed_name(self):
        changes = [["種類", "編集前", "編集後"], ["別名", "旧別名", "新別名"]]
        text = build_edit_alias_discord_text(self.author, "旧別名", changes, "editor_ip")
        self.assertIn("旧別名", text)
        self.assertIn("新別名", text)

    def test_text_contains_changed_type(self):
        changes = [["種類", "編集前", "編集後"], ["種別", "以前の名称", "SNSでの名称"]]
        text = build_edit_alias_discord_text(self.author, "対象別名", changes, "editor_ip")
        self.assertIn("以前の名称", text)
        self.assertIn("SNSでの名称", text)

    def test_text_contains_author_name(self):
        changes = [["種類", "編集前", "編集後"], ["別名", "旧", "新"]]
        text = build_edit_alias_discord_text(self.author, "旧", changes, "editor_ip")
        self.assertIn("編集通知テスト作者", text)


class BuildDeleteAliasDiscordTextTest(TestCase):
    """build_delete_alias_discord_text() のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="削除通知テスト作者")

    def test_text_contains_author_name(self):
        text = build_delete_alias_discord_text(self.author, "削除対象別名", "editor_ip")
        self.assertIn("削除通知テスト作者", text)

    def test_text_contains_alias_name(self):
        text = build_delete_alias_discord_text(self.author, "削除対象別名", "editor_ip")
        self.assertIn("削除対象別名", text)


class BuildUnifyNamePlanTest(TestCase):
    """build_unify_name_plan() のテスト（#1137）"""

    def setUp(self):
        self.author = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")

    def test_current_name_targets_self_and_sources_past_alias_authors(self):
        past_author = Author.objects.create(name="以前の名義2")
        plan = build_unify_name_plan(self.author, "現在の名義")
        self.assertEqual(plan.target_author, self.author)
        self.assertEqual(plan.source_authors, [past_author])
        self.assertFalse(plan.renames_author)
        self.assertFalse(plan.moves_to_existing_author)

    def test_past_alias_without_existing_author_renames_self(self):
        plan = build_unify_name_plan(self.author, "以前の名義")
        self.assertEqual(plan.target_author, self.author)
        self.assertEqual(plan.source_authors, [])
        self.assertTrue(plan.renames_author)
        self.assertFalse(plan.moves_to_existing_author)

    def test_past_alias_with_existing_author_targets_it_and_sources_self(self):
        target = Author.objects.create(name="以前の名義")
        plan = build_unify_name_plan(self.author, "以前の名義")
        self.assertEqual(plan.target_author, target)
        self.assertEqual(plan.source_authors, [self.author])
        self.assertFalse(plan.renames_author)
        self.assertTrue(plan.moves_to_existing_author)

    def test_authors_matching_non_past_aliases_are_not_sources(self):
        AuthorAlias.objects.create(name="別名義", author=self.author, alias_type="another")
        Author.objects.create(name="別名義")
        plan = build_unify_name_plan(self.author, "現在の名義")
        self.assertEqual(plan.source_authors, [])

    def test_source_authors_are_in_past_alias_order(self):
        # 別名一覧画面の統一するフォームの候補と同じ順に並べる（#1230）。作者のid順・名前順の
        # どちらとも異なる順になるよう、後に登録した別名ほど作者のidと名前が小さくなるようにする
        AuthorAlias.objects.create(name="ん以前の名義", author=self.author, alias_type="past")
        AuthorAlias.objects.create(name="あ以前の名義", author=self.author, alias_type="past")
        first_author = Author.objects.create(name="あ以前の名義")
        second_author = Author.objects.create(name="ん以前の名義")
        plan = build_unify_name_plan(self.author, "現在の名義")
        self.assertEqual(plan.source_authors, [second_author, first_author])

    def test_affected_source_authors_excludes_authors_without_songs(self):
        past_author = Author.objects.create(name="以前の名義")
        Author.objects.create(name="以前の名義2")
        song = Song.objects.create(title="以前の名義の曲")
        song.authors.add(past_author)
        plan = build_unify_name_plan(self.author, "現在の名義")
        pairs = plan.song_author_pairs()
        self.assertEqual(pairs, [(song.id, past_author.id)])
        self.assertEqual(plan.affected_source_authors(pairs), [past_author])

    def test_affected_source_authors_includes_self_without_songs_when_target_is_existing_author(self):
        # 既存の別Authorが統一先の場合、authorは曲が無くても別名・リンクを移すため含める
        Author.objects.create(name="以前の名義")
        plan = build_unify_name_plan(self.author, "以前の名義")
        self.assertEqual(plan.affected_source_authors(plan.song_author_pairs()), [self.author])


class GetUnunifiedSourceAuthorsTest(TestCase):
    """get_ununified_source_authors() のテスト（#1230）"""

    def setUp(self):
        self.author = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")
        AuthorAlias.objects.create(name="以前の名義2", author=self.author, alias_type="past")

    def test_no_author_matching_past_alias_is_unified(self):
        self.assertEqual(get_ununified_source_authors(self.author), ([], 0))

    def test_author_matching_past_alias_without_songs_is_unified(self):
        # 統一済みの作者は削除されず、曲数0で残る（#1137）
        Author.objects.create(name="以前の名義")
        self.assertEqual(get_ununified_source_authors(self.author), ([], 0))

    def test_author_matching_past_alias_with_songs_is_not_unified(self):
        past_author = Author.objects.create(name="以前の名義")
        Author.objects.create(name="以前の名義2")
        for title in ["以前の名義の曲1", "以前の名義の曲2"]:
            Song.objects.create(title=title).authors.add(past_author)

        self.assertEqual(get_ununified_source_authors(self.author), ([past_author], 2))

    def test_song_co_authored_by_multiple_past_alias_authors_is_counted_once(self):
        past_author = Author.objects.create(name="以前の名義")
        past_author2 = Author.objects.create(name="以前の名義2")
        Song.objects.create(title="共著の曲").authors.add(past_author, past_author2)

        source_authors, song_count = get_ununified_source_authors(self.author)

        self.assertCountEqual(source_authors, [past_author, past_author2])
        self.assertEqual(song_count, 1)

    def test_own_songs_are_not_counted(self):
        Song.objects.create(title="現在の名義の曲").authors.add(self.author)
        self.assertEqual(get_ununified_source_authors(self.author), ([], 0))

    def test_authors_matching_non_past_aliases_are_not_counted(self):
        # 別名義（another）等、past以外の種別は統一の対象外
        AuthorAlias.objects.create(name="別名義", author=self.author, alias_type="another")
        Song.objects.create(title="別名義の曲").authors.add(Author.objects.create(name="別名義"))
        self.assertEqual(get_ununified_source_authors(self.author), ([], 0))

    def test_does_not_fetch_each_song(self):
        # 別名一覧画面を開くたびに呼ばれるため、統一元の曲を1曲ずつ取得せず、曲を持つAuthorのidと
        # 曲数を集計して取得する（DISTINCTのauthor_idとCOUNT(DISTINCT song_id)の2クエリ）
        past_author = Author.objects.create(name="以前の名義")
        for i in range(5):
            Song.objects.create(title=f"以前の名義の曲{i}").authors.add(past_author)

        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(get_ununified_source_authors(self.author), ([past_author], 5))

        song_authors_table = connection.ops.quote_name(Song.authors.through._meta.db_table)
        song_authors_queries = [q["sql"] for q in ctx.captured_queries if song_authors_table in q["sql"]]
        self.assertEqual(len(song_authors_queries), 2)
        for sql in song_authors_queries:
            self.assertIn("DISTINCT", sql)

    def test_skips_song_count_query_when_unified(self):
        # 曲を持つAuthorが無ければ、曲数の集計は行わない
        Author.objects.create(name="以前の名義")

        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(get_ununified_source_authors(self.author), ([], 0))

        self.assertFalse(any("COUNT" in q["sql"] for q in ctx.captured_queries))


class BuildUnifyNameDiscordTextTest(TestCase):
    """build_unify_name_discord_text() のテスト（#1137）"""

    def setUp(self):
        self.target = Author.objects.create(name="統一後の名義")

    def test_text_contains_new_name_and_target_aliases_url(self):
        text = build_unify_name_discord_text(self.target, "統一後の名義", "統一後の名義", "editor_ip")
        self.assertIn("統一後の名義", text)
        self.assertIn(f"/authors/{self.target.id}/aliases", text)

    def test_text_contains_old_name_only_when_changed(self):
        text = build_unify_name_discord_text(self.target, "変更前の名義", "統一後の名義", "editor_ip")
        self.assertIn("変更前の名義", text)
        text = build_unify_name_discord_text(self.target, "統一後の名義", "統一後の名義", "editor_ip")
        self.assertNotIn("変更前", text)

    def test_text_contains_source_authors(self):
        source = Author.objects.create(name="統一元の名義")
        text = build_unify_name_discord_text(
            self.target, "統一後の名義", "統一後の名義", "editor_ip", source_authors=[source]
        )
        self.assertIn(f"Author(id={source.id}, name=統一元の名義)", text)

    def test_text_contains_editor(self):
        text = build_unify_name_discord_text(self.target, "統一後の名義", "統一後の名義", "テスト編集者")
        self.assertIn("テスト編集者", text)
