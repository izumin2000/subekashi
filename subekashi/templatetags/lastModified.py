from django import template

register = template.Library()

@register.simple_tag
def get_last_modified():
    try:
        from subekashi.constants.dynamic.version import VERSION
        return VERSION
    except:
        return "python manage.py constを実行してください"