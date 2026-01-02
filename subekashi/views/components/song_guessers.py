from django.template.loader import render_to_string
from django.http import JsonResponse
from subekashi.lib.search_filter import song_search
from django_ratelimit.decorators import ratelimit


SIZE = 50
@ratelimit(key='ip', rate='2/second', method=['GET', 'POST'], block=True)
def song_guessers(request):
    result = []
    query = dict(request.GET)
    query["size"] = SIZE
    query["count"] = True
    song_qs, statistics = song_search(query)
    for song in song_qs:
        result.append(render_to_string('subekashi/components/song_guesser.html', {'song': song}))
    
    if statistics["count"] > SIZE:
        message = "これ以上の候補を表示する為には条件を絞ってください。"
    if statistics["count"] > 0:
        message = "これ以上の検索結果はありません。<br>ヒットしなかったり、追加できない場合、一度下書きとして登録してから再読み込みしてください。"
    else:
        message = "検索結果はありません。<br>ヒットしなかったり、追加できない場合、一度下書きとして登録してから再読み込みしてください。"
    result.append(f"<p>{message}</p>")
    return JsonResponse(result, safe=False)