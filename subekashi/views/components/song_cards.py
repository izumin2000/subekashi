from django.template.loader import render_to_string
from django.http import JsonResponse
from subekashi.models import Song
from subekashi.lib.song_filter import song_filter
from django_ratelimit.decorators import ratelimit


@ratelimit(key='ip', rate='2/second', method=['GET', 'POST'], block=True)
def song_cards(request):
    result = []
    query = dict(request.GET)
    page = int(query.get("page")[0]) if query.get("page") and (query.get("page") != ['undefined']) else 1
    query["count"] = True
    query["page"] = page
    song_qs, statistics = song_filter(query)
    
    if page == 1:
        result.append(f"<p id='search-info'>{Song.objects.count()}件中{statistics['count']}件ヒットしました</p>")
    
    for song in song_qs:
        result.append(render_to_string('subekashi/components/song_card.html', {'song': song}))
    
    if (page != statistics["max_page"]) and statistics["count"]:
        result.append(f"<img id='next-page-loading' src='/static/subekashi/image/loading.gif' alt='loading'></img>")
        
    return JsonResponse(result, safe=False)