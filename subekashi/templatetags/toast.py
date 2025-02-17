from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.simple_tag
def get_toast(icon, text):
    if not text:
        return
    
    ICON_DICT = {
        "ok": "fas fa-check-square ok",
        "warning": "fas fa-exclamation-triangle warning",
        "error": "fas fa-times-circle error"
    }
    icon_class = ICON_DICT[icon] if icon in ICON_DICT else ""
    context = {
        "icon_class": icon_class,
        "text": text
    }
    return render_to_string('subekashi/components/toast.html', context)