"""
Django-filter based search implementation.
Replaces the custom search.py implementation.
"""
import math
from subekashi.filters import SongFilter
from subekashi.models import Song

DEFALT_SIZE = 50  # 1度の検索で取得できるsongオブジェクトの数


def song_search(querys, is_paging=False):
    """
    Filter and search songs using django-filter.

    Args:
        querys: Dictionary of query parameters
        is_paging: Boolean indicating if pagination should be applied

    Returns:
        Tuple of (queryset, statistics_dict)
    """
    statistics = {}

    # Clean query parameters - handle list values
    cleaned_querys = {}
    for key, value in querys.items():
        # If value is a list, take the first element
        if isinstance(value, list) and len(value) > 0:
            value = value[0]

        # Convert boolean string values to actual booleans
        if value in ["True", "true", "1", 1]:
            value = True
        elif value in ["False", "false", "0", 0]:
            value = False

        cleaned_querys[key] = value

    # Apply django-filter
    filterset = SongFilter(cleaned_querys, queryset=Song.objects.all())
    song_qs = filterset.qs

    # Handle sorting (already handled in FilterSet, but keep for compatibility)
    # The FilterSet handles random sort internally

    # Count results
    count = song_qs.count()

    # Add count to statistics if requested
    if cleaned_querys.get("count"):
        statistics["count"] = count

    # Handle pagination
    if is_paging:
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

        # Apply pagination slice
        start = (page - 1) * size
        end = page * size
        song_qs = song_qs[start:end]

    return song_qs, statistics
