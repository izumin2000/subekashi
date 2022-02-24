from django.forms import ModelForm
from izuminapp.model import Firstview

class FirstviewForm (ModelForm) :
    class Meta :
        model = Firstview
        fields = ("image", "title", "player")