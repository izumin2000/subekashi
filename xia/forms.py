from distutils.log import info
from django import forms

class PlayerForm(forms.Form) :
    name = forms.CharField(label="プレイヤー名")
    info = forms.CharField(label="説明", required=False, widget=forms.Textarea())
    password = forms.CharField(label="パスワード")

class MinisterForm(forms.Form) :
    name = forms.CharField(label="プレイヤー名")
    title = forms.CharField(label="身分")
    password = forms.CharField(label="パスワード")