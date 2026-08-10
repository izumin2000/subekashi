"""
lib/author_alias_service.py のテスト

別名のDiscord通知テキスト構築関数を検証する。
"""
from django.test import TestCase
from subekashi.models import Author, AuthorAlias
from subekashi.lib.author_alias_service import (
    build_new_alias_discord_text,
    build_edit_alias_discord_text,
    build_delete_alias_discord_text,
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
