from django.template.loader import render_to_string
from django.http import JsonResponse
from subekashi.lib.song_filter import song_filter
from django_ratelimit.decorators import ratelimit
from rest_framework.exceptions import ValidationError


SIZE = 50
@ratelimit(key='ip', rate='2/second', method=['GET', 'POST'], block=True)
def song_guessers(request):
    result = []
    query = dict(request.GET)
    query["size"] = SIZE
    query["count"] = True

    try:
        song_qs, statistics = song_filter(query)
    except ValidationError as e:
        # バリデーションエラーをHTMLとして返す
        error_detail = e.detail
        if isinstance(error_detail, dict) and "error" in error_detail:
            error_message = error_detail["error"]
        else:
            error_message = str(error_detail)
        result.append(f"<p class='error'>エラー: {error_message}</p>")
        return JsonResponse(result, safe=False)

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