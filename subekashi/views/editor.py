from django.shortcuts import render
from django.core.paginator import Paginator
from subekashi.models import Editor, History
from subekashi.lib.ip import get_ip

HISTORIES_PER_PAGE = 50


def editor(request, editor_id):
    # Editorがなければ404
    try :
        editor = Editor.objects.get(pk = editor_id)
    except :
        return render(request, 'subekashi/404.html', status=404)

    all_histories = History.objects.select_related("song").filter(editor=editor).order_by("-create_time")
    paginator = Paginator(all_histories, HISTORIES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    detaD = {
        "metatitle" : editor,
        "editor": editor,
        "is_me": get_ip(request) == editor.ip,
        "page_obj": page_obj,
        "total_count": paginator.count,
    }

    return render(request, 'subekashi/editor.html', detaD)