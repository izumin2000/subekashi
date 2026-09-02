"""
forms.py のテスト

ContactForm, SongDeleteForm, SongEditForm, AuthorAliasForm のバリデーションを検証する。
ContactForm/SongDeleteForm/SongEditFormはDBアクセスしないため SimpleTestCase を使用するが、
AuthorAliasFormはclean_name()で重複チェックのためDBアクセスするため TestCase を使用する。
"""
from django.test import SimpleTestCase, TestCase
from subekashi.forms import AuthorAliasForm, AuthorPrimaryNameForm, ContactForm, SongDeleteForm, SongEditForm
from subekashi.models import Author, AuthorAlias


class ContactFormTest(SimpleTestCase):
    """ContactForm のテスト"""

    def _make_data(self, category="不具合の報告", detail="詳細内容です"):
        return {"category": category, "detail": detail}

    def test_valid_form(self):
        form = ContactForm(data=self._make_data())
        self.assertTrue(form.is_valid())

    def test_all_category_choices_are_valid(self):
        for category in ["不具合の報告", "提案", "質問", "その他"]:
            form = ContactForm(data=self._make_data(category=category))
            self.assertTrue(form.is_valid(), f"カテゴリ '{category}' が無効と判定された")

    def test_empty_category_is_invalid(self):
        form = ContactForm(data=self._make_data(category=""))
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_invalid_category_is_invalid(self):
        form = ContactForm(data=self._make_data(category="不正な選択肢"))
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_empty_detail_is_invalid(self):
        form = ContactForm(data=self._make_data(detail=""))
        self.assertFalse(form.is_valid())
        self.assertIn("detail", form.errors)

    def test_empty_detail_error_message(self):
        form = ContactForm(data=self._make_data(detail=""))
        form.is_valid()
        self.assertIn("入力必須項目を入力してください。", form.errors["detail"])

    def test_missing_category_error_message(self):
        form = ContactForm(data={"detail": "詳細"})
        form.is_valid()
        self.assertIn("入力必須項目を入力してください。", form.errors["category"])

    def test_detail_max_length_10000_is_valid(self):
        form = ContactForm(data=self._make_data(detail="あ" * 10000))
        self.assertTrue(form.is_valid())

    def test_detail_over_10000_chars_is_invalid(self):
        form = ContactForm(data=self._make_data(detail="あ" * 10001))
        self.assertFalse(form.is_valid())
        self.assertIn("detail", form.errors)


class SongDeleteFormTest(SimpleTestCase):
    """SongDeleteForm のテスト"""

    def test_valid_form(self):
        form = SongDeleteForm(data={"reason": "削除すべき理由があります"})
        self.assertTrue(form.is_valid())

    def test_empty_reason_is_invalid(self):
        form = SongDeleteForm(data={"reason": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("reason", form.errors)

    def test_empty_reason_error_message(self):
        form = SongDeleteForm(data={"reason": ""})
        form.is_valid()
        self.assertIn("削除理由を入力してください。", form.errors["reason"])

    def test_missing_reason_is_invalid(self):
        form = SongDeleteForm(data={})
        self.assertFalse(form.is_valid())


class SongEditFormTest(SimpleTestCase):
    """SongEditForm のテスト"""

    def _make_data(self, **kwargs):
        defaults = {
            "title": "テスト曲タイトル",
            "authors": "テスト作者",
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_form_with_required_fields_only(self):
        form = SongEditForm(data=self._make_data())
        self.assertTrue(form.is_valid())

    def test_empty_title_is_invalid(self):
        form = SongEditForm(data=self._make_data(title=""))
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_empty_title_error_message(self):
        form = SongEditForm(data=self._make_data(title=""))
        form.is_valid()
        self.assertIn("タイトルが未入力です。", form.errors["title"])

    def test_empty_authors_is_invalid(self):
        form = SongEditForm(data=self._make_data(authors=""))
        self.assertFalse(form.is_valid())
        self.assertIn("authors", form.errors)

    def test_empty_authors_error_message(self):
        form = SongEditForm(data=self._make_data(authors=""))
        form.is_valid()
        self.assertIn("作者は空白にできません。", form.errors["authors"])

    def test_url_is_optional(self):
        form = SongEditForm(data=self._make_data(url=""))
        self.assertTrue(form.is_valid())

    def test_imitate_is_optional(self):
        form = SongEditForm(data=self._make_data(imitate=""))
        self.assertTrue(form.is_valid())

    def test_lyrics_is_optional(self):
        form = SongEditForm(data=self._make_data(lyrics=""))
        self.assertTrue(form.is_valid())

    def test_title_max_length_500_is_valid(self):
        form = SongEditForm(data=self._make_data(title="あ" * 500))
        self.assertTrue(form.is_valid())

    def test_title_over_500_chars_is_invalid(self):
        form = SongEditForm(data=self._make_data(title="あ" * 501))
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_lyrics_max_length_10000_is_valid(self):
        form = SongEditForm(data=self._make_data(lyrics="あ" * 10000))
        self.assertTrue(form.is_valid())

    def test_lyrics_over_10000_chars_is_invalid(self):
        form = SongEditForm(data=self._make_data(lyrics="あ" * 10001))
        self.assertFalse(form.is_valid())
        self.assertIn("lyrics", form.errors)

    def test_boolean_flag_is_original_true(self):
        form = SongEditForm(data=self._make_data(is_original=True))
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data["is_original"])

    def test_boolean_flags_default_to_false(self):
        form = SongEditForm(data=self._make_data())
        form.is_valid()
        for field in ["is_original", "is_deleted", "is_joke", "is_inst", "is_subeana", "is_draft", "is_questionable"]:
            self.assertFalse(form.cleaned_data[field], f"{field} のデフォルトが False でない")

    def test_boolean_flag_is_questionable_true(self):
        form = SongEditForm(data=self._make_data(is_questionable=True))
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data["is_questionable"])

    def test_all_optional_fields_provided(self):
        form = SongEditForm(data=self._make_data(
            url="https://youtu.be/dQw4w9WgXcQ",
            imitate="1,2,3",
            lyrics="テスト歌詞\nライン2",
            is_original=True,
            is_joke=False,
        ))
        self.assertTrue(form.is_valid())


class AuthorAliasFormTest(TestCase):
    """AuthorAliasForm のテスト"""

    def setUp(self):
        self.author = Author.objects.create(name="フォームテスト作者")

    def _make_data(self, **kwargs):
        defaults = {"name": "別名A", "alias_type": "past"}
        defaults.update(kwargs)
        return defaults

    def test_valid_form(self):
        form = AuthorAliasForm(data=self._make_data(), author=self.author)
        self.assertTrue(form.is_valid())

    def test_empty_name_is_invalid(self):
        form = AuthorAliasForm(data=self._make_data(name=""), author=self.author)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_invalid_alias_type_is_invalid(self):
        form = AuthorAliasForm(data=self._make_data(alias_type="不正な種別"), author=self.author)
        self.assertFalse(form.is_valid())
        self.assertIn("alias_type", form.errors)

    def test_all_choice_values_are_valid(self):
        for value, _label in AuthorAlias.CHOICES:
            form = AuthorAliasForm(data=self._make_data(alias_type=value), author=self.author)
            self.assertTrue(form.is_valid(), f"alias_type '{value}' が無効と判定された")

    def test_name_same_as_author_name_is_invalid(self):
        form = AuthorAliasForm(data=self._make_data(name=self.author.name), author=self.author)
        self.assertFalse(form.is_valid())
        self.assertIn("作者自身の名前は別名として登録できません。", form.errors["name"])

    def test_duplicate_name_is_invalid(self):
        AuthorAlias.objects.create(name="既存別名", author=self.author)
        form = AuthorAliasForm(data=self._make_data(name="既存別名"), author=self.author)
        self.assertFalse(form.is_valid())
        self.assertIn("その別名は既に登録されています。", form.errors["name"])

    def test_editing_alias_excludes_itself_from_duplicate_check(self):
        alias = AuthorAlias.objects.create(name="編集対象別名", author=self.author)
        form = AuthorAliasForm(
            data=self._make_data(name="編集対象別名"), author=self.author, editing_alias=alias,
        )
        self.assertTrue(form.is_valid())

    def test_editing_alias_still_detects_duplicate_with_other_alias(self):
        AuthorAlias.objects.create(name="別の既存別名", author=self.author)
        alias = AuthorAlias.objects.create(name="編集対象別名2", author=self.author)
        form = AuthorAliasForm(
            data=self._make_data(name="別の既存別名"), author=self.author, editing_alias=alias,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("その別名は既に登録されています。", form.errors["name"])

    def test_group_name_can_be_registered_by_another_author(self):
        # alias_type="group"は、既に別のauthorが同じ名前で登録していても許可する（#1044）
        other_author = Author.objects.create(name="グループ他メンバー")
        AuthorAlias.objects.create(name="合作グループA", author=other_author, alias_type="group")

        form = AuthorAliasForm(
            data=self._make_data(name="合作グループA", alias_type="group"), author=self.author,
        )
        self.assertTrue(form.is_valid())

    def test_same_author_cannot_register_same_group_name_twice(self):
        # 同じauthorによる同じグループ名の重複登録は従来通りブロックする（#1044）
        AuthorAlias.objects.create(name="合作グループB", author=self.author, alias_type="group")

        form = AuthorAliasForm(
            data=self._make_data(name="合作グループB", alias_type="group"), author=self.author,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("その別名は既に登録されています。", form.errors["name"])

    def test_group_name_conflicting_with_non_group_alias_is_blocked(self):
        # グループ名がgroup以外の既存別名と衝突する場合は従来通りブロックする（#1044）
        other_author = Author.objects.create(name="非グループ登録者")
        AuthorAlias.objects.create(name="表記揺れ名", author=other_author, alias_type="spell")

        form = AuthorAliasForm(
            data=self._make_data(name="表記揺れ名", alias_type="group"), author=self.author,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("その別名は既に登録されています。", form.errors["name"])

    def test_non_group_name_conflicting_with_existing_group_alias_is_blocked(self):
        # 既存のgroup別名と同名で、group以外の種別を新規登録しようとする場合は
        # 従来通りブロックする（groupの緩和はgroup同士の組み合わせに限定する、#1044）
        other_author = Author.objects.create(name="グループ登録者")
        AuthorAlias.objects.create(name="合作グループC", author=other_author, alias_type="group")

        form = AuthorAliasForm(
            data=self._make_data(name="合作グループC", alias_type="past"), author=self.author,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("その別名は既に登録されています。", form.errors["name"])


class AuthorPrimaryNameFormTest(TestCase):
    """AuthorPrimaryNameForm のテスト（#1008）"""

    def setUp(self):
        self.author = Author.objects.create(name="現在の名義")

    def test_current_name_is_valid(self):
        form = AuthorPrimaryNameForm(data={"name": self.author.name}, author=self.author)
        self.assertTrue(form.is_valid())

    def test_past_alias_name_is_valid(self):
        AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")
        form = AuthorPrimaryNameForm(data={"name": "以前の名義"}, author=self.author)
        self.assertTrue(form.is_valid())

    def test_non_past_alias_name_is_invalid(self):
        # another等、past以外の種別は候補にならない
        AuthorAlias.objects.create(name="別名義", author=self.author, alias_type="another")
        form = AuthorPrimaryNameForm(data={"name": "別名義"}, author=self.author)
        self.assertFalse(form.is_valid())
        self.assertIn("選択できない名義です。", form.errors["name"])

    def test_unrelated_name_is_invalid(self):
        form = AuthorPrimaryNameForm(data={"name": "全く関係ない名前"}, author=self.author)
        self.assertFalse(form.is_valid())
        self.assertIn("選択できない名義です。", form.errors["name"])

    def test_past_alias_name_conflicting_with_another_author_is_valid(self):
        # past別名の名前と完全一致する別のAuthorが既に存在していても選択可能。
        # 衝突するAuthorの統合（マージ）はAuthorPrimaryNameSetView側で行う（#1029）
        Author.objects.create(name="衝突する名前")
        AuthorAlias.objects.create(name="衝突する名前", author=self.author, alias_type="past")
        form = AuthorPrimaryNameForm(data={"name": "衝突する名前"}, author=self.author)
        self.assertTrue(form.is_valid())
