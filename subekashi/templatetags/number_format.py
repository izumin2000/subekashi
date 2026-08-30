from django import template


register = template.Library()

@register.filter
def intcomma(value):
    if value is None:
        return ""
    try:
        return f"{value:,}"
    except (TypeError, ValueError):
        return value
