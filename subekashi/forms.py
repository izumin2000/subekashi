from django import forms
from django.db.models import Q
from subekashi.models import AuthorAlias


CONTACT_CATEGORY_CHOICES = [
    ("不具合の報告", "不具合の報告"),
    ("提案", "提案"),
    ("質問", "質問"),
    ("その他", "その他"),
]


class ContactForm(forms.Form):
    category = forms.ChoiceField(
        choices=CONTACT_CATEGORY_CHOICES,
        error_messages={
            'required': '入力必須項目を入力してください。',
            'invalid_choice': '入力必須項目を入力してください。',
        },
    )
    detail = forms.CharField(
        widget=forms.Textarea,
        error_messages={'required': '入力必須項目を入力してください。'},
    )


class SongDeleteForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea,
        error_messages={'required': '削除理由を入力してください。'},
    )


class AuthorAliasForm(forms.Form):
    name = forms.CharField(
        max_length=500,
        error_messages={'required': '別名を入力してください。'},
    )
    alias_type = forms.ChoiceField(
        choices=AuthorAlias.CHOICES,
        error_messages={
            'required': '種別を選択してください。',
            'invalid_choice': '種別を選択してください。',
        },
    )

    def __init__(self, *args, author=None, editing_alias=None, **kwargs):
        self.author = author
        self.editing_alias = editing_alias
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name']

        if self.author is not None and name == self.author.name:
            raise forms.ValidationError('作者自身の名前は別名として登録できません。')

        return name

    def clean(self):
        # alias_typeがname以降に定義されているため、cleaned_data['alias_type']が
        # 使えるclean()側で重複チェックを行う（#1044）
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        alias_type = cleaned_data.get('alias_type')
        if name is None or alias_type is None:
            return cleaned_data

        conflict_qs = AuthorAlias.objects.filter(name=name)
        if self.editing_alias is not None:
            conflict_qs = conflict_qs.exclude(pk=self.editing_alias.pk)

        if alias_type == "group" and self.author is not None:
            # 同じグループ名を別のauthorが登録することは許可するが、同じauthorによる
            # 重複登録や、group以外の種別（past/another等）・Authorとの名前衝突は
            # 従来通りブロックする
            conflict_qs = conflict_qs.exclude(Q(alias_type="group") & ~Q(author=self.author))

        if conflict_qs.exists():
            self.add_error('name', 'その別名は既に登録されています。')

        return cleaned_data


class AuthorPrimaryNameForm(forms.Form):
    """一番有名な名義の選択フォーム（#1008）

    選択肢はauthor自身の現在の名前 + alias_type="past"の別名のみ。
    選んだ名前が別のAuthorの名前と衝突する場合、AuthorPrimaryNameSetView側で
    そのAuthorをこのauthorに統合（マージ）した上で名義を切り替える。
    """
    name = forms.CharField(
        max_length=500,
        error_messages={'required': '名義を選択してください。'},
    )

    def __init__(self, *args, author=None, **kwargs):
        self.author = author
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name']

        candidates = {self.author.name} | set(
            self.author.aliases.filter(alias_type="past").values_list("name", flat=True)
        )
        if name not in candidates:
            raise forms.ValidationError('選択できない名義です。')

        return name


class SongEditForm(forms.Form):
    title = forms.CharField(
        max_length=500,
        error_messages={'required': 'タイトルが未入力です。'},
    )
    authors = forms.CharField(
        error_messages={'required': '作者は空白にできません。'},
    )
    url = forms.CharField(required=False)
    imitate = forms.CharField(required=False)
    lyrics = forms.CharField(required=False, widget=forms.Textarea)
    is_original = forms.BooleanField(required=False)
    is_deleted = forms.BooleanField(required=False)
    is_joke = forms.BooleanField(required=False)
    is_inst = forms.BooleanField(required=False)
    is_subeana = forms.BooleanField(required=False)
    is_draft = forms.BooleanField(required=False)
    is_questionable = forms.BooleanField(required=False)
