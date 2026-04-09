"""
lib/author_helpers.py のテスト

get_or_create_authors() の動作を検証する。
test_author_migration.py の AuthorHelpersTest と重複する部分があるが、
こちらはエッジケースをより詳細にカバーする。
"""
from django.test import TestCase
from subekashi.models import Author
from subekashi.lib.author_helpers import get_or_create_authors


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
