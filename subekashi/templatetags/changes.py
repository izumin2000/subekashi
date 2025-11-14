from django import template
from django.template.loader import render_to_string
from subekashi.models import History


register = template.Library()
@register.simple_tag
def render_changes(history):
    changes = History.objects.get(pk = history.id).temp_changes
    context = {
        "changes" : changes
    }
    return render_to_string('subekashi/components/changes.html', context)