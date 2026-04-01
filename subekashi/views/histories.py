from django.shortcuts import render
from django.core.paginator import Paginator
from subekashi.models import Editor, History
from subekashi.lib.ip import get_ip
from subekashi.constants.constants import HISTORIES_PER_PAGE


def histories(request):
    search_query = request.GET.get("q", "").strip()
    all_histories = History.get_all(search_query)

    paginator = Paginator(all_histories, HISTORIES_PER_PAGE)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    ip = get_ip(request)
    my_editor = Editor.get_by_ip(ip)

    dataD = {
        "metatitle": "編集履歴",
        "page_obj": page_obj,
        "ip": ip,
        "my_editor": my_editor,
        "search_query": search_query,
    }

    return render(request, "subekashi/histories.html", dataD)
