"""
クエリパラメータ関連のユーティリティ関数
"""

# YouTube関連のフィルタ・並び替え（指定され、mediatypesが無い場合はYouTubeの曲のみに絞り込む）
# 曲の検索画面(songs.js)でも、自動で適用されるフィルタの案内に使用する
YOUTUBE_FILTERS = ['view_gte', 'view_lte', 'like_gte', 'like_lte', 'upload_time_gte', 'upload_time_lte']
YOUTUBE_SORTS = ['view', '-view', 'like', '-like', 'upload_time', '-upload_time']


def clean_query_params(query_params):
    """
    クエリパラメータをクリーンアップ

    リスト形式の値（例: request.GETから取得した値）を
    単一の値に変換する

    Args:
        query_params: クエリパラメータの辞書

    Returns:
        dict: クリーンアップされたクエリパラメータ
    """
    cleaned_query = {}
    for key, value in query_params.items():
        # 値がリストの場合、最初の要素を取得
        if isinstance(value, list) and len(value) > 0:
            value = value[0]
        cleaned_query[key] = value
    return cleaned_query


def has_youtube_filter_or_sort(query_data):
    """
    YouTube関連のフィルタまたはソートが存在するかチェック

    Args:
        query_data: クエリパラメータの辞書

    Returns:
        bool: YouTube関連のフィルタまたはソートが存在する場合True
    """
    has_youtube_filter = any(key in query_data for key in YOUTUBE_FILTERS)
    return has_youtube_filter or query_data.get('sort') in YOUTUBE_SORTS


def has_view_filter_or_sort(query_data):
    """
    view関連のフィルタまたはソートが存在するかチェック

    Args:
        query_data: クエリパラメータの辞書

    Returns:
        bool: view関連のフィルタまたはソートが存在する場合True
    """
    has_view_lte_filter = 'view_lte' in query_data
    has_view_sort = query_data.get('sort') in ['view', '-view']
    return has_view_lte_filter or has_view_sort


def has_like_filter_or_sort(query_data):
    """
    like関連のフィルタまたはソートが存在するかチェック

    Args:
        query_data: クエリパラメータの辞書

    Returns:
        bool: like関連のフィルタまたはソートが存在する場合True
    """
    has_like_lte_filter = 'like_lte' in query_data
    has_like_sort = query_data.get('sort') in ['like', '-like']
    return has_like_lte_filter or has_like_sort


def has_upload_time_sort(query_data):
    """
    upload_time関連のソートが存在するかチェック

    Args:
        query_data: クエリパラメータの辞書

    Returns:
        bool: upload_time関連のソートが存在する場合True
    """
    return query_data.get('sort') in ['upload_time', '-upload_time']
