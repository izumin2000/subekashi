from django import template
from django.template.loader import render_to_string
from subekashi.models import History
from subekashi.constants.constants import EDIT_CHANGES_HEADER


register = template.Library()
@register.simple_tag
def render_changes(history):
    history = History.objects.get(pk = history.id)
    changes = history.changes
    context = {
        "is_delete": history.history_type == "delete",
        # 編集前と編集後の差分をJS（editor.js）で表示する。以前は編集もhistory_type="new"で保存していたため、見出しで判定する
        "is_edit": isinstance(changes, list) and bool(changes) and changes[0] == EDIT_CHANGES_HEADER,
        "changes": changes
    }
    return render_to_string('subekashi/components/changes.html', context)
