from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from subekashi.constants.constants import LONG_TERM_COOKIE_AGE, SORT_CHOICES
from subekashi.lib.kenreki_service import compute_kenreki_for_songs
from subekashi.lib.query_utils import YOUTUBE_SORTS
from subekashi.lib.song_filterset import order_by_sort_with_missing_last
from subekashi.lib.stats_service import get_view_like_pairs
from subekashi.models import Author, Song


SORT_VALUES = {choice['value'] for choice in SORT_CHOICES}
DEFAULT_SORT = '-id'
SORT_COOKIE_NAME = 'author_sort'


# 並び替えと、cookieに保存する並び替え（保存しない場合はNone）を返す
# 曲の検索画面と同様に、URLクエリで指定された並び替えは「検索の選択肢の保存」の設定が保存の場合のみcookieに保存する
def resolve_sort(request):
    is_saved_select = request.COOKIES.get('is_saved_select', 'on') == 'on'

    sort = request.GET.get('sort')
    if sort:
        if sort not in SORT_VALUES:
            return DEFAULT_SORT, None
        return sort, sort if is_saved_select else None

    if not is_saved_select:
        return DEFAULT_SORT, None
    cookie_sort = request.COOKIES.get(SORT_COOKIE_NAME)
    return (cookie_sort if cookie_sort in SORT_VALUES else DEFAULT_SORT), None


# 並び替えはcookieによって変わるため、キャッシュされた古い並び順を表示しないようにする
@method_decorator(never_cache, name='dispatch')
class AuthorView(View):
    def get(self, request, author_id):
        # Author IDで検索、存在しなければ404
        author_obj = Author.get_or_none(author_id)
        if author_obj is None:
            return render(request, 'subekashi/404.html', status=404)
        author_name = author_obj.name

        author_songs = Song.get_for_author(author_id)
        sort, sort_to_save = resolve_sort(request)
        songInsL = order_by_sort_with_missing_last(author_songs, sort)

        # 説明文は並び替えによって変わらないよう、登録日の遅い順の曲名にする
        titles = ", ".join(author_songs.values_list('title', flat=True))
        if len(titles) >= 80:
            titles = titles[:80] + "...など"

        view_like_pairs = get_view_like_pairs(author_songs)
        kenreki = None
        if view_like_pairs:
            kenreki = compute_kenreki_for_songs(view_like_pairs)

        context = {
            "metatitle": author_name,
            "author": author_name,
            "author_id": author_obj.id,
            "songInsL": songInsL,
            "SORT_CHOICES": SORT_CHOICES,
            "sort": sort,
            "is_youtube_sort": sort in YOUTUBE_SORTS,
            "alias_count": len(author_obj.get_transitive_aliases()),
            "kenreki": kenreki,
            "description": f"{author_name}の曲一覧：{titles}",
        }
        response = render(request, "subekashi/author.html", context)

        if sort_to_save:
            response.set_cookie(
                SORT_COOKIE_NAME,
                sort_to_save,
                max_age=LONG_TERM_COOKIE_AGE,
                path='/',
                samesite='Lax'
            )

        return response
