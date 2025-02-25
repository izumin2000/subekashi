from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.simple_tag
def get_toast(icon, text):
    if not text:
        return
    
    ICON_DICT = {
        "info": "fas fa-info-circle info",
        "ok": "fas fa-check-circle ok",
        "warning": "fas fa-exclamation-triangle warning",
        "error": "fas fa-ban error"
    }
    icon_class = ICON_DICT[icon] if icon in ICON_DICT else ""
    toast_class = "toast" if len(text) < 50 else "toast long-time"
    context = {
        "toast_class": toast_class,
        "icon_class": icon_class,
        "text": text
    }
    return render_to_string('subekashi/components/toast.html', context)