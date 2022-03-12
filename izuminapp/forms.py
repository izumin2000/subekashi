from distutils.log import info
from django import forms

class FirstviewForm(forms.Form) :
    image = forms.CharField()
    title = forms.CharField()
    player = forms.CharField()

class PlayerForm(forms.Form) :
    name = forms.CharField()
    info = forms.CharField()
    rank = forms.CharField()
    primary = forms.BooleanField()
    crime = forms.BooleanField()