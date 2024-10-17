from django import template
from django.template.loader import render_to_string


register = template.Library()
@register.simple_tag
def render_categorys():
    return render_to_string('subekashi/components/categorys.html')