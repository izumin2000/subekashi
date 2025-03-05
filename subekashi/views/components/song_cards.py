from django.template.loader import render_to_string
from django.http import JsonResponse
from subekashi.models import Song
from subekashi.lib.search import song_search
from django_ratelimit.decorators import ratelimit


@ratelimit(key='ip', rate='2/second', method=['GET', 'POST'], block=True)
def song_cards(request):
    result = []
    query = dict(request.GET)
    page = int(query.get("page", ['1'])[0])
    query["count"] = True
    query["page"] = page
    song_qs, statistics = song_search(query)
    
    if page == 1:
        result.append(f"<p>{Song.objects.count()}件中{statistics['count']}件ヒットしました</p>")
    
    sort = query.get("sort")
    if (page == 1) and ("view" in sort):
        result.append("<p class='warning'><i class='warning fas fa-exclamation-triangle'></i>システムの都合上、再生回数が1回以上の曲を表示しています。</p>")
    
    if (page == 1) and ("like" in sort):
        result.append("<p class='warning'><i class='warning fas fa-exclamation-triangle'></i>システムの都合上、高評価数が1回以上の曲を表示しています。</p>")
        
    for song in song_qs:
        result.append(render_to_string('subekashi/components/song_card.html', {'song': song}))
    
    if page != statistics["max_page"]:
        result.append(f"<img id='loading' src='/static/subekashi/image/loading.gif' alt='loading'></img>")
        
    return JsonResponse(result, safe=False)