from django.shortcuts import render
from subekashi.models import Editor, History
from subekashi.lib.ip import get_ip


def editor(request, editor_id):
    # Editorがなければ404
    try :
        editor = Editor.objects.get(pk = editor_id)
    except :
        return render(request, 'subekashi/404.html', status=404)
    
    detaD = {
        "metatitle" : editor,
        "editor": editor,
        "is_me": get_ip(request) == editor.ip,
        "historys": History.objects.filter(editor = editor).order_by("-create_time")
    }

    return render(request, 'subekashi/editor.html', detaD)