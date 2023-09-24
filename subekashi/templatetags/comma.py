from django import template

register = template.Library()

@register.filter(name='iscomma')
def iscomma(value):
    value = value.replace(", ", ",")
    l = value.split(',')
    return len(l) >= 2

@register.filter(name='commapop')
def commapop(value):
    value = value.replace(", ", ",")
    l = value.split(',')
    return l[0] if len(l) else ""