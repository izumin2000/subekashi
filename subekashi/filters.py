import django_filters
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
    SongモデルのためのDjango-filter FilterSet
    """

    # 大文字小文字を区別しない部分一致テキストフィールド
    title = django_filters.CharFilter(lookup_expr='icontains')
    channel = django_filters.CharFilter(lookup_expr='icontains')
    lyrics = django_filters.CharFilter(lookup_expr='icontains')
    url = django_filters.CharFilter(lookup_expr='icontains')

    # 完全一致フィルタ（後方互換性のため_exactサフィックスを使用）
    # 注意: _exactという名前にもかかわらず、これらは完全一致を実行します（部分一致ではありません）
    title_exact = django_filters.CharFilter(field_name='title', lookup_expr='exact')
    channel_exact = django_filters.CharFilter(field_name='channel', lookup_expr='exact')

    # YouTubeデータのgte/lteフィルタ
    view_gte = django_filters.NumberFilter(field_name='view', lookup_expr='gte')
    view_lte = django_filters.NumberFilter(field_name='view', lookup_expr='lte')
    like_gte = django_filters.NumberFilter(field_name='like', lookup_expr='gte')
    like_lte = django_filters.NumberFilter(field_name='like', lookup_expr='lte')
    upload_time_gte = django_filters.DateTimeFilter(field_name='upload_time', lookup_expr='gte')
    upload_time_lte = django_filters.DateTimeFilter(field_name='upload_time', lookup_expr='lte')

    # 真偽値フィルタ
    issubeana = django_filters.BooleanFilter()
    isjoke = django_filters.BooleanFilter()
    isdraft = django_filters.BooleanFilter()
    isoriginal = django_filters.BooleanFilter()
    isinst = django_filters.BooleanFilter()
    isdeleted = django_filters.BooleanFilter()

    # 複雑なカスタムフィルタ
    keyword = django_filters.CharFilter(method='filter_keyword')
    imitate = django_filters.CharFilter(method='filter_imitate')
    imitated = django_filters.CharFilter(method='filter_imitated')
    guesser = django_filters.CharFilter(method='filter_guesser')
    mediatypes = django_filters.CharFilter(method='filter_mediatypes')
    islack = django_filters.BooleanFilter(method='filter_islack')

    # ソート
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
        fields = []  # すべてのフィールドを上記で明示的に定義します

    def filter_keyword(self, queryset, name, value):
        """複数フィールドにわたるキーワード検索"""
        return queryset.filter(filter_by_keyword(value))

    def filter_imitate(self, queryset, name, value):
        """imitateフィールドによるフィルタ（カンマ区切りリストをサポート）"""
        return queryset.filter(filter_by_imitate(value))

    def filter_imitated(self, queryset, name, value):
        """imitatedフィールドによるフィルタ（カンマ区切りリストをサポート）"""
        return queryset.filter(filter_by_imitated(value))

    def filter_guesser(self, queryset, name, value):
        """guesserによるフィルタ（タイトルとチャンネルを検索）"""
        return queryset.filter(filter_by_guesser(value))

    def filter_mediatypes(self, queryset, name, value):
        """正規表現を使用したメディアタイプによるフィルタ"""
        return queryset.filter(filter_by_mediatypes(value))

    def filter_islack(self, queryset, name, value):
        """不完全な曲をフィルタ"""
        if value:
            return queryset.filter(filter_by_lack)
        return queryset

    def filter_sort(self, queryset, name, value):
        """ランダムソートを含むソート処理"""
        if not value:
            return queryset

        # 特別な'random'ソートを処理
        sort_value = self.data.get('sort', '')
        if sort_value == 'random':
            return queryset.order_by('?')

        # その他のケースはデフォルトのOrderingFilterに処理させる
        return queryset.order_by(*value) if value else queryset

    @property
    def qs(self):
        """
        YouTube関連のクエリが存在する場合、自動的にYouTubeメディアフィルタを
        追加するためにqsプロパティをオーバーライド
        """
        queryset = super().qs

        # YouTube関連のパラメータが存在するかチェック
        YOUTUBE_ITEMS = ['view', 'like', 'upload_time']
        YOUTUBE_SORT = ['upload_time', '-upload_time', 'view', '-view', 'like', '-like']

        youtube_filters = [f'{item}_gte' for item in YOUTUBE_ITEMS] + \
                         [f'{item}_lte' for item in YOUTUBE_ITEMS]

        has_youtube_sort = self.data.get('sort') in YOUTUBE_SORT
        has_youtube_filter = any(key in self.data for key in youtube_filters)

        # YouTube関連だがmediatypesが指定されていない場合、YouTubeフィルタを追加
        if (has_youtube_sort or has_youtube_filter) and 'mediatypes' not in self.data:
            queryset = queryset.filter(filter_by_mediatypes('youtube'))

        return queryset
