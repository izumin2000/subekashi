from distutils.log import info
from django import forms

class FirstviewForm(forms.Form) :
    name = forms.CharField(label="ファイル名")
    title = forms.CharField(label="タイトル", required=False)
    player = forms.CharField(label="プレイヤー", required=False)
    displayon = forms.BooleanField(label="表示する", required=False)
    displayoff = forms.BooleanField(label="非表示にする", required=False)
    delete = forms.BooleanField(label="削除する", required=False)
    password = forms.CharField(label="パスワード")

class PlayerForm(forms.Form) :
    name = forms.CharField(label="プレイヤー名")
    rank = forms.CharField(label="身分")
    primary = forms.BooleanField(label="大臣？", required=False)
    crime = forms.BooleanField(label="指名手配犯？", required=False)
    info = forms.CharField(label="説明", required=False, widget=forms.Textarea())
    password = forms.CharField(label="パスワード")