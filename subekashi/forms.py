from django import forms


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
