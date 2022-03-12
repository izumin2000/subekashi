from distutils.log import info
from django import forms

class FirstviewForm(forms.Form) :
    image = forms.CharField()
    title = forms.CharField()
    player = forms.CharField()