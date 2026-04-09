"""
forms.py のテスト

ContactForm, SongDeleteForm, SongEditForm のバリデーションを検証する。
フォームはDBアクセスしないため SimpleTestCase を使用する。
"""
from django.test import SimpleTestCase
from subekashi.forms import ContactForm, SongDeleteForm, SongEditForm


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

    def test_boolean_flag_is_original_true(self):
        form = SongEditForm(data=self._make_data(is_original=True))
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data["is_original"])

    def test_boolean_flags_default_to_false(self):
        form = SongEditForm(data=self._make_data())
        form.is_valid()
        for field in ["is_original", "is_deleted", "is_joke", "is_inst", "is_subeana", "is_draft"]:
            self.assertFalse(form.cleaned_data[field], f"{field} のデフォルトが False でない")

    def test_all_optional_fields_provided(self):
        form = SongEditForm(data=self._make_data(
            url="https://youtu.be/dQw4w9WgXcQ",
            imitate="1,2,3",
            lyrics="テスト歌詞\nライン2",
            is_original=True,
            is_joke=False,
        ))
        self.assertTrue(form.is_valid())
