from distutils.log import info
from django import forms

class FirstviewForm(forms.Form) :
    image = forms.CharField(label="ファイル名")
    title = forms.CharField(label="タイトル")
    player = forms.CharField(label="プレイヤー")
    password = forms.CharField(label="パスワード")

class PlayerForm(forms.Form) :
    name = forms.CharField(label="プレイヤー名")
    rank = forms.CharField(label="身分")
    primary = forms.BooleanField(label="大臣？")
    crime = forms.BooleanField(label="指名手配犯？")
    info = forms.CharField(label="説明")
    password = forms.CharField(label="パスワード")