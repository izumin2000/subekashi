import django_filters
from django.db.models import Q
from subekashi.models import Song
from subekashi.lib.filter import (
    filter_by_keyword,
    filter_by_imitate,
    filter_by_imitated,
    filter_by_guesser,
    filter_by_mediatypes,
    filter_by_lack,
)


class SongFilter(django_filters.FilterSet):
    """
    Django-filter FilterSet for Song model.
    Replaces the custom search.py implementation while maintaining backward compatibility.
    """

    # Text fields with case-insensitive contains
    title = django_filters.CharFilter(lookup_expr='icontains')
    channel = django_filters.CharFilter(lookup_expr='icontains')
    lyrics = django_filters.CharFilter(lookup_expr='icontains')
    url = django_filters.CharFilter(lookup_expr='icontains')

    # Exact match filters (using _exact suffix for backward compatibility)
    # Note: Despite the name "_exact", these perform exact matching (not partial)
    title_exact = django_filters.CharFilter(field_name='title', lookup_expr='exact')
    channel_exact = django_filters.CharFilter(field_name='channel', lookup_expr='exact')

    # YouTube data filters with gte/lte
    view_gte = django_filters.NumberFilter(field_name='view', lookup_expr='gte')
    view_lte = django_filters.NumberFilter(field_name='view', lookup_expr='lte')
    like_gte = django_filters.NumberFilter(field_name='like', lookup_expr='gte')
    like_lte = django_filters.NumberFilter(field_name='like', lookup_expr='lte')
    upload_time_gte = django_filters.DateTimeFilter(field_name='upload_time', lookup_expr='gte')
    upload_time_lte = django_filters.DateTimeFilter(field_name='upload_time', lookup_expr='lte')

    # Boolean filters
    issubeana = django_filters.BooleanFilter()
    isjoke = django_filters.BooleanFilter()
    isdraft = django_filters.BooleanFilter()
    isoriginal = django_filters.BooleanFilter()
    isinst = django_filters.BooleanFilter()
    isdeleted = django_filters.BooleanFilter()

    # Complex custom filters
    keyword = django_filters.CharFilter(method='filter_keyword')
    imitate = django_filters.CharFilter(method='filter_imitate')
    imitated = django_filters.CharFilter(method='filter_imitated')
    guesser = django_filters.CharFilter(method='filter_guesser')
    mediatypes = django_filters.CharFilter(method='filter_mediatypes')
    islack = django_filters.BooleanFilter(method='filter_islack')

    # Sorting
    sort = django_filters.OrderingFilter(
        fields=(
            ('title', 'title'),
            ('channel', 'channel'),
            ('upload_time', 'upload_time'),
            ('view', 'view'),
            ('like', 'like'),
            ('post_time', 'post_time'),
        ),
        method='filter_sort',
    )

    class Meta:
        model = Song
        fields = []  # We define all fields explicitly above

    def filter_keyword(self, queryset, name, value):
        """Filter by keyword across multiple fields"""
        return queryset.filter(filter_by_keyword(value))

    def filter_imitate(self, queryset, name, value):
        """Filter by imitate field (comma-separated list support)"""
        return queryset.filter(filter_by_imitate(value))

    def filter_imitated(self, queryset, name, value):
        """Filter by imitated field (comma-separated list support)"""
        return queryset.filter(filter_by_imitated(value))

    def filter_guesser(self, queryset, name, value):
        """Filter by guesser (searches title and channel)"""
        return queryset.filter(filter_by_guesser(value))

    def filter_mediatypes(self, queryset, name, value):
        """Filter by media types using regex"""
        return queryset.filter(filter_by_mediatypes(value))

    def filter_islack(self, queryset, name, value):
        """Filter incomplete songs"""
        if value:
            return queryset.filter(filter_by_lack)
        return queryset

    def filter_sort(self, queryset, name, value):
        """Handle sorting including random sort"""
        if not value:
            return queryset

        # Handle the special 'random' sort
        sort_value = self.data.get('sort', '')
        if sort_value == 'random':
            return queryset.order_by('?')

        # Let the default OrderingFilter handle other cases
        return queryset.order_by(*value) if value else queryset

    @property
    def qs(self):
        """
        Override qs property to automatically add YouTube media filter
        when YouTube-related queries are present
        """
        queryset = super().qs

        # Check if YouTube-related parameters are present
        YOUTUBE_ITEMS = ['view', 'like', 'upload_time']
        YOUTUBE_SORT = ['upload_time', '-upload_time', 'view', '-view', 'like', '-like']

        youtube_filters = [f'{item}_gte' for item in YOUTUBE_ITEMS] + \
                         [f'{item}_lte' for item in YOUTUBE_ITEMS]

        has_youtube_sort = self.data.get('sort') in YOUTUBE_SORT
        has_youtube_filter = any(key in self.data for key in youtube_filters)

        # If YouTube-related but no mediatypes specified, add YouTube filter
        if (has_youtube_sort or has_youtube_filter) and 'mediatypes' not in self.data:
            queryset = queryset.filter(filter_by_mediatypes('youtube'))

        return queryset
