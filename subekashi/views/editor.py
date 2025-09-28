from django.shortcuts import render
from subekashi.models import Editor


def editor(request, editor_id):
    # Editorがなければ404
    try :
        editor = Editor.objects.get(pk = editor_id)
    except :
        return render(request, 'subekashi/404.html', status=404)

    return render(request, 'subekashi/editor.html', {"editor": editor})