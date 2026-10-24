import django_filters
from django import forms
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from article.models import Article
from subekashi.converters import SQLITE_INT_MAX, SQLITE_INT_MIN
from subekashi.lib.pagination import OpenDataPagination
from subekashi.lib.throttling import UserRateThrottle
from subekashi.models import Author, Contact, History, Prush, Stats, Word
from ...serializer import (
    ArticleSerializer,
    AuthorDetailSerializer,
    ContactSerializer,
    HistorySerializer,
    PrushSerializer,
    StatsSerializer,
    WordSerializer,
)


class OpenDataThrottle(UserRateThrottle):
    rate = '2/second'


# 誰でもGETで取得できる、読み取り専用の公開API（#1243）
class OpenDataAPI(viewsets.ReadOnlyModelViewSet):
    throttle_classes = [OpenDataThrottle]
    pagination_class = OpenDataPagination
    filter_backends = [DjangoFilterBackend]
    # /api/word/candidates/ のような同じ接頭辞の別のAPIを個別取得として扱わないよう、idは数字に限る
    lookup_value_regex = r'[0-9]+'


class AuthorAPI(OpenDataAPI):
    queryset = Author.objects.prefetch_related('aliases', 'links').order_by('id')
    serializer_class = AuthorDetailSerializer


class PrushAPI(OpenDataAPI):
    queryset = Prush.objects.order_by('id')
    serializer_class = PrushSerializer


# NumberFilterは小数も受け付け、?song=1.5 でid=1の曲の履歴を返してしまうため、整数に限る。
# SQLiteで扱えない大きさの整数はクエリの実行時にOverflowErrorになるため、入力エラーにする
class IdFilter(django_filters.NumberFilter):
    field_class = forms.IntegerField

    def __init__(self, *args, **kwargs):
        super().__init__(*args, min_value=SQLITE_INT_MIN, max_value=SQLITE_INT_MAX, **kwargs)


class HistoryFilter(django_filters.FilterSet):
    song = IdFilter()
    author = IdFilter()
    editor = IdFilter(method='filter_editor')

    # 編集履歴を非公開にしている編集者で絞り込めると、APIで隠した編集者がわかってしまうため、公開している編集者に限る
    def filter_editor(self, queryset, name, value):
        return queryset.filter(editor=value).filter(Q(editor__is_open=True) | Q(editor__is_forced_open=True))

    class Meta:
        model = History
        fields = ['song', 'author', 'editor']


class HistoryAPI(OpenDataAPI):
    # HistorySerializerが編集者の公開設定を見るため、履歴ごとに編集者を取得しないようselect_relatedする
    queryset = History.objects.select_related('editor').order_by('-create_time', '-id')
    serializer_class = HistorySerializer
    filterset_class = HistoryFilter


# 回答していない問い合わせは返さない
class ContactAPI(OpenDataAPI):
    queryset = Contact.get_answered()
    serializer_class = ContactSerializer


class WordAPI(OpenDataAPI):
    queryset = Word.objects.order_by('id')
    serializer_class = WordSerializer
    filterset_fields = ['word', 'hinshi', 'katsuyou']


class StatsAPI(OpenDataAPI):
    queryset = Stats.objects.all()
    serializer_class = StatsSerializer
    filterset_fields = ['songrange']


class ArticleAPI(OpenDataAPI):
    serializer_class = ArticleSerializer
    filterset_fields = ['tag']
    # 記事のidは「.」を含むことがある
    lookup_value_regex = r'[^/]+'

    # 記事一覧と同じく、非公開の記事・公開日時の前の記事は返さない
    def get_queryset(self):
        return Article.objects.filter(is_open=True, post_time__lte=timezone.now()).order_by('-post_time')
