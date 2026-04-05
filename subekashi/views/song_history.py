from django.shortcuts import render
from django.core.paginator import Paginator
from django.views import View
from subekashi.models import Song, History
from subekashi.lib.ip import get_ip
from subekashi.constants.constants import HISTORIES_PER_PAGE


class SongHistoryView(View):
    def get(self, request, song_id):
        # Songがなければ404
        song = Song.get_or_none(song_id)
        if song is None:
            return render(request, 'subekashi/404.html', status=404)

        all_histories = History.get_for_song(song)
        paginator = Paginator(all_histories, HISTORIES_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        context = {
            "metatitle": f"{song.title}の編集履歴",
            "song": song,
            "page_obj": page_obj,
            "ip": get_ip(request)
        }

        return render(request, 'subekashi/song_history.html', context)
