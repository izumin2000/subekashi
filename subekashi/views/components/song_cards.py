from django.template.loader import render_to_string
from django.http import JsonResponse
from config.settings import *
from subekashi.models import Song
from subekashi.lib.search import song_search


def song_cards(request):
    result = []
    query = dict(request.GET)
    page = int(query.get("page", ['1'])[0])
    query["count"] = True
    query["page"] = page
    try:
        song_qs, statistics = song_search(query)
    except:
        return JsonResponse({}, safe=False)
    
    if page == 1:
        result.append(f"<p>{Song.objects.count()}件中{statistics['count']}件ヒットしました</p>")
        
    for song in song_qs:
        result.append(render_to_string('subekashi/components/song_card.html', {'song': song}))
    
    if page != statistics["max_page"]:
        result.append(f"<img id='loading' src='{ROOT_DIR}/{STATIC_URL}subekashi/image/loading.gif' alt='loading'></img>")
        
    return JsonResponse(result, safe=False)