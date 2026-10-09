from django import template
from django.templatetags.static import static
from django.urls import reverse
from config.settings import ROOT_URL
from subekashi.lib.ogp import make_ogp_token

register = template.Library()

@register.simple_tag
def get_ogp_image_url(metatitle):
    if not metatitle:
        return f"{ROOT_URL}{static('subekashi/image/ogp.png')}"
    return f"{ROOT_URL}{reverse('subekashi:ogp_image', args=[make_ogp_token(metatitle)])}"
