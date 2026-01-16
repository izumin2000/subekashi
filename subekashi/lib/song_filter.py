"""
Django-filterベースの検索実装
"""
import math
from subekashi.lib.filters import SongFilter
from subekashi.lib.query_utils import clean_query_params
from subekashi.models import Song
from rest_framework.exceptions import ValidationError

DEFALT_SIZE = 50  # 1度の検索で取得できるsongオブジェクトの数


def song_filter(querys):
    """
    django-filterを使用して楽曲をフィルタリング・検索する

    Args:
        querys: クエリパラメータの辞書

    Returns:
        (queryset, statistics_dict)のタプル

    Raises:
        ValidationError: バリデーションエラーが発生した場合
    """
    statistics = {}

    # クエリパラメータをクリーンアップ - リスト値を処理
    cleaned_querys = clean_query_params(querys)

    # django-filterを適用
    try:
        filterset = SongFilter(cleaned_querys, queryset=Song.objects.all())

        # フィルタのバリデーションエラーをチェック
        if not filterset.is_valid():
            # エラーメッセージを収集
            error_messages = []
            for field, errors in filterset.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")

            raise ValidationError({"error": ", ".join(error_messages)})

        song_qs = filterset.qs
    except Exception as e:
        # django_filters.exceptions.FieldErrorやその他の例外をキャッチ
        if isinstance(e, ValidationError):
            raise
        raise ValidationError({"error": str(e)})

    # 結果をカウント
    count = song_qs.count()
    statistics["count"] = count

    # ページネーション処理
    # 実用的な上限として2^31-1を使用
    MAX_QUERY_SIZE = 2147483647

    try:
        page = int(cleaned_querys.get("page", 1))
        if page < 1 or page > MAX_QUERY_SIZE:
            page = 1
    except (ValueError, TypeError):
        page = 1

    try:
        size = int(cleaned_querys.get("size", DEFALT_SIZE))
        if size < 1 or size > MAX_QUERY_SIZE:
            size = DEFALT_SIZE
    except (ValueError, TypeError):
        size = DEFALT_SIZE

    # 統計情報をレスポンスに追加
    statistics["page"] = page
    statistics["size"] = size
    max_page = math.ceil(count / size) if size > 0 else 1
    statistics["max_page"] = max_page

    # ページネーションのスライスを適用
    start = (page - 1) * size
    end = page * size
    song_qs = song_qs[start:end]

    return song_qs, statistics
