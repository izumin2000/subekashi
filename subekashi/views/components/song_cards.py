from django.template.loader import render_to_string
from django.http import JsonResponse
from subekashi.models import Song
from subekashi.lib.song_filter import song_filter
from subekashi.lib.query_utils import (
    clean_query_params,
    has_view_filter_or_sort,
    has_like_filter_or_sort,
)
from django_ratelimit.decorators import ratelimit
from rest_framework.exceptions import ValidationError


def get_active_filters(query):
    """
    クエリパラメータから有効なフィルターのラベルを取得
    keywordとsortは除外
    """
    filter_labels = {
        'title': 'タイトル',
        'author': '作者名',
        'lyrics': '歌詞',
        'url': 'URL',
        'imitate': '模倣',
        'view_gte': '再生回数/以上',
        'view_lte': '再生回数/以下',
        'like_gte': '高評価数/以上',
        'like_lte': '高評価数/以下',
        'upload_time_gte': '投稿日/以降',
        'upload_time_lte': '投稿日/以前',
        'issubeana': '界隈曲の種類',
        'isjoke': 'ネタ曲',
        'mediatypes': 'メディア',
        'islack': '作成途中',
        'isdraft': '下書き',
        'isoriginal': 'オリジナル模倣曲',
        'isinst': 'インスト曲',
        'isdeleted': '非公開/削除済み',
    }

    active = []
    for param, label in filter_labels.items():
        if param in query and query[param]:
            active.append(label)

    return '・'.join(active) if active else ''


@ratelimit(key='ip', rate='2/second', method=['GET', 'POST'], block=True)
def song_cards(request):
    result = []
    query = dict(request.GET)

    # クエリパラメータをクリーンアップ
    cleaned_query = clean_query_params(query)

    page_value = cleaned_query.get("page")
    page = int(page_value) if page_value and (page_value != 'undefined') else 1
    cleaned_query["count"] = True
    cleaned_query["page"] = page

    try:
        song_qs, statistics = song_filter(cleaned_query)
    except ValidationError as e:
        # バリデーションエラーをHTMLとして返す
        error_detail = e.detail
        if isinstance(error_detail, dict) and "error" in error_detail:
            error_message = error_detail["error"]
        else:
            error_message = str(error_detail)
        result.append(f"<p class='error'>エラー: {error_message}</p>")
        return JsonResponse(result, safe=False)

    if page == 1:
        # アクティブなフィルターを表示
        active_filters = get_active_filters(cleaned_query)
        if active_filters:
            result.append(f"<p class='search-info'>{active_filters}が有効です</p>")

        # 再生数のフィルター/ソートなら.search-infoを追加
        if has_view_filter_or_sort(cleaned_query):
            result.append("<p class='search-info'>再生数が1回以上の曲を表示しています</p>")

        # 高評価数のフィルター/ソートなら.search-infoを追加
        if has_like_filter_or_sort(cleaned_query):
            result.append("<p class='search-info'>高評価数が1以上の曲を表示しています</p>")
        
        # ヒット数以外の何かしらの検索情報があれば水平線を画面に表示する
        if result:
            result.append("<hr>")

        # ヒット数を追加
        result.append(f"<p class='search-count'>{Song.objects.count()}件中{statistics['count']}件ヒットしました</p>")

    for song in song_qs:
        result.append(render_to_string('subekashi/components/song_card.html', {'song': song}))

    if (page != statistics["max_page"]) and statistics["count"]:
        result.append(f"<img id='next-page-loading' src='/static/subekashi/image/loading.gif' alt='loading'></img>")

    return JsonResponse(result, safe=False)