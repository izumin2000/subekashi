import django_filters
from django.core.exceptions import ValidationError
from subekashi.models import Song
from subekashi.lib.filter import (
    filter_by_keyword,
    filter_by_imitate,
    filter_by_imitated,
    filter_by_guesser,
    filter_by_mediatypes,
    filter_by_lack,
)
from subekashi.lib.url import clean_url
from subekashi.lib.query_utils import has_view_filter_or_sort, has_like_filter_or_sort


def validate_positive_integer(value):
    """正の整数であることを検証（1以上）"""
    if value is not None and value < 1:
        raise ValidationError(f'値は1以上である必要があります: {value}')
    return value


def validate_max_length(max_length):
    """最大文字列長を検証するバリデータを返す"""
    def validator(value):
        if value and len(value) > max_length:
            raise ValidationError(
                f'文字列長は{max_length}文字以下である必要があります（現在: {len(value)}文字）'
            )
        return value
    return validator


class SongFilter(django_filters.FilterSet):
    """
    SongモデルのためのDjango-filter FilterSet
    """

    # 大文字小文字を区別しない部分一致テキストフィールド
    # models.pyの max_length に準拠したバリデーション
    title = django_filters.CharFilter(
        lookup_expr='icontains',
        validators=[validate_max_length(500)]
    )
    channel = django_filters.CharFilter(
        field_name='authors__name',
        lookup_expr='icontains',
        validators=[validate_max_length(500)]
    )
    lyrics = django_filters.CharFilter(
        lookup_expr='icontains',
        validators=[validate_max_length(10000)]
    )
    url = django_filters.CharFilter(
        method='filter_url',
        validators=[validate_max_length(500)]
    )

    # 完全一致フィルタ（後方互換性のため_exactサフィックスを使用）
    title_exact = django_filters.CharFilter(
        field_name='title',
        lookup_expr='exact',
        validators=[validate_max_length(500)]
    )
    channel_exact = django_filters.CharFilter(
        field_name='authors__name',
        lookup_expr='exact',
        validators=[validate_max_length(500)]
    )

    # YouTubeデータのgte/lteフィルタ
    # 負の値を許可しない
    view_gte = django_filters.NumberFilter(
        field_name='view',
        lookup_expr='gte',
        validators=[validate_positive_integer]
    )
    view_lte = django_filters.NumberFilter(
        field_name='view',
        lookup_expr='lte',
        validators=[validate_positive_integer]
    )
    like_gte = django_filters.NumberFilter(
        field_name='like',
        lookup_expr='gte',
        validators=[validate_positive_integer]
    )
    like_lte = django_filters.NumberFilter(
        field_name='like',
        lookup_expr='lte',
        validators=[validate_positive_integer]
    )
    upload_time_gte = django_filters.DateTimeFilter(field_name='upload_time', lookup_expr='gte')
    upload_time_lte = django_filters.DateTimeFilter(field_name='upload_time', lookup_expr='lte')

    # 真偽値フィルタ
    issubeana = django_filters.BooleanFilter()
    isjoke = django_filters.BooleanFilter()
    isdraft = django_filters.BooleanFilter()
    isoriginal = django_filters.BooleanFilter()
    isinst = django_filters.BooleanFilter()
    isdeleted = django_filters.BooleanFilter()

    # カスタムフィルタ
    keyword = django_filters.CharFilter(
        method='filter_keyword',
        validators=[validate_max_length(500)]
    )
    imitate = django_filters.CharFilter(
        method='filter_imitate',
        validators=[validate_max_length(10000)]
    )
    imitated = django_filters.CharFilter(
        method='filter_imitated',
        validators=[validate_max_length(10000)]
    )
    guesser = django_filters.CharFilter(
        method='filter_guesser',
        validators=[validate_max_length(500)]
    )
    mediatypes = django_filters.CharFilter(
        method='filter_mediatypes',
        validators=[validate_max_length(100)]
    )
    islack = django_filters.BooleanFilter(method='filter_islack')

    # ソート (randomをサポートするためCharFilterを使用)
    sort = django_filters.CharFilter(
        method='filter_sort',
        validators=[validate_max_length(100)]
    )

    class Meta:
        model = Song
        fields = []  # すべてのフィールドを上記で明示的に定義

    def filter_keyword(self, queryset, name, value):
        """複数フィールドにわたるキーワード検索"""
        value = clean_url(value)
        return queryset.filter(filter_by_keyword(value))

    def filter_url(self, queryset, name, value):
        """URLフィールドによるフィルタ（clean_urlを適用）"""
        value = clean_url(value)
        return queryset.filter(url__icontains=value)

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
        if value == 'random':
            return queryset.order_by('?')

        # 許可されたソートフィールド
        allowed_fields = {
            'id', '-id',
            'title', '-title',
            'channel', '-channel',
            'authors__name', '-authors__name',
            'upload_time', '-upload_time',
            'view', '-view',
            'like', '-like',
            'post_time', '-post_time',
        }

        # channelソートをauthors__nameに変換（後方互換性のため）
        if value == 'channel':
            value = 'authors__name'
        elif value == '-channel':
            value = '-authors__name'

        # バリデーション
        if value not in allowed_fields:
            raise ValidationError(f'許可されていないソートフィールドです: {value}')

        return queryset.order_by(value)

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

        # view関連のフィルタまたはソートがある場合、view >= 1 を適用
        if has_view_filter_or_sort(self.data):
            queryset = queryset.filter(view__gte=1)

        # like関連のフィルタまたはソートがある場合、like >= 1 を適用
        if has_like_filter_or_sort(self.data):
            queryset = queryset.filter(like__gte=1)

        # channelフィルタ（authors__name）使用時にのみdistinct()を適用
        if 'channel' in self.data or 'channel_exact' in self.data:
            queryset = queryset.distinct()

        return queryset
