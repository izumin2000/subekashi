from django.shortcuts import render
from django.core.paginator import Paginator
from django.views import View
from subekashi.models import Editor, History
from subekashi.lib.ip import get_ip
from subekashi.constants.constants import HISTORIES_PER_PAGE


class EditorView(View):
    def get(self, request, editor_id):
        # Editorがなければ404
        editor = Editor.get_or_none(editor_id)
        if editor is None:
            return render(request, 'subekashi/404.html', status=404)

        all_histories = History.get_for_editor(editor)
        paginator = Paginator(all_histories, HISTORIES_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        context = {
            "metatitle": editor,
            "editor": editor,
            "is_me": get_ip(request) == editor.ip,
            "page_obj": page_obj,
            "total_count": paginator.count,
        }

        return render(request, 'subekashi/editor.html', context)
