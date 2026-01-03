"""
Django-filterベースの検索実装
"""
import math
from subekashi.lib.filters import SongFilter
from subekashi.models import Song

DEFALT_SIZE = 50  # 1度の検索で取得できるsongオブジェクトの数


def song_filter(querys):
    """
    django-filterを使用して楽曲をフィルタリング・検索する

    Args:
        querys: クエリパラメータの辞書

    Returns:
        (queryset, statistics_dict)のタプル
    """
    statistics = {}

    # クエリパラメータをクリーンアップ - リスト値を処理
    cleaned_querys = {}
    for key, value in querys.items():
        # 値がリストの場合、最初の要素を取得
        if isinstance(value, list) and len(value) > 0:
            value = value[0]

        cleaned_querys[key] = value

    # django-filterを適用
    filterset = SongFilter(cleaned_querys, queryset=Song.objects.all())
    song_qs = filterset.qs

    # 結果をカウント
    count = song_qs.count()

    # リクエストされている場合、統計情報にカウントを追加
    if cleaned_querys.get("count"):
        statistics["count"] = count

    # ページネーション処理
    try:
        page = int(cleaned_querys.get("page", 1))
    except (ValueError, TypeError):
        page = 1

    try:
        size = int(cleaned_querys.get("size", DEFALT_SIZE))
    except (ValueError, TypeError):
        size = DEFALT_SIZE

    statistics["page"] = page
    statistics["size"] = size
    max_page = math.ceil(count / size) if size > 0 else 1
    statistics["max_page"] = max_page

    # ページネーションのスライスを適用
    start = (page - 1) * size
    end = page * size
    song_qs = song_qs[start:end]

    return song_qs, statistics
