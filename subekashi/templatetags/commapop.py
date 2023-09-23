from django import template

register = template.Library()

@register.filter(name='commapop')
def commapop(value):
    l = value.split(',')
    return l[0] if len(l) else ""