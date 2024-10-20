from django import template
from django.template.loader import render_to_string
from subekashi.models import Song


register = template.Library()
@register.simple_tag
def render_categorys():
    song_qs = Song.objects.filter(id__lte = 30, channel = "全てあなたの所為です。") 
    context = {
        "song_qs" : song_qs
    }
    return render_to_string('subekashi/components/categorys.html', context)


@register.simple_tag
def clean_title(title):
    TITLES = {
        "DSC_0001.AVI": "DSC",
        "教育 (CXXXII Ver.)": "教育132",
        "アブジェ (CXXXII Ver.)": "アブジェ132",
        "名の無い星が空に堕ちたら": "名の無い星"
    }
    
    if title in TITLES.keys():
        title = TITLES[title]
    return title