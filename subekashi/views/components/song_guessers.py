from django.template.loader import render_to_string
from django.http import JsonResponse
from subekashi.lib.search import song_search


SIZE = 50
def song_guessers(request):
    result = []
    query = dict(request.GET)
    query["size"] = SIZE
    query["count"] = True
    song_qs, statistics = song_search(query)
    for song in song_qs:
        result.append(render_to_string('subekashi/components/song_guesser.html', {'song': song}))
    
    if statistics["count"] > SIZE:
        message = "最大表示件数に達しました。これ以上の候補を表示するには条件を絞ってください。"
    else:
        message = "これ以上の検索結果はありません。"
    result.append(f"<p>{message}</p>")
    return JsonResponse(result, safe=False)