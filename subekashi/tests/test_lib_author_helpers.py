"""
lib/author_helpers.py のテスト

get_or_create_authors() の動作を検証する。
test_author_migration.py の AuthorHelpersTest と重複する部分があるが、
こちらはエッジケースをより詳細にカバーする。
"""
from unittest.mock import MagicMock, patch
from django.test import TestCase
from subekashi.models import Author, AuthorAlias
from subekashi.lib.author_helpers import get_or_create_authors
from subekashi.lib.song_service import check_reject_list


class GetOrCreateAuthorsTest(TestCase):
    """get_or_create_authors() のテスト"""

    def test_creates_new_authors(self):
        authors = get_or_create_authors(["新作者A", "新作者B"])
        self.assertEqual(len(authors), 2)
        self.assertEqual(Author.objects.count(), 2)

    def test_returns_author_objects(self):
        authors = get_or_create_authors(["作者X"])
        self.assertIsInstance(authors[0], Author)
        self.assertEqual(authors[0].name, "作者X")

    def test_does_not_duplicate_existing_author(self):
        Author.objects.create(name="既存作者")
        authors = get_or_create_authors(["既存作者"])
        self.assertEqual(len(authors), 1)
        self.assertEqual(Author.objects.count(), 1)

    def test_skips_empty_strings(self):
        authors = get_or_create_authors(["作者A", "", "作者B", ""])
        self.assertEqual(len(authors), 2)
        self.assertEqual(Author.objects.count(), 2)

    def test_all_empty_strings_returns_empty_list(self):
        authors = get_or_create_authors(["", "", ""])
        self.assertEqual(authors, [])
        self.assertEqual(Author.objects.count(), 0)

    def test_empty_list_returns_empty_list(self):
        authors = get_or_create_authors([])
        self.assertEqual(authors, [])

    def test_preserves_order_of_input(self):
        authors = get_or_create_authors(["作者Z", "作者A", "作者M"])
        self.assertEqual(authors[0].name, "作者Z")
        self.assertEqual(authors[1].name, "作者A")
        self.assertEqual(authors[2].name, "作者M")

    def test_mix_of_new_and_existing_authors(self):
        Author.objects.create(name="既存作者")
        authors = get_or_create_authors(["既存作者", "新規作者"])
        self.assertEqual(len(authors), 2)
        self.assertEqual(Author.objects.count(), 2)

    def test_past_alias_name_resolves_to_current_author(self):
        # #1008: alias_type="past"のAuthorAlias.nameと入力が完全一致する場合、
        # 新規Authorを作らずそのalias.authorに解決する
        current = Author.objects.create(name="現在の名義")
        AuthorAlias.objects.create(name="以前の名義", author=current, alias_type="past")

        authors = get_or_create_authors(["以前の名義"])

        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0], current)
        self.assertEqual(Author.objects.count(), 1)
        self.assertFalse(Author.objects.filter(name="以前の名義").exists())

    def test_non_past_alias_type_is_not_normalized(self):
        # another等、past以外の種別は正規化の対象外（意図的に区別すべき別人格を
        # 巻き込まないため）。入力文字列のまま新規Authorとして作成される
        owner = Author.objects.create(name="所有者作者")
        AuthorAlias.objects.create(name="別名義候補", author=owner, alias_type="another")

        authors = get_or_create_authors(["別名義候補"])

        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0].name, "別名義候補")
        self.assertNotEqual(authors[0], owner)
        self.assertEqual(Author.objects.count(), 2)

    def test_past_alias_resolution_mixed_with_new_and_existing(self):
        current = Author.objects.create(name="現在の名義2")
        AuthorAlias.objects.create(name="以前の名義2", author=current, alias_type="past")
        Author.objects.create(name="既存作者2")

        authors = get_or_create_authors(["以前の名義2", "既存作者2", "完全新規作者"])

        self.assertEqual(len(authors), 3)
        self.assertEqual(authors[0], current)
        self.assertEqual(authors[1].name, "既存作者2")
        self.assertEqual(authors[2].name, "完全新規作者")

    def test_past_alias_normalization_prevents_reject_list_evasion(self):
        # #1008: 掲載拒否リストに載っているauthorのpast別名で曲を投稿しようとしても、
        # get_or_create_authors()が現在の名義に正規化してから返すため、
        # check_reject_list()はその現在の名義に対して正しく判定できる
        ng_author = Author.objects.create(name="NGアーティスト")
        AuthorAlias.objects.create(name="NGアーティストの以前の名義", author=ng_author, alias_type="past")

        authors = get_or_create_authors(["NGアーティストの以前の名義"])

        mock_reject_module = MagicMock()
        mock_reject_module.REJECT_LIST = ["NGアーティスト"]
        with patch.dict("sys.modules", {"subekashi.constants.dynamic.reject": mock_reject_module}):
            result = check_reject_list(authors)

        self.assertIsNotNone(result)
        self.assertIn("NGアーティスト", result)

    def test_past_alias_lookup_is_batched_not_per_name(self):
        # past別名の存在チェックは名前ごとに都度クエリを発行せず、1クエリで一括取得する。
        # 名前が何件あってもこのクエリ数は増えない（N+1にならない）ことの回帰防止テスト
        for i in range(5):
            author = Author.objects.create(name=f"現在の名義{i}")
            AuthorAlias.objects.create(name=f"以前の名義{i}", author=author, alias_type="past")

        with self.assertNumQueries(1):
            authors = get_or_create_authors([f"以前の名義{i}" for i in range(5)])

        self.assertEqual(len(authors), 5)
