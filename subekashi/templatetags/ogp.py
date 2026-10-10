from django import template
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from subekashi.lib.ogp import OGP_VERSION, make_ogp_token, normalize_title

register = template.Library()

@register.simple_tag
def get_ogp_image_url(metatitle):
    title = normalize_title(metatitle) if metatitle else ""
    if not title:
        return f"{settings.ROOT_URL}{static('subekashi/image/ogp.png')}"
    return f"{settings.ROOT_URL}{reverse('subekashi:ogp_image', args=[make_ogp_token(title)])}?v={OGP_VERSION}"
