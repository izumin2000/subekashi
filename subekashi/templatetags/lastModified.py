from django import template
from subekashi.models import Singleton

register = template.Library()

@register.simple_tag
def get_last_modified():
    singleton_instance = Singleton.objects.filter(key="lastModified").first()
    if singleton_instance:
        return singleton_instance.value
    return None
