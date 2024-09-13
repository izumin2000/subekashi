from django import template
from subekashi.constants.view import *

register = template.Library()

@register.simple_tag
def get_last_modified():
    try:
        from subekashi.constants.dynamic.version import VERSION
        return VERSION
    except:
        return CONST_ERROR