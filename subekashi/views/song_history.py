from django.shortcuts import render
from django.core.paginator import Paginator
from subekashi.models import *
from subekashi.lib.ip import get_ip
from subekashi.constants.constants import HISTORIES_PER_PAGE


def song_history(request, song_id):
    # Songがなければ404
    try :
        song = Song.objects.get(pk = song_id)
    except :
        return render(request, 'subekashi/404.html', status=404)

    all_histories = History.objects.select_related("editor").filter(song=song).order_by("-create_time")
    paginator = Paginator(all_histories, HISTORIES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    dataD = {
        "metatitle": f"{song.title}の編集履歴",
        "song": song,
        "page_obj": page_obj,
        "ip": get_ip(request)
    }

    return render(request, 'subekashi/song_history.html', dataD)
