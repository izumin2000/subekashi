from django.template.loader import render_to_string
from django.http import JsonResponse
from subekashi.models import Song
from subekashi.lib.song_filter import song_filter
from django_ratelimit.decorators import ratelimit


@ratelimit(key='ip', rate='2/second', method=['GET', 'POST'], block=True)
def song_cards(request):
    result = []
    query = dict(request.GET)

    # クエリパラメータをクリーンアップ
    cleaned_query = {}
    for key, value in query.items():
        if isinstance(value, list) and len(value) > 0:
            value = value[0]
        cleaned_query[key] = value

    page_value = cleaned_query.get("page")
    page = int(page_value) if page_value and (page_value != 'undefined') else 1
    cleaned_query["count"] = True
    cleaned_query["page"] = page
    song_qs, statistics = song_filter(cleaned_query)

    if page == 1:
        # YouTube関連のフィルター/ソートを見つける
        sort_value = cleaned_query.get('sort')
        has_view_sort = sort_value in ['view', '-view']
        has_like_sort = sort_value in ['like', '-like']
        has_view_lte_filter = 'view_lte' in cleaned_query
        has_like_lte_filter = 'like_lte' in cleaned_query

        # 再生数のフィルター/ソートなら.search-infoを追加
        if has_view_sort or has_view_lte_filter:
            result.append("<p class='search-info'>再生数が1回以上の曲を表示しています</p>")

        # 高評価数のフィルター/ソートなら.search-infoを追加
        if has_like_sort or has_like_lte_filter:
            result.append("<p class='search-info'>高評価数が1以上の曲を表示しています</p>")

        # ヒット数を追加
        result.append(f"<p class='search-info'>{Song.objects.count()}件中{statistics['count']}件ヒットしました</p>")

    for song in song_qs:
        result.append(render_to_string('subekashi/components/song_card.html', {'song': song}))

    if (page != statistics["max_page"]) and statistics["count"]:
        result.append(f"<img id='next-page-loading' src='/static/subekashi/image/loading.gif' alt='loading'></img>")

    return JsonResponse(result, safe=False)